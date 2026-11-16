"""Compute the pre-registered hypotheses H1-H8 from saved outputs (no model calls).

    python experiments/analyze.py --run TEST_deploy

Writes results/ANALYSIS_<run>.json and results/ANALYSIS_<run>.md
"""
import argparse
import json
import statistics
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from splitmatch import paths, stats  # noqa: E402
from splitmatch.privacy import audit, load_log  # noqa: E402

CACHE = paths.BASELINE_CACHE


def load_baseline(name, key="prediction"):
    d = {}
    for l in open(CACHE / name, encoding="utf-8"):
        r = json.loads(l)
        p = r.get(key)
        d[r["pair_id"]] = {"pred": None if p is None else int(str(p).lower() == "eligible"),
                           "y": int(str(r["target"]).lower() == "eligible"),
                           "trial": r["trial_id"], "patient": r["pair_id"].split("__")[0],
                           "conf": r.get("confidence")}
    return d


def load_advisory():
    d = {}
    for l in open(CACHE / "experiment8_testing_data_advisory.jsonl", encoding="utf-8"):
        r = json.loads(l)
        p = r.get("adv_pred")
        d[r["pair_id"]] = {"pred": None if p is None else int(str(p).lower() == "eligible"),
                           "y": int(str(r["target"]).lower() == "eligible"), "trial": r["trial_id"],
                           "patient": r["pair_id"].split("__")[0], "conf": r.get("adv_conf")}
    return d


def split_dict(df, mode):
    return {r.pair_id: {"pred": (1 if r[mode] == "ELIGIBLE" else 0 if r[mode] == "NOT_ELIGIBLE" else None),
                        "y": int(r.label), "trial": r.trial_id, "patient": r.patient_id,
                        "u": r.u} for _, r in df.iterrows()}


def fmt(m):
    return {k: (round(v, 4) if isinstance(v, float) else v) for k, v in m.items()}


def _lab(p):
    return 1 if p == "ELIGIBLE" else 0 if p == "NOT_ELIGIBLE" else None


def analyze_stress(base_run: str, edge: str) -> dict:
    """H4 (redaction, closed loop), H6 (counterfactual cues), H8 (noisy) from saved outputs."""
    out = {}
    base = pd.read_json(paths.RESULTS / "runs" / base_run / "predictions.jsonl", lines=True).set_index("pair_id")
    sdir = paths.RESULTS / "stress"
    f = sdir / f"redaction_{edge}.jsonl"
    if f.exists():
        r = pd.read_json(f, lines=True)
        aff = r[r.affected]
        def d(dfm, col):
            return {i: {"pred": _lab(p) if isinstance(p, str) else int(p), "y": int(y), "trial": t,
                        "patient": pt} for i, p, y, t, pt in zip(dfm.pair_id, dfm[col], dfm.label, dfm.trial_id, dfm.patient)}
        ids = list(aff.pair_id)
        S_sel = d(aff, "split_selective")
        Z = d(aff, "zs")
        # committed-wrong rate: committed AND wrong / all affected pairs
        def cw(dd):
            return float(sum(1 for i in ids if dd[i]["pred"] is not None and dd[i]["pred"] != dd[i]["y"]) / len(ids))
        diff = lambda a, b, sub: (sum(1 for i in sub if a[i]["pred"] is not None and a[i]["pred"] != a[i]["y"]) -  # noqa: E731
                                  sum(1 for i in sub if b[i]["pred"] is not None and b[i]["pred"] != b[i]["y"])) / len(sub)
        pt, ci = stats.cluster_boot(diff, [S_sel, Z], ids)
        S_red, S_ans = d(aff, "split_forced"), d(aff, "split_forced_after_answer")
        full = {i: {"pred": _lab(base.loc[o, "forced"]), "y": int(y)} for i, o, y in zip(aff.pair_id, aff.orig_pair, aff.label)}
        acc = lambda dd: float(sum(dd[i]["pred"] == dd[i]["y"] for i in ids) / len(ids))  # noqa: E731
        asked_pool = aff[~aff.split_selective.isin(["NOT_ELIGIBLE"])]
        out["H4_redaction"] = {
            "variant_pairs": len(r), "affected_pairs": len(aff),
            "committed_wrong_split_selective": cw(S_sel), "committed_wrong_zero_shot": cw(Z),
            "diff_split_minus_zs": pt, "diff_ci95_trial": ci,
            "ask_recall_removed_category": float(aff.asked_removed.mean()),
            "ask_recall_when_not_excluded": float(asked_pool.asked_removed.mean()) if len(asked_pool) else None,
            "forced_acc_redacted": acc(S_red), "forced_acc_after_one_answer": acc(S_ans),
            "forced_acc_full_note": acc(full), "zero_shot_acc_redacted": acc(Z),
        }
    f = sdir / f"counterfactual_{edge}.jsonl"
    if f.exists():
        r = pd.read_json(f, lines=True)
        zs_orig = {}
        zfile = paths.RESULTS / "baselines" / "ZS_cloud_test_rerun.jsonl"
        if zfile.exists():
            z = pd.read_json(zfile, lines=True)
            zs_orig = dict(zip(z.pair_id, (z.prediction == "Eligible").astype(int)))
        r["split_flip"] = [base.loc[o, "forced"] != p for o, p in zip(r.orig_pair, r.split_forced)]
        r["zs_flip"] = [zs_orig.get(o, None) is not None and zs_orig[o] != p for o, p in zip(r.orig_pair, r.zs)]
        fl = {i: {"s": int(a), "z": int(b), "trial": t, "patient": pt, "pred": int(not a), "y": 1}
              for i, a, b, t, pt in zip(r.pair_id, r.split_flip, r.zs_flip, r.trial_id, r.patient)}
        flz = {i: {**v, "pred": int(not v["z"])} for i, v in fl.items()}
        ids = list(r.pair_id)
        # statistic: flip_rate(zero-shot) - flip_rate(SPLIT); > 0 means SPLIT flips less
        fdiff = lambda a, sub: float(sum(a[i]["z"] - a[i]["s"] for i in sub) / len(sub))  # noqa: E731
        pt_, ci_ = stats.cluster_boot(fdiff, [fl], ids)
        out["H6_counterfactual"] = {"variant_pairs": len(r),
                                    "flip_rate_split": float(r.split_flip.mean()),
                                    "flip_rate_zero_shot": float(r.zs_flip.mean()),
                                    "flip_rate_by_cue_split": r.groupby("variant").split_flip.mean().to_dict(),
                                    "flip_rate_by_cue_zero_shot": r.groupby("variant").zs_flip.mean().to_dict(),
                                    "zs_minus_split_flip": pt_, "zs_minus_split_flip_ci95_trial": ci_,
                                    "mcnemar_flips": stats.mcnemar(fl, flz, ids)}
    f = sdir / f"noisy_{edge}.jsonl"
    if f.exists():
        r = pd.read_json(f, lines=True)
        ids = list(r.pair_id)
        S = {i: {"pred": _lab(p), "y": int(y), "trial": t, "patient": pt} for i, p, y, t, pt in zip(r.pair_id, r.split_forced, r.label, r.trial_id, r.patient)}
        Z = {i: {"pred": int(p), "y": int(y), "trial": t, "patient": pt} for i, p, y, t, pt in zip(r.pair_id, r.zs, r.label, r.trial_id, r.patient)}
        out["H8_noisy"] = {"split_forced": stats.confusion(S, ids), "zero_shot": stats.confusion(Z, ids)}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--stress-edge", default="")
    a = ap.parse_args()
    if a.stress_edge:
        res = analyze_stress(a.run, a.stress_edge)
        (paths.RESULTS / f"ANALYSIS_STRESS_{a.run}_{a.stress_edge}.json").write_text(
            json.dumps(res, indent=1, default=str), encoding="utf-8")
        print(json.dumps(res, indent=1, default=str))
        return
    run_dir = paths.RESULTS / "runs" / a.run
    df = pd.read_json(run_dir / "predictions.jsonl", lines=True)
    ids = sorted(df.pair_id)
    S_f, S_s = split_dict(df, "forced"), split_dict(df, "selective")
    base = {"zero_shot": load_baseline("experiment1_testing_data_zero_shot.jsonl"),
            "few_shot": load_baseline("experiment1_testing_data_few_shot.jsonl"),
            "rag": load_baseline("experiment1_testing_data_rag_only.jsonl"),
            "indicon_hard_veto": load_baseline("experiment1_testing_data_full.jsonl"),
            "indicon_advisory": load_advisory()}
    out = {"run": a.run, "n": len(ids)}

    # main table
    table = {"SPLIT-Match (forced)": fmt(stats.confusion(S_f, ids)),
             "SPLIT-Match (selective)": fmt(stats.confusion(S_s, ids))}
    for k, d in base.items():
        table[k] = fmt(stats.confusion(d, ids))
    for k in list(table):
        dd = S_f if k.startswith("SPLIT-Match (forced") else S_s if k.startswith("SPLIT") else base[k]
        table[k]["f1_ci95_trial"] = [round(x, 4) for x in stats.cluster_boot(stats.f1_of, [dd], ids)[1]]
    out["main_table"] = table

    # H1
    out["H1_non_inferiority_vs_zero_shot"] = stats.non_inferiority(S_f, base["zero_shot"], ids)
    out["H1_secondary_vs_indicon"] = {k: stats.non_inferiority(S_f, base[k], ids)
                                      for k in ("indicon_hard_veto", "indicon_advisory")}

    # H2 privacy
    recs = load_log(run_id=f"run:{a.run}")
    out["H2_privacy"] = audit(recs)
    out["H2_privacy"]["offline_decided_share"] = float(
        ((df.n_l2 == 0) & df.selective.isin(["ELIGIBLE", "NOT_ELIGIBLE"])).mean())
    out["H2_privacy"]["pairs_with_any_cloud_fact_call"] = float((df.n_l2 > 0).mean())
    out["H2_privacy"]["l2_calls_per_pair_mean"] = float(df.n_l2.mean())

    # H3 edge cost
    t = json.loads((run_dir / "timing.json").read_text())
    edge_calls = [r for r in recs if r["channel"] in ("edge_local", "edge_proxy") and not r.get("cached")]
    lat = sorted(r.get("latency_s", 0) for r in edge_calls if r.get("tag") == "structure")
    out["H3_edge"] = {
        "structure_s_p50": statistics.median(lat) if lat else None,
        "structure_s_p95": lat[int(0.95 * (len(lat) - 1))] if lat else None,
        "l1_s_median": statistics.median([r["latency_s"] for r in edge_calls if r.get("tag") == "l1"]) if any(r.get("tag") == "l1" for r in edge_calls) else None,
        "eval_ms_mean": statistics.mean(t["eval_ms"]) if t["eval_ms"] else None,
        "eval_ms_max": max(t["eval_ms"]) if t["eval_ms"] else None,
        "edge_calls": len(edge_calls), "patients": df.patient_id.nunique(),
        "pairs": len(df), "cloud_fact_calls": int(df.n_l2.sum()),
    }

    # H5 deferral quality (AURC on forced predictions)
    corr = [int(S_f[i]["pred"] == S_f[i]["y"]) for i in ids]
    out["H5_aurc"] = {"split_u": stats.aurc([S_f[i]["u"] for i in ids], corr)}
    for k in ("zero_shot", "indicon_advisory"):
        d = base[k]
        c = [int(d[i]["pred"] == d[i]["y"]) for i in ids]
        conf = [-(d[i]["conf"] if d[i]["conf"] is not None else 0) for i in ids]
        out["H5_aurc"][k] = stats.aurc(conf, c)

    # H7 subset: the 17 INDICON gate false negatives (previously inspected; flagged)
    fn17 = json.loads((paths.BASELINES / "results" / "experiment5_gate_safety_testing_data.json")
                      .read_text(encoding="utf-8"))
    fn_ids = fn17.get("false_negative_pairs") or fn17.get("fn_pairs") or []
    if fn_ids:
        out["H7_indicon_gate_fn_subset"] = {"n": len(fn_ids), "split_forced_correct":
                                            sum(S_f[i]["pred"] == S_f[i]["y"] for i in fn_ids if i in S_f)}

    (paths.RESULTS / f"ANALYSIS_{a.run}.json").write_text(json.dumps(out, indent=1, default=str),
                                                         encoding="utf-8")
    print(json.dumps({"main": {k: (v["acc"], v["f1"], v["coverage"]) for k, v in table.items()},
                      "H1": {k: out["H1_non_inferiority_vs_zero_shot"][k] for k in
                             ("acc_diff", "acc_diff_ci95", "non_inferior", "f1_diff_ci95")},
                      "H2": {k: out["H2_privacy"][k] for k in ("raw_egress_violations",
                                                              "offline_decided_share",
                                                              "l2_calls_per_pair_mean")},
                      "H5": out["H5_aurc"]}, indent=1, default=str))


if __name__ == "__main__":
    main()
