"""Remaining pre-registered statistics + descriptive tables (no model calls).

    python experiments/analyze_extra.py

Adds what analyze.py reports only as point estimates or not at all:
  H5  trial-cluster bootstrap CI of the AURC differences
  H7  boolean-only vs full: F1 difference with CI (+ the flagged INDICON 17-FN subset)
  ABL every pre-registered ablation vs TEST_proxy (forced F1 diff CI, selective coverage/acc, L2 load)
  H8  delta-F1 (noisy - clean) for SPLIT-Match and zero-shot, CI of each and of the difference
  FRONTIER  accuracy vs patient-data exposure across all conditions (descriptive)
Writes results/ANALYSIS_EXTRA.json. Missing inputs are skipped and listed under "missing".
"""
import json
import statistics
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from analyze import load_advisory, load_baseline, split_dict  # noqa: E402
from splitmatch import paths, stats  # noqa: E402
from splitmatch.pipeline import metrics  # noqa: E402

R = paths.RESULTS
missing = []


def run_df(name):
    f = R / "runs" / name / "predictions.jsonl"
    if not f.exists():
        missing.append(name)
        return None
    return pd.read_json(f, lines=True)


def jsonl_baseline(name):
    f = R / "baselines" / f"{name}.jsonl"
    if not f.exists():
        missing.append(name)
        return None
    d = {}
    for l in open(f, encoding="utf-8"):
        r = json.loads(l)
        d[r["pair_id"]] = {"pred": int(str(r["prediction"]).lower() == "eligible"), "y": int(r["label"]),
                           "trial": r["trial_id"], "patient": r["pair_id"].split("__")[0],
                           "conf": r.get("confidence"), "n_fields": r.get("n_fields")}
    return d


def r4(x):
    if isinstance(x, float):
        return round(x, 4)
    if isinstance(x, list):
        return [r4(v) for v in x]
    if isinstance(x, dict):
        return {k: r4(v) for k, v in x.items()}
    return x


def aurc_of(d, ids, key):
    return stats.aurc([d[i][key] for i in ids], [int(d[i]["pred"] == d[i]["y"]) for i in ids])


def main():
    out = {}
    base = run_df("TEST_proxy")
    ids = sorted(base.pair_id)
    S = split_dict(base, "forced")
    Ssel = split_dict(base, "selective")
    zs = load_baseline("experiment1_testing_data_zero_shot.jsonl")
    adv = load_advisory()

    # ── H5: AURC differences with trial-cluster CI ───────────────────────
    for d in (zs, adv):
        for i in ids:
            d[i]["score"] = -(d[i]["conf"] if d[i]["conf"] is not None else 0)
    for i in ids:
        S[i]["score"] = S[i]["u"]
    h5 = {}
    for k, d in (("zero_shot", zs), ("indicon_advisory", adv)):
        def fn(a, b, sub):
            return aurc_of(a, sub, "score") - aurc_of(b, sub, "score")
        pt, ci = stats.cluster_boot(fn, [S, d], ids)
        h5[f"split_minus_{k}"] = {"diff": pt, "ci95_trial": ci}
    h5["aurc"] = {"split_u": aurc_of(S, ids, "score"), "zero_shot": aurc_of(zs, ids, "score"),
                  "indicon_advisory": aurc_of(adv, ids, "score")}
    out["H5"] = h5

    # ── ablations vs TEST_proxy ──────────────────────────────────────────
    abl = {}
    for name in ("AB_hardveto", "AB_noL1", "AB_noL2", "AB_boolean", "AB_single", "AB_noverify"):
        df = run_df(name)
        if df is None:
            continue
        A = split_dict(df, "forced")
        m = metrics(df)
        pt, ci = stats.cluster_boot(stats.f1_diff, [A, S], ids)
        apt, aci = stats.cluster_boot(stats.acc_diff, [A, S], ids)
        abl[name] = {"forced": {k: m["forced"][k] for k in ("acc_all", "precision", "recall", "f1", "tp", "fp", "fn", "tn")},
                     "selective": {k: m["selective"][k] for k in ("coverage", "acc_decided", "precision", "recall")},
                     "l2_per_pair": m["mean_l2_per_pair"], "offline_decided": m["offline_decided"],
                     "f1_diff_vs_full": pt, "f1_diff_ci95": ci, "acc_diff_vs_full": apt, "acc_diff_ci95": aci,
                     "mcnemar_vs_full": stats.mcnemar(A, S, ids), "sign_flip_vs_full": stats.sign_flip(A, S, ids)}
    nc = jsonl_baseline("AB_nocompiler_proxy20b")
    if nc:
        pt, ci = stats.cluster_boot(stats.f1_diff, [nc, S], ids)
        apt, aci = stats.cluster_boot(stats.acc_diff, [nc, S], ids)
        abl["AB_nocompiler_proxy20b"] = {"forced": stats.confusion(nc, ids), "f1_diff_vs_full": pt,
                                         "f1_diff_ci95": ci, "acc_diff_vs_full": apt, "acc_diff_ci95": aci,
                                         "mcnemar_vs_full": stats.mcnemar(nc, S, ids)}
    full_m = metrics(base)
    abl["_full_TEST_proxy"] = {"forced": {k: full_m["forced"][k] for k in ("acc_all", "precision", "recall", "f1")},
                               "selective": {k: full_m["selective"][k] for k in ("coverage", "acc_decided", "precision", "recall")},
                               "l2_per_pair": full_m["mean_l2_per_pair"], "offline_decided": full_m["offline_decided"]}
    out["ablations"] = abl

    # ── H7 ───────────────────────────────────────────────────────────────
    if "AB_boolean" in abl:
        bdf = run_df("AB_boolean")
        Bd = split_dict(bdf, "forced")
        fn17 = json.loads((paths.BASELINES / "results" / "experiment5_gate_safety_testing_data.json").read_text(encoding="utf-8"))
        fn_ids = fn17.get("false_negative_pairs") or fn17.get("fn_pairs") or []
        out["H7"] = {"f1_full_minus_boolean": -abl["AB_boolean"]["f1_diff_vs_full"],
                     "ci95": [-abl["AB_boolean"]["f1_diff_ci95"][1], -abl["AB_boolean"]["f1_diff_ci95"][0]],
                     "fn17_subset_flagged": {"n": len(fn_ids),
                                             "full_correct": sum(S[i]["pred"] == S[i]["y"] for i in fn_ids if i in S),
                                             "boolean_correct": sum(Bd[i]["pred"] == Bd[i]["y"] for i in fn_ids if i in Bd)}}

    # ── H8: noisy notes ──────────────────────────────────────────────────
    f = R / "stress" / "noisy_proxy.jsonl"
    zr = jsonl_baseline("ZS_cloud_test_rerun")
    if f.exists() and zr:
        r = pd.read_json(f, lines=True)
        Sn = {o: {"pred": 1 if p == "ELIGIBLE" else 0, "y": int(y), "trial": t, "patient": o.split("__")[0]}
              for o, p, y, t in zip(r.orig_pair, r.split_forced, r.label, r.trial_id)}
        Zn = {o: {"pred": int(p), "y": int(y), "trial": t, "patient": o.split("__")[0]}
              for o, p, y, t in zip(r.orig_pair, r.zs, r.label, r.trial_id)}
        def dd(a, b, sub):
            return stats.f1_of(a, sub) - stats.f1_of(b, sub)
        def did(a, b, c, d, sub):
            return (stats.f1_of(a, sub) - stats.f1_of(b, sub)) - (stats.f1_of(c, sub) - stats.f1_of(d, sub))
        sp, sci = stats.cluster_boot(dd, [Sn, S], ids)
        zp, zci = stats.cluster_boot(dd, [Zn, zr], ids)
        dp, dci = stats.cluster_boot(did, [Sn, S, Zn, zr], ids)
        out["H8"] = {"split_f1_clean": stats.f1_of(S, ids), "split_f1_noisy": stats.f1_of(Sn, ids),
                     "zs_f1_clean_rerun": stats.f1_of(zr, ids), "zs_f1_noisy": stats.f1_of(Zn, ids),
                     "split_delta_f1": sp, "split_delta_ci95": sci, "zs_delta_f1": zp, "zs_delta_ci95": zci,
                     "delta_split_minus_delta_zs": dp, "ci95": dci,
                     "split_acc_noisy": stats.confusion(Sn, ids)["acc"], "zs_acc_noisy": stats.confusion(Zn, ids)["acc"]}
    else:
        missing.append("noisy_proxy")

    # ── frontier (descriptive) ───────────────────────────────────────────
    fr = []
    def add(label, d, exposure, note=""):
        if d is None:
            return
        c = stats.confusion(d, ids)
        fr.append({"condition": label, "acc": c["acc"], "f1": c["f1"], "coverage": c["coverage"],
                   "f1_ci95": stats.cluster_boot(stats.f1_of, [d], ids)[1], "patient_data_to_cloud": exposure,
                   "note": note})
    add("Cloud zero-shot (full note)", zs, "full narrative every pair")
    add("Cloud zero-shot rerun", zr, "full narrative every pair", "Groq non-determinism check")
    rec = jsonl_baseline("REC_cloud_test_proxy")
    if rec:
        add("Cloud decides from de-identified record (exploratory)", rec,
            f"structured record, median {statistics.median(v['n_fields'] for v in rec.values())} fields, every pair")
    add("INDICON advisory hybrid", adv, "full narrative every pair")
    add("SPLIT-Match forced (proxy edge)", S, "single facts on 63% of pairs; no narrative")
    add("SPLIT-Match selective (proxy edge)", Ssel, "single facts on 63% of pairs; no narrative")
    nl2 = run_df("AB_noL2")
    if nl2 is not None:
        add("SPLIT-Match offline, -L2 (forced)", split_dict(nl2, "forced"), "none")
        add("SPLIT-Match offline, -L2 (selective)", split_dict(nl2, "selective"), "none")
    dep = run_df("TEST_deploy")
    if dep is not None:
        add("SPLIT-Match forced (local Qwen3-4B edge, deploy)", split_dict(dep, "forced"), "single facts; no narrative")
        add("SPLIT-Match selective (local Qwen3-4B edge, deploy)", split_dict(dep, "selective"), "single facts; no narrative")
    add("Edge zero-shot, gpt-oss-20b (proxy for edge)", nc, "none (if run on device)")
    add("Edge zero-shot, local Qwen3-4B", jsonl_baseline("ZS_edge_qwen4b_test"), "none")
    out["frontier"] = fr
    out["missing"] = sorted(set(missing))
    (R / "ANALYSIS_EXTRA.json").write_text(json.dumps(r4(out), indent=1, default=str), encoding="utf-8")
    print(json.dumps(r4(out), indent=1, default=str))


if __name__ == "__main__":
    main()
