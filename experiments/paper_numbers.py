"""[post-freeze, analysis only] Every number used in the paper, computed from saved outputs.

    python experiments/paper_numbers.py

Writes:
  results/PAPER_NUMBERS.json        all values, with trial-cluster bootstrap CIs
  paper/generated/numbers.tex       LaTeX macros (\\newcommand) used by paper/main.tex
  paper/generated/frontier.dat      pgfplots table for the privacy-accuracy frontier figure

No model calls. Conditions whose outputs do not exist yet are skipped and listed under
"missing"; their macros render as a red [pending] marker so a missing number can never
silently enter the paper.

Comparisons against cloud zero-shot reuse the pre-registered statistics (trial-cluster
bootstrap, B = 5000, seed 20260815; exact McNemar; exact trial sign-flip). The
non-inferiority test of the *edge full-note* conditions against cloud zero-shot is
EXPLORATORY: it was not pre-registered and is labelled as such in the paper.
"""
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from analyze import load_advisory, load_baseline, split_dict  # noqa: E402
from splitmatch import paths, stats  # noqa: E402

R = paths.RESULTS
OUT = Path(__file__).resolve().parent.parent / "paper" / "generated"
missing = []


def jsonl(name):
    f = R / "baselines" / f"{name}.jsonl"
    if not f.exists():
        missing.append(name)
        return None
    d = {}
    for line in open(f, encoding="utf-8"):
        r = json.loads(line)
        d[r["pair_id"]] = {"pred": int(str(r["prediction"]).lower() == "eligible"), "y": int(r["label"]),
                           "trial": r["trial_id"], "patient": r["pair_id"].split("__")[0],
                           "latency": r.get("latency_s")}
    return d


def run(names, mode):
    dfs = []
    for n in names:
        f = R / "runs" / n / "predictions.jsonl"
        if not f.exists():
            missing.append(n)
            return None
        dfs.append(pd.read_json(f, lines=True))
    return split_dict(pd.concat(dfs, ignore_index=True), mode)


def acc_of(d, sub):
    return float(stats.correct(d, sub).mean())


def summarise(d, ids):
    c = stats.confusion(d, ids)
    dec = [i for i in ids if d[i]["pred"] is not None]
    out = {"acc": c["acc"], "f1": c["f1"], "precision": c["precision"], "recall": c["recall"],
           "coverage": c["coverage"], "acc_ci95": stats.cluster_boot(acc_of, [d], ids)[1],
           "f1_ci95": stats.cluster_boot(stats.f1_of, [d], ids)[1]}
    if c["coverage"] < 1:
        out["acc_decided"] = acc_of(d, dec)
    return out


def versus(a, ref, ids):
    """a vs reference: accuracy difference (a - ref) with CI, McNemar, sign-flip, NI at -0.05."""
    pt, ci = stats.cluster_boot(stats.acc_diff, [a, ref], ids)
    return {"acc_diff": pt, "acc_diff_ci95": ci, "non_inferior_m005": ci[0] > -0.05,
            "mcnemar": stats.mcnemar(a, ref, ids), "sign_flip": stats.sign_flip(a, ref, ids)}


def main():
    res = {"test": {}, "dev": {}, "vs_cloud_zs": {"test": {}, "dev": {}}}
    test_ids = sorted(pd.read_json(R / "runs" / "TEST_proxy" / "predictions.jsonl", lines=True).pair_id)
    conds_test = {
        "cloudZS": load_baseline("experiment1_testing_data_zero_shot.jsonl"),
        "cloudZSrerun": jsonl("ZS_cloud_test_rerun"),
        "cloudFS": load_baseline("experiment1_testing_data_few_shot.jsonl"),
        "cloudRAG": load_baseline("experiment1_testing_data_rag_only.jsonl"),
        "indiconAdv": load_advisory(),
        "cloudRecord": jsonl("REC_cloud_test_proxy"),
        "cloudRecordDeploy": jsonl("REC_cloud_test_deploy"),
        "splitProxy": run(["TEST_proxy"], "forced"),
        "splitProxySel": run(["TEST_proxy"], "selective"),
        "splitDeploy": run(["TEST_deploy"], "forced"),
        "splitDeploySel": run(["TEST_deploy"], "selective"),
        "offline": run(["AB_noL2"], "forced"),
        "offlineSel": run(["AB_noL2"], "selective"),
        "singleCompiler": run(["AB_single"], "forced"),
        "edgeTwentyB": jsonl("AB_nocompiler_proxy20b"),
        "edgeFourB": jsonl("ZS_edge_qwen4b_test"),
    }
    conds_dev = {
        "cloudZS": jsonl("ZS_cloud_dev"),
        "splitProxy": run(["dev_train_proxy_v9", "dev_val_proxy_v9"], "forced"),
        "splitProxySel": run(["dev_train_proxy_v9", "dev_val_proxy_v9"], "selective"),
        "edgeTwentyB": jsonl("AB_nocompiler_proxy20b_dev"),
        "edgeFourB": jsonl("ZS_edge_qwen4b_dev"),
    }
    for split, conds in (("test", conds_test), ("dev", conds_dev)):
        ref = conds["cloudZS"]
        ids = test_ids if split == "test" else sorted(ref)
        for k, d in conds.items():
            if d is None:
                continue
            if set(ids) - set(d):
                missing.append(f"{split}:{k}:incomplete")
                continue
            res[split][k] = summarise(d, ids)
            if k != "cloudZS" and not k.endswith("Sel") and ref is not None:
                res["vs_cloud_zs"][split][k] = versus(d, ref, ids)
        for k in ("edgeFourB",):
            d = conds.get(k)
            if d and all(v.get("latency") for v in d.values()):
                lat = sorted(v["latency"] for v in d.values())
                res[split][k]["latency_s_median"] = lat[len(lat) // 2]
                res[split][k]["latency_s_p95"] = lat[int(0.95 * (len(lat) - 1))]
    # Same local 4B model, two uses: reading the full note vs the compiled SPLIT-Match pipeline.
    a, b = conds_test.get("edgeFourB"), conds_test.get("splitDeploy")
    if a and b and not (set(test_ids) - set(a)) and not (set(test_ids) - set(b)):
        res["fourB_vs_splitDeploy_test"] = versus(a, b, test_ids)
    res["missing"] = sorted(set(missing))
    (R / "PAPER_NUMBERS.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")

    # ── LaTeX macros ─────────────────────────────────────────────────────
    OUT.mkdir(parents=True, exist_ok=True)
    lines = ["% generated by experiments/paper_numbers.py -- do not edit by hand",
             "\\providecommand{\\pending}{\\textcolor{red}{[pending]}}"]

    def pfmt(p):
        """p-value for use inside math mode: 0.11, 0.0018, 2\\times10^{-10}."""
        if p >= 0.001:
            return "{:.2g}".format(p)
        m, e = "{:.0e}".format(p).split("e")
        return f"{m}\\times10^{{{int(e)}}}"

    def mac(name, val, fmt="{:.3f}"):
        if val is None:
            s = "\\pending"
        elif fmt == "p":
            s = pfmt(val)
        else:
            s = fmt.format(val)
        s = s.replace("%", "\\%")
        lines.append(f"\\newcommand{{\\{name}}}{{{s}}}")

    lt = res["test"].get("edgeFourB", {})
    mac("edgeFourBLatMed", lt.get("latency_s_median"), "{:.0f}")
    mac("edgeFourBLatPnf", lt.get("latency_s_p95"), "{:.0f}")
    fv = res.get("fourB_vs_splitDeploy_test")
    mac("fourBvsSplitDiff", fv and fv["acc_diff"], "{:+.3f}")
    mac("fourBvsSplitLo", fv and fv["acc_diff_ci95"][0], "{:+.3f}")
    mac("fourBvsSplitHi", fv and fv["acc_diff_ci95"][1], "{:+.3f}")
    mac("fourBvsSplitMcp", fv and fv["mcnemar"]["p_exact"], "p")

    for split in ("test", "dev"):
        sp = "T" if split == "test" else "D"
        for k in list(conds_test) + list(conds_dev):
            m = res[split].get(k)
            mac(f"acc{sp}{k}", m and m["acc"])
            mac(f"fone{sp}{k}", m and m["f1"])
            mac(f"cov{sp}{k}", m and m["coverage"], "{:.1%}")
            mac(f"accdec{sp}{k}", m and m.get("acc_decided"))
            mac(f"acclo{sp}{k}", m and m["acc_ci95"][0])
            mac(f"acchi{sp}{k}", m and m["acc_ci95"][1])
            v = res["vs_cloud_zs"][split].get(k)
            mac(f"diff{sp}{k}", v and v["acc_diff"], "{:+.3f}")
            mac(f"difflo{sp}{k}", v and v["acc_diff_ci95"][0], "{:+.3f}")
            mac(f"diffhi{sp}{k}", v and v["acc_diff_ci95"][1], "{:+.3f}")
            mac(f"mcp{sp}{k}", v and v["mcnemar"]["p_exact"], "p")
    # ── privacy, edge cost, fidelity, stress, audit (read from the saved analysis files)
    def load(name):
        f = R / name
        if not f.exists():
            missing.append(name)
            return {}
        return json.loads(f.read_text(encoding="utf-8"))

    dep, prx = load("ANALYSIS_TEST_deploy.json"), load("ANALYSIS_TEST_proxy.json")
    ext, strs = load("ANALYSIS_EXTRA.json"), load("ANALYSIS_STRESS_TEST_proxy_proxy.json")
    fid = load("FIDELITY_TEST_deploy_vs_TEST_proxy.json")
    h2d, h2p = dep.get("H2_privacy", {}), prx.get("H2_privacy", {})
    mac("privCallsDeploy", h2d.get("calls_by_channel", {}).get("cloud_fact"), "{:d}")
    mac("privViolDeploy", h2d.get("raw_egress_violations"), "{:d}")
    mac("privOfflineDeploy", h2d.get("offline_decided_share"), "{:.1%}")
    mac("privOfflineProxy", h2p.get("offline_decided_share"), "{:.1%}")
    mac("privLtwoDeploy", h2d.get("l2_calls_per_pair_mean"), "{:.2f}")
    mac("privFieldsDeploy", h2d.get("disclosed_fields_per_escalated_pair", {}).get("median"), "{:.0f}")
    mac("privKtwoDeploy", h2d.get("k_anonymity", {}).get("share_k_ge_2"), "{:.1%}")
    mac("privCallsProxy", h2p.get("calls_by_channel", {}).get("cloud_fact"), "{:d}")
    h3 = dep.get("H3_edge", {})
    mac("edgeStructPfifty", h3.get("structure_s_p50"), "{:.0f}")
    mac("edgeStructPnf", h3.get("structure_s_p95"), "{:.0f}")
    mac("edgeEvalMs", h3.get("eval_ms_mean"), "{:.2f}")
    import re
    l1 = sorted(float(x) for x in re.findall(r"\] L1 P\d+: \d+ statements \(([\d.]+)s\)",
                                              (Path(paths.RESULTS).parent / "runtime" / "TEST_deploy.log")
                                              .read_text(encoding="utf-8", errors="ignore")))
    mac("edgeLoneMedian", l1[len(l1) // 2] if l1 else None, "{:.0f}")
    mac("edgeLonePnf", l1[int(0.95 * (len(l1) - 1))] if l1 else None, "{:.0f}")
    # Per-patient CPU time: SPLIT-Match = median structuring + median batched L1;
    # full-note 4B = median over patients of the summed per-pair latencies.
    sp = (h3.get("structure_s_p50") + l1[len(l1) // 2]) if (l1 and h3.get("structure_s_p50")) else None
    mac("edgeSplitPerPatient", sp, "{:.0f}")
    d4 = conds_test.get("edgeFourB")
    pp = None
    if d4 and all(v.get("latency") for v in d4.values()):
        per = {}
        for pid, v in d4.items():
            per[pid.split("__")[0]] = per.get(pid.split("__")[0], 0) + v["latency"]
        pv = sorted(per.values())
        pp = pv[len(pv) // 2]
    mac("edgeFourBPerPatient", pp, "{:.0f}")
    mac("edgeCostRatio", sp / pp if (sp and pp) else None, "{:.1f}")
    mac("fidForced", fid.get("forced_decision_agreement"), "{:.1%}")
    mac("fidVerified", fid.get("field_agreement_on_verified"), "{:.1%}")
    h4 = strs.get("H4_redaction", {})
    mac("redAffected", h4.get("affected_pairs"), "{:d}")
    mac("redCwSplit", h4.get("committed_wrong_split_selective"), "{:.1%}")
    mac("redCwZs", h4.get("committed_wrong_zero_shot"), "{:.1%}")
    mac("redCwLo", h4.get("diff_ci95_trial", [None])[0], "{:+.3f}")
    mac("redCwHi", (h4.get("diff_ci95_trial") or [None, None])[1], "{:+.3f}")
    mac("redAsk", h4.get("ask_recall_removed_category"), "{:.0%}")
    mac("redAccRed", h4.get("forced_acc_redacted"), "{:.3f}")
    mac("redAccAns", h4.get("forced_acc_after_one_answer"), "{:.3f}")
    mac("redAccZs", h4.get("zero_shot_acc_redacted"), "{:.3f}")
    h6 = strs.get("H6_counterfactual", {})
    mac("cfFlipSplit", h6.get("flip_rate_split"), "{:.1%}")
    mac("cfFlipZs", h6.get("flip_rate_zero_shot"), "{:.1%}")
    mac("cfMcp", h6.get("mcnemar_flips", {}).get("p_exact"), "p")
    h8 = ext.get("H8") or {}
    mac("noisyDeltaSplit", h8.get("split_delta_f1"), "{:+.3f}")
    mac("noisyDeltaZs", h8.get("zs_delta_f1"), "{:+.3f}")
    mac("noisyDidLo", (h8.get("ci95") or [None])[0], "{:+.3f}")
    mac("noisyDidHi", (h8.get("ci95") or [None, None])[1], "{:+.3f}")
    mac("noisyAccSplit", h8.get("split_acc_noisy"), "{:.3f}")
    mac("noisyAccZs", h8.get("zs_acc_noisy"), "{:.3f}")
    ab = ext.get("ablations", {})
    for k, n in (("AB_single", "Single"), ("AB_noL1", "NoLone"), ("AB_noL2", "NoLtwo"), ("AB_hardveto", "Veto"),
                 ("AB_boolean", "Bool"), ("AB_noverify", "NoVerify")):
        a = ab.get(k, {})
        mac(f"ab{n}Acc", a.get("forced", {}).get("acc_all"), "{:.3f}")
        mac(f"ab{n}Diff", a.get("acc_diff_vs_full"), "{:+.3f}")
        mac(f"ab{n}Lo", (a.get("acc_diff_ci95") or [None])[0], "{:+.3f}")
        mac(f"ab{n}Hi", (a.get("acc_diff_ci95") or [None, None])[1], "{:+.3f}")
        mac(f"ab{n}Mcp", a.get("mcnemar_vs_full", {}).get("p_exact"), "p")
    h5 = ext.get("H5", {})
    mac("aurcSplit", dep.get("H5_aurc", {}).get("split_u"), "{:.3f}")
    mac("aurcZs", dep.get("H5_aurc", {}).get("zero_shot"), "{:.3f}")
    fe = load("fresh/extraction_local.json") if (R / "fresh" / "extraction_local.json").exists() else {}
    if not fe:
        missing.append("fresh/extraction_local.json")
    fp = load("fresh/extraction_proxy.json")
    for tag, e in (("Proxy", fp), ("Local", fe)):
        mac(f"ext{tag}Recall", e.get("field_recall_correct"), "{:.1%}")
        mac(f"ext{tag}Prec", e.get("precision_extracted"), "{:.1%}")
        mac(f"ext{tag}Verified", e.get("share_verified"), "{:.1%}")
        mac(f"ext{tag}VerPrec", e.get("verified_precision"), "{:.1%}")
        mac(f"ext{tag}UnverPrec", e.get("unverified_precision"), "{:.1%}")
        uf, up = e.get("unverified_facts"), e.get("unverified_precision")
        vf, vp = e.get("verified_facts"), e.get("verified_precision")
        mac(f"ext{tag}WrongUnver", round(uf * (1 - up)) if uf is not None and up is not None else None, "{:d}")
        mac(f"ext{tag}WrongVer", round(vf * (1 - vp)) if vf is not None and vp is not None else None, "{:d}")
    res["h5_extra"] = h5
    # ── review analyses (experiments/review_analysis.py; exploratory) ────────
    rv = load("REVIEW_ANALYSIS.json")
    cl = rv.get("clinical", {})
    tagmap = {"cloudZS": "CloudZS", "cloudRecord_deployFS": "RecDeploy", "cloudRecord_proxyFS": "RecProxy",
              "splitDeploy": "SplitDeploy", "offline": "Offline", "edgeTwentyB": "EdgeTwentyB",
              "edgeFourB": "EdgeFourB", "qwen27b": "QwenTwentySeven", "qwen3_1p7b_local": "QwenOneSeven"}
    for k, t in tagmap.items():
        c = cl.get(k, {})
        mac(f"rec{t}", c.get("recall"), "{:.3f}")
        mac(f"prec{t}", c.get("precision"), "{:.3f}")
        mac(f"miss{t}", c.get("missed_eligible"), "{:d}")
        mac(f"unref{t}", c.get("unnecessary_referrals"), "{:d}")
        p100 = c.get("per100_patients", {})
        mac(f"missHundred{t}", p100.get("missed_eligible"), "{:.1f}")
        mac(f"unrefHundred{t}", p100.get("unnecessary_referrals"), "{:.1f}")
        mac(f"recDiff{t}", c.get("recall_diff"), "{:+.3f}")
        for m, mm in (("trial", "Tr"), ("patient", "Pa"), ("twoway", "Tw")):
            ci = c.get(f"recall_diff_ci_{m}")
            mac(f"recLo{mm}{t}", ci and ci[0], "{:+.3f}")
            mac(f"recHi{mm}{t}", ci and ci[1], "{:+.3f}")
            ca = c.get(f"acc_diff_ci_{m}")
            mac(f"accLo{mm}{t}", ca and ca[0], "{:+.3f}")
            mac(f"accHi{mm}{t}", ca and ca[1], "{:+.3f}")
    nz = rv.get("noise", {})
    mac("nfCloudMean", nz.get("cloud_mean"), "{:.3f}")
    mac("nfCloudSd", nz.get("cloud_sd"), "{:.3f}")
    mac("nfCloudRuns", len(nz.get("cloud_runs_acc", {})) or None, "{:d}")
    mac("nfEdgeMean", nz.get("edge20b_mean"), "{:.3f}")
    mac("nfEdgeSd", nz.get("edge20b_sd"), "{:.3f}")
    mac("nfEdgeRuns", len(nz.get("edge20b_runs_acc", {})) or None, "{:d}")
    mac("nfCloudMaxGap", nz.get("cloud_max_between_run_gap"), "{:.3f}")
    mac("nfAvgDiff", nz.get("run_averaged_diff_edge20b_minus_cloud"), "{:+.3f}")
    ci = nz.get("run_averaged_diff_ci_trial")
    mac("nfAvgLo", ci and ci[0], "{:+.3f}")
    mac("nfAvgHi", ci and ci[1], "{:+.3f}")
    ag = nz.get("cloud_pairwise_agreement") or []
    mac("nfCloudAgreeMin", min(ag) if ag else None, "{:.1%}")
    cap = rv.get("capacity", {})
    for k, t in (("qwen3_1p7b_local", "OneSeven"), ("edgeFourB", "Four"), ("qwen27b", "TwentySeven"),
                 ("edgeTwentyB", "TwentyB"), ("cloudZS", "OneTwenty")):
        c = cap.get(k, {})
        mac(f"cap{t}Acc", c.get("acc"), "{:.3f}")
        mac(f"cap{t}Diff", c.get("acc_diff_vs_cloud"), "{:+.3f}")
    ln = rv.get("long_notes", {})
    for k, t in (("cloud120b", "Cloud"), ("edge20b", "TwentyB"), ("edge4b", "Four")):
        c = ln.get(k, {})
        mac(f"long{t}Short", c.get("acc_short"), "{:.3f}")
        mac(f"long{t}Acc", c.get("acc_long"), "{:.3f}")
        mac(f"long{t}Delta", c.get("delta"), "{:+.3f}")
        ci = c.get("delta_ci_trial")
        mac(f"long{t}Lo", ci and ci[0], "{:+.3f}")
        mac(f"long{t}Hi", ci and ci[1], "{:+.3f}")
    nt = ln.get("notes", {})
    mac("longWordsMed", nt.get("words_long_median"), "{:d}")
    mac("longWordsMin", nt.get("words_long_min"), "{:d}")
    mac("longWordsMax", nt.get("words_long_max"), "{:d}")
    mac("longFiller", nt.get("filler_sentences"), "{:d}")
    mac("longDropped", nt.get("filler_dropped_by_screen"), "{:d}")
    cv = rv.get("coverage", {})
    mac("covOfflineAcc", cv.get("offline_split_acc_decided"), "{:.3f}")
    for k, t in (("cloudZS", "Cloud"), ("edgeTwentyB", "TwentyB"), ("edgeTwentyB_local", "TwentyBLocal"), ("edgeFourB", "Four")):
        c = cv.get(k, {})
        mac(f"cov{t}Acc", c.get("acc_at_same_coverage"), "{:.3f}")
        mac(f"cov{t}Diff", c.get("offline_minus_model"), "{:+.3f}")
        ci = c.get("diff_ci_trial")
        mac(f"cov{t}Lo", ci and ci[0], "{:+.3f}")
        mac(f"cov{t}Hi", ci and ci[1], "{:+.3f}")
    bw = rv.get("bandwidth", {})
    for k, t in (("full_note", "Full"), ("record_deploy", "Record"), ("facts_deploy", "Facts")):
        mac(f"bw{t}", (bw.get(k) or {}).get("median_chars_per_patient"), "{:,d}")
    os_ = rv.get("outage_sim", {})
    for av, t in (("0.7", "Seventy"), ("0.5", "Fifty")):
        o = os_.get(av, {})
        mac(f"out{t}Cloud", (o.get("cloud_full_note") or {}).get("completion_rate"), "{:.0%}")
        mac(f"out{t}Split", (o.get("split_match_deploy") or {}).get("completion_rate"), "{:.0%}")
        mac(f"out{t}Edge", (o.get("edge_4b_full_note") or {}).get("completion_rate"), "{:.0%}")
    un = rv.get("uniqueness", {})
    mac("uniqRecord", (un.get("record_level") or {}).get("100000"), "{:.1%}")
    mac("uniqFact", (un.get("fact_level_mean_uniqueness_over_payloads") or {}).get("100000"), "{:.1%}")
    mac("uniqLinked", (un.get("fact_level_linked_per_patient_mean_uniqueness") or {}).get("100000"), "{:.1%}")
    l20 = (rv.get("local20b") or {})
    l20 = l20.get("LOC_gptoss20b_sub40") or l20.get("LOC_gptoss20b_pilot") or {}
    mac("locPairs", l20.get("pairs_ok"), "{:d}")
    mac("locAcc", l20.get("acc"), "{:.3f}")
    mac("locHostedAcc", l20.get("hosted_acc_same_pairs"), "{:.3f}")
    mac("locAgree", l20.get("agreement_with_hosted"), "{:.1%}")
    mac("locLatMed", l20.get("latency_p50_s"), "{:.0f}")
    mac("locLatPnf", l20.get("latency_p95_s"), "{:.0f}")
    mac("locGenTps", l20.get("gen_tok_per_s_median"), "{:.1f}")
    mac("locPromptTps", l20.get("prompt_tok_per_s_median"), "{:.1f}")
    mac("locPeakRamGb", (l20.get("peak_ram_mb") or 0) / 1024 if l20.get("peak_ram_mb") else None, "{:.1f}")
    # same device model, read vs compiled: all three clustering schemes (round-2 review)
    sm = rv.get("same_model") or {}
    for m, mm in (("trial", "Tr"), ("patient", "Pa"), ("twoway", "Tw")):
        ci = sm.get(f"acc_diff_ci_{m}")
        mac(f"fourBvsSplitLo{mm}", ci and ci[0], "{:+.3f}")
        mac(f"fourBvsSplitHi{mm}", ci and ci[1], "{:+.3f}")
        cr = sm.get(f"recall_diff_ci_{m}")
        mac(f"fourBvsSplitRecLo{mm}", cr and cr[0], "{:+.3f}")
        mac(f"fourBvsSplitRecHi{mm}", cr and cr[1], "{:+.3f}")
    mac("fourBvsSplitRecDiff", sm.get("recall_diff"), "{:+.3f}")
    for k, pre in (("recall_read", "RecRead"), ("recall_compiled", "RecComp"), ("acc_read", "AccRead"),
                   ("acc_compiled", "AccComp")):
        mac(f"fourBvsSplit{pre}", sm.get(k), "{:.3f}")
    mac("fourBvsSplitMissRead", sm.get("missed_read"), "{:d}")
    mac("fourBvsSplitMissComp", sm.get("missed_compiled"), "{:d}")
    # second device model (round-3 review): hosted gpt-oss-20b, pre-specified -compiler ablation
    tw = sm.get("gptoss20b_hosted") or {}
    mac("twentyVsSplitDiff", tw.get("acc_diff"), "{:+.3f}")
    mac("twentyVsSplitRecDiff", tw.get("recall_diff"), "{:+.3f}")
    mac("twentyVsSplitAccRead", tw.get("acc_read"), "{:.3f}")
    mac("twentyVsSplitAccComp", tw.get("acc_compiled"), "{:.3f}")
    mac("twentyVsSplitRecRead", tw.get("recall_read"), "{:.3f}")
    mac("twentyVsSplitRecComp", tw.get("recall_compiled"), "{:.3f}")
    mac("twentyVsSplitMissRead", tw.get("missed_read"), "{:d}")
    mac("twentyVsSplitMissComp", tw.get("missed_compiled"), "{:d}")
    mac("twentyVsSplitMcp", (tw.get("mcnemar") or {}).get("p_exact"), "p")
    mc = tw.get("mcnemar") or {}
    mac("twentyVsSplitMcA", mc.get("A_only_correct"), "{:d}")
    mac("twentyVsSplitMcB", mc.get("B_only_correct"), "{:d}")
    for m, mm in (("trial", "Tr"), ("patient", "Pa"), ("twoway", "Tw")):
        ci = tw.get(f"acc_diff_ci_{m}")
        mac(f"twentyVsSplitLo{mm}", ci and ci[0], "{:+.3f}")
        mac(f"twentyVsSplitHi{mm}", ci and ci[1], "{:+.3f}")
        cr = tw.get(f"recall_diff_ci_{m}")
        mac(f"twentyVsSplitRecLo{mm}", cr and cr[0], "{:+.3f}")
        mac(f"twentyVsSplitRecHi{mm}", cr and cr[1], "{:+.3f}")
    # ── round-5 review: missed-patient inference, decomposition, outage sensitivity, gateway suite, repeats
    ms = rv.get("missed") or {}
    tags = {"cloudZS": "Cloud", "cloudRecord_deployFS": "Rec", "splitDeploy": "Split", "offline": "Off",
            "edgeFourB": "Four", "edgeTwentyB_local": "TwLoc", "edgeTwentyB": "TwHost", "qwen27b": "TwSev",
            "qwen3_1p7b_local": "OneSev"}
    for k, t in tags.items():
        m = ms.get(k) or {}
        ci = m.get("recall_ci_trial")
        mac(f"rec{t}", m.get("recall"), "{:.3f}")
        mac(f"rec{t}Lo", ci and ci[0], "{:.3f}")
        mac(f"rec{t}Hi", ci and ci[1], "{:.3f}")
        mac(f"recD{t}", m.get("recall_diff_vs_cloud"), "{:+.3f}")
        for sch, ss in (("trial", "Tr"), ("patient", "Pa"), ("twoway", "Tw")):
            c2 = m.get(f"recall_diff_ci_{sch}")
            mac(f"recD{t}Lo{ss}", c2 and c2[0], "{:+.3f}")
            mac(f"recD{t}Hi{ss}", c2 and c2[1], "{:+.3f}")
        mc = m.get("mcnemar_eligible_only") or {}
        mac(f"mcE{t}A", mc.get("A_only_correct"), "{:d}")
        mac(f"mcE{t}B", mc.get("B_only_correct"), "{:d}")
        mac(f"mcE{t}P", mc.get("p_exact"), "p")
    dc = rv.get("decomposition") or {}
    for k, t in (("gptoss20b_hosted", "Tw"), ("qwen4b_laptop", "Four")):
        d = dc.get(k) or {}
        ok = bool(d.get("complete"))
        for inp, ii in (("note", "Note"), ("fact_sheet", "Fs"), ("rules", "Rules")):
            x = (d.get(inp) or {}) if ok else {}
            mac(f"dec{t}{ii}Acc", x.get("acc"), "{:.3f}")
            mac(f"dec{t}{ii}Rec", x.get("recall"), "{:.3f}")
            mac(f"dec{t}{ii}Miss", x.get("missed"), "{:d}")
            mac(f"dec{t}{ii}Unn", x.get("unnecessary"), "{:d}")
        for step, sp in (("note_minus_fact_sheet", "NF"), ("fact_sheet_minus_rules", "FR")):
            x = (d.get(step) or {}) if ok else {}
            mac(f"dec{t}{sp}Acc", x.get("acc_diff"), "{:+.3f}")
            mac(f"dec{t}{sp}Rec", x.get("recall_diff"), "{:+.3f}")
            mac(f"dec{t}{sp}Mcp", (x.get("mcnemar") or {}).get("p_exact"), "p")
            for sch, ss in (("trial", "Tr"), ("twoway", "Tw")):
                c3 = x.get(f"acc_diff_ci_{sch}")
                mac(f"dec{t}{sp}AccLo{ss}", c3 and c3[0], "{:+.3f}")
                mac(f"dec{t}{sp}AccHi{ss}", c3 and c3[1], "{:+.3f}")
                c4 = x.get(f"recall_diff_ci_{sch}")
                mac(f"dec{t}{sp}RecLo{ss}", c4 and c4[0], "{:+.3f}")
                mac(f"dec{t}{sp}RecHi{ss}", c4 and c4[1], "{:+.3f}")
    osn = rv.get("outage_sensitivity") or {}
    for up, uu in (("5.0", "Five"), ("30.0", "Thirty"), ("120.0", "OneTwenty")):
        x = (osn.get(up) or {}).get("0.5") or {}
        mac(f"outHalf{uu}Cloud", x.get("cloud_full_note"), "{:.1%}")
        mac(f"outHalf{uu}Split", x.get("split_match_deploy"), "{:.1%}")
    gs = load("review/GATEWAY_SUITE.json") or {}
    cs = gs.get("cases") or {}

    def gcase(prefix):
        return next((v for k, v in cs.items() if k.startswith(prefix)), {})
    for pre, t in (("P1", "Exact"), ("P2", "Case"), ("P3", "Embed"), ("P4", "Pid"), ("P5", "Pairid"),
                   ("P6", "Half"), ("P7", "Drop"), ("P8", "Punct"), ("P9", "Btsf"), ("A1", "FactOk"),
                   ("A2", "PubOk")):
        g = gcase(pre)
        mac(f"gw{t}N", g.get("n"), "{:d}")
        mac(f"gw{t}Rate", g.get("block_rate"), "{:.1%}")
    rt = gs.get("real_traffic_partial_overlap") or {}
    mac("gwRealN", rt.get("fact_queries"), "{:d}")
    mac("gwRealFive", rt.get("queries_with_ge_5_words"), "{:d}")
    mac("gwRealFiveShare", rt.get("queries_with_ge_5_words") and rt["queries_with_ge_5_words"] / rt["fact_queries"],
        "{:.1%}")
    mac("gwRealMax", rt.get("max_consecutive_note_words_not_in_criteria"), "{:d}")
    mac("gwShortUnprot", (gs.get("unprotected_note_sentences") or {}).get("shorter_than_25_chars"), "{:d}")
    mac("gwRegistered", gs.get("registered_sentences"), "{:d}")
    lr = rv.get("local_repeats") or {}
    for k, t in (("qwen4b_full_test", "Four"), ("gptoss20b_sub40", "Tw")):
        x = lr.get(k) or {}
        ok = bool(x.get("complete"))
        g = (lambda kk: x.get(kk)) if ok else (lambda kk: None)
        mac(f"rep{t}Agree", g("agreement_with_first_run"), "{:.1%}")
        mac(f"rep{t}AccFirst", g("acc_first_run_same_pairs"), "{:.3f}")
        mac(f"rep{t}AccRep", g("acc_repeat"), "{:.3f}")
        mac(f"rep{t}LatMed", g("latency_p50_s"), "{:.0f}")
        mac(f"rep{t}LatPnf", g("latency_p95_s"), "{:.0f}")
        mac(f"rep{t}Cold", g("cold_load_s"), "{:.0f}")
        mac(f"rep{t}RamGb", g("peak_ram_mb") and g("peak_ram_mb") / 1024, "{:.1f}")
    un = rv.get("uniqueness") or {}
    mac("uniqRecordTenK", (un.get("record_level") or {}).get("10000"), "{:.1%}")
    mac("uniqLinkedTenK", (un.get("fact_level_linked_per_patient_mean_uniqueness") or {}).get("10000"), "{:.1%}")
    # round-6 review: which exclusion route produced the missed patients (experiments/l2_attribution.py)
    la = load("review/L2_ATTRIBUTION.json") or {}
    ex = la.get("extra_misses_with_l2") or {}
    exr = ex.get("by_route") or {}
    mac("ltwoProxyMiss", (la.get("TEST_proxy") or {}).get("missed"), "{:d}")
    mac("ltwoNoMiss", (la.get("AB_noL2") or {}).get("missed"), "{:d}")
    mac("ltwoExtra", ex.get("n"), "{:d}")
    mac("ltwoExtraTwoKey", exr.get("two keys incl. cloud judge"), "{:d}")
    mac("ltwoExtraAlone", exr.get("cloud judge alone (forced mode)"), "{:d}")
    dr = (la.get("TEST_deploy") or {}).get("by_route") or {}
    mac("ltwoDeployMiss", (la.get("TEST_deploy") or {}).get("missed"), "{:d}")
    mac("ltwoDeployCloud", (dr.get("two keys incl. cloud judge") or 0) + (dr.get("cloud judge alone (forced mode)") or 0)
        if dr else None, "{:d}")
    sel = ex.get("selective_without_l2") or {}
    mac("ltwoExtraAsk", sel.get("NEED_INFO"), "{:d}")
    mac("ltwoExtraDefer", sel.get("DEFER"), "{:d}")
    # fact queries: calls vs distinct messages
    mac("privDistinctDeploy", (load("review/GATEWAY_SUITE.json") or {}).get("cases", {})
        .get("A1 real fact queries (laptop run)", {}).get("n"), "{:d}")
    # gpt-oss-20b on the laptop, all 270 pairs (round-2 review); pending until the run completes
    lf = rv.get("local20b_full") or {}
    full = bool(lf.get("complete"))
    g = (lambda k: lf.get(k)) if full else (lambda k: None)
    lc = (lf.get("clinical") or {}) if full else {}
    mac("locFullAcc", lc.get("acc"), "{:.3f}")
    ci = g("acc_ci_trial")
    mac("locFullAccLo", ci and ci[0], "{:.3f}")
    mac("locFullAccHi", ci and ci[1], "{:.3f}")
    cap = rv.get("capacity") or {}
    mac("capOneSevenLat", (cap.get("qwen3_1p7b_local") or {}).get("laptop_latency_p50_s"), "{:.0f}")
    mac("capFourLat", (cap.get("edgeFourB") or {}).get("laptop_latency_p50_s"), "{:.0f}")
    mac("locFullRec", lc.get("recall"), "{:.3f}")
    mac("locFullMiss", lc.get("missed_eligible"), "{:d}")
    mac("locFullUnref", lc.get("unnecessary_referrals"), "{:d}")
    mac("locFullMissHundred", (lc.get("per100_patients") or {}).get("missed_eligible"), "{:.1f}")
    mac("locFullUnrefHundred", (lc.get("per100_patients") or {}).get("unnecessary_referrals"), "{:.1f}")
    mac("locFullDiff", g("acc_diff_vs_cloud"), "{:+.3f}")
    mac("locFullRecDiff", g("recall_diff_vs_cloud"), "{:+.3f}")
    for m, mm in (("trial", "Tr"), ("patient", "Pa"), ("twoway", "Tw")):
        ci = g(f"acc_diff_ci_{m}")
        mac(f"locFullLo{mm}", ci and ci[0], "{:+.3f}")
        mac(f"locFullHi{mm}", ci and ci[1], "{:+.3f}")
        cr = g(f"recall_diff_ci_{m}")
        mac(f"locFullRecLo{mm}", cr and cr[0], "{:+.3f}")
        mac(f"locFullRecHi{mm}", cr and cr[1], "{:+.3f}")
    mac("locFullMcp", (g("mcnemar_vs_cloud") or {}).get("p_exact"), "p")
    mac("locFullAvgDiff", g("diff_vs_cloud_run_mean"), "{:+.3f}")
    ci = g("diff_vs_cloud_run_mean_ci_trial")
    mac("locFullAvgLo", ci and ci[0], "{:+.3f}")
    mac("locFullAvgHi", ci and ci[1], "{:+.3f}")
    mac("locFullHostedMean", g("hosted_mean_acc"), "{:.3f}")
    ag = list((g("agreement_with_hosted") or {}).values())
    mac("locFullAgreeMin", min(ag) if ag else None, "{:.1%}")
    mac("locFullAgreeMax", max(ag) if ag else None, "{:.1%}")
    mac("locFullVsHostedDiff", g("acc_diff_vs_hosted_orig"), "{:+.3f}")
    ci = g("acc_diff_vs_hosted_orig_ci_trial")
    mac("locFullVsHostedLo", ci and ci[0], "{:+.3f}")
    mac("locFullVsHostedHi", ci and ci[1], "{:+.3f}")
    mac("locFullVsHostedMcp", (g("mcnemar_vs_hosted_orig") or {}).get("p_exact"), "p")
    mac("locFullLatMed", g("latency_p50_s"), "{:.0f}")
    mac("locFullLatPnf", g("latency_p95_s"), "{:.0f}")
    mac("locFullPerPatientMin", g("per_patient_median_s") and g("per_patient_median_s") / 60, "{:.0f}")
    mac("locFullHours", g("total_cpu_hours"), "{:.1f}")
    mac("locFullGenTps", g("gen_tok_per_s_median"), "{:.1f}")
    mac("locFullPeakRamGb", g("peak_ram_mb") and g("peak_ram_mb") / 1024, "{:.1f}")
    # run-to-run spread of missed / unnecessary (45 test patients -> per 100 patients)
    for key, pre in (("cloud_runs_miss_unn", "cloudRuns"), ("hosted_runs_miss_unn", "hostedTwentyRuns")):
        rr = list((g(key) or {}).values())
        ms = [r["missed"] for r in rr]
        us = [r["unnecessary"] for r in rr]
        mac(f"{pre}MissMin", min(ms) if ms else None, "{:d}")
        mac(f"{pre}MissMax", max(ms) if ms else None, "{:d}")
        mac(f"{pre}MissMean", (sum(ms) / len(ms)) if ms else None, "{:.1f}")
        mac(f"{pre}MissHundredMin", min(ms) / 45 * 100 if ms else None, "{:.1f}")
        mac(f"{pre}MissHundredMax", max(ms) / 45 * 100 if ms else None, "{:.1f}")
        mac(f"{pre}MissHundredMean", (sum(ms) / len(ms)) / 45 * 100 if ms else None, "{:.1f}")
        mac(f"{pre}UnnMin", min(us) if us else None, "{:d}")
        mac(f"{pre}UnnMax", max(us) if us else None, "{:d}")
    mac("locVsFourDiff", g("vs_4b_acc_diff"), "{:+.3f}")
    ci = g("vs_4b_acc_diff_ci_trial")
    mac("locVsFourLo", ci and ci[0], "{:+.3f}")
    mac("locVsFourHi", ci and ci[1], "{:+.3f}")
    mac("locVsFourMcp", (g("vs_4b_mcnemar") or {}).get("p_exact"), "p")
    vc = g("vs_4b_eligible_caught_only") or {}
    mac("locVsFourCatchTwenty", vc.get("20b"), "{:d}")
    mac("locVsFourCatchFour", vc.get("4b"), "{:d}")
    o50 = (os_.get("0.5") or {}).get("edge_20b_local_full_note") or {}
    mac("outFiftyEdgeTwenty", o50.get("completion_rate"), "{:.0%}")
    lines = list(dict.fromkeys(lines))  # keys appearing in both condition lists
    (OUT / "numbers.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # ── frontier table for pgfplots: x = disclosure level (0 = nothing ... 3 = full note)
    levels = [("cloudZS", 3.0, "Cloud"), ("cloudRecordDeploy", 2.0, "Record"),
              ("splitProxy", 0.88, "SPLIT (proxy)"), ("splitDeploy", 1.12, "SPLIT (4B)"),
              ("offline", -0.14, "Offline SPLIT"), ("edgeTwentyB", 0.0, "Edge 20B"),
              ("edgeFourB", 0.14, "Edge 4B")]
    rows = ["x acc lo hi label"]
    for k, x, lab in levels:
        m = res["test"].get(k)
        if m:
            rows.append(f"{x} {m['acc']:.4f} {m['acc'] - m['acc_ci95'][0]:.4f} "
                        f"{m['acc_ci95'][1] - m['acc']:.4f} {{{lab}}}")
    (OUT / "frontier.dat").write_text("\n".join(rows) + "\n", encoding="utf-8")

    # ── Figure 1 (clinical lens): missed eligible and unnecessary referrals per 100 patients screened
    # against six trials, by where the note is read. The 20B row is the laptop run once it is complete.
    def p100(k):
        c = cl.get(k) or {}
        q = c.get("per100_patients") or {}
        return q.get("missed_eligible"), q.get("unnecessary_referrals")
    fig = [("Cloud LLM reads full note", p100("cloudZS")),
           ("Cloud LLM reads 4B record", p100("cloudRecord_deployFS")),
           ("SPLIT-Match, facts to cloud", p100("splitDeploy")),
           ("SPLIT-Match, offline", p100("offline")),
           ("Qwen3-4B reads note on device", p100("edgeFourB"))]
    if full:
        q = lc.get("per100_patients") or {}
        fig.append(("gpt-oss-20b reads note on device", (q.get("missed_eligible"), q.get("unnecessary_referrals"))))
    else:
        fig.append(("gpt-oss-20b reads note (hosted)", p100("edgeTwentyB")))
    mrows = ["label miss unnec"] + [f"{{{lab}}} {m:.1f} {u:.1f}" for lab, (m, u) in fig
                                     if m is not None and u is not None]
    (OUT / "missed.dat").write_text("\n".join(mrows) + "\n", encoding="utf-8")
    print(json.dumps({"test": {k: round(v["acc"], 4) for k, v in res["test"].items()},
                      "dev": {k: round(v["acc"], 4) for k, v in res["dev"].items()},
                      "vs_cloud_zs_test": {k: [round(v["acc_diff"], 3), [round(c, 3) for c in v["acc_diff_ci95"]],
                                               v["non_inferior_m005"]] for k, v in res["vs_cloud_zs"]["test"].items()},
                      "vs_cloud_zs_dev": {k: [round(v["acc_diff"], 3), [round(c, 3) for c in v["acc_diff_ci95"]]]
                                          for k, v in res["vs_cloud_zs"]["dev"].items()},
                      "missing": res["missing"]}, indent=1))


if __name__ == "__main__":
    main()
