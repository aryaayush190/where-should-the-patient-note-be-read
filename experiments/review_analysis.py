"""Analyses added for the TELMED pre-submission review (2026-11-09). EXPLORATORY, analysis only.

    PYTHONIOENCODING=utf-8 OPENBLAS_NUM_THREADS=1 .venv/Scripts/python experiments/review_analysis.py

Writes results/REVIEW_ANALYSIS.json and prints a short summary. Sections:
  clinical    referral sensitivity (recall), missed eligible, unnecessary referrals, per 100 patients;
              recall / accuracy differences vs cloud zero-shot with trial-, patient- and two-way
              (trial x patient) cluster bootstraps
  noise       run-to-run spread of cloud zero-shot and the 20B edge model; gap vs spread
  capacity    accuracy by edge-model size (same prompt)
  long_notes  accuracy on long cluttered notes vs the original short notes (paired)
  coverage    accuracy at matched coverage: offline SPLIT-Match selective vs confidence abstention
  bandwidth   patient bytes sent per patient at each privacy level; outage simulation
  uniqueness  population uniqueness of record-level and fact-level payloads (generator population)
  local20b    local gpt-oss-20b feasibility (RAM, tokens/s, latency, agreement with hosted)
"""
from __future__ import annotations

import json
import random
import statistics as st
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
from analyze import load_advisory, load_baseline  # noqa: E402
from paper_numbers import run  # noqa: E402
from splitmatch import paths, stats  # noqa: E402

R = paths.RESULTS
RV = R / "review"
B = 2000            # bootstrap replicates for the added sensitivity analyses
SEED = 20261109
N_TEST_PATIENTS = 45


# ── loading ──────────────────────────────────────────────────────────────────
def from_rows(rows, rep=None):
    d = {}
    for r in rows:
        if rep is not None and r.get("rep", 0) != rep:
            continue
        if "prediction" not in r:
            continue
        d[r["pair_id"]] = {"pred": int(str(r["prediction"]).lower() == "eligible"), "y": int(r["label"]),
                           "trial": r["trial_id"], "patient": r["pair_id"].split("__")[0],
                           "conf": r.get("confidence"), "latency": r.get("latency_s")}
    return d


def jsonl_rows(f: Path):
    if not f.exists():
        return []
    out = []
    for x in f.read_text(encoding="utf-8").splitlines():
        try:
            out.append(json.loads(x))
        except Exception:
            pass
    return out


def baseline(name):
    return from_rows(jsonl_rows(R / "baselines" / f"{name}.jsonl"))


def review(name, rep=None):
    return from_rows(jsonl_rows(RV / f"{name}.jsonl"), rep)


def complete(d, ids):
    return d is not None and len(d) > 0 and not (set(ids) - set(d))


# ── statistics ───────────────────────────────────────────────────────────────
def recall(d, ids):
    pos = [i for i in ids if d[i]["y"] == 1]
    return sum(d[i]["pred"] == 1 for i in pos) / len(pos) if pos else float("nan")


def acc(d, ids):
    return float(np.mean([d[i]["pred"] == d[i]["y"] for i in ids]))


def boot_diff(fn, a, b, ids, mode):
    """Bootstrap CI of fn(a)-fn(b): mode trial | patient | twoway (trial x patient, weights = product)."""
    ids = list(ids)
    rng = np.random.default_rng(SEED)
    tr = sorted({a[i]["trial"] for i in ids})
    pa = sorted({a[i]["patient"] for i in ids})
    ti = {t: k for k, t in enumerate(tr)}
    pi = {p: k for k, p in enumerate(pa)}
    T = np.array([ti[a[i]["trial"]] for i in ids])
    P = np.array([pi[a[i]["patient"]] for i in ids])
    y = np.array([a[i]["y"] for i in ids])
    ca = np.array([a[i]["pred"] == a[i]["y"] for i in ids], float)
    cb = np.array([b[i]["pred"] == b[i]["y"] for i in ids], float)
    pa_ = np.array([a[i]["pred"] for i in ids], float)
    pb_ = np.array([b[i]["pred"] for i in ids], float)
    vals = []
    for _ in range(B):
        wt = rng.multinomial(len(tr), [1 / len(tr)] * len(tr))[T] if mode in ("trial", "twoway") else 1
        wp = rng.multinomial(len(pa), [1 / len(pa)] * len(pa))[P] if mode in ("patient", "twoway") else 1
        w = np.ones(len(ids)) * wt * wp
        if fn == "acc":
            if w.sum() == 0:
                continue
            vals.append(float((w * (ca - cb)).sum() / w.sum()))
        else:  # recall
            wpos = w * (y == 1)
            if wpos.sum() == 0:
                continue
            vals.append(float((wpos * (pa_ - pb_)).sum() / wpos.sum()))
    lo, hi = np.percentile(vals, [2.5, 97.5])
    return [round(float(lo), 3), round(float(hi), 3)]


def clinical_row(d, ids):
    c = stats.confusion(d, ids)
    k = 100 / N_TEST_PATIENTS
    return {"acc": round(c["acc"], 3), "recall": round(c["recall"], 3), "precision": round(c["precision"], 3),
            "missed_eligible": c["fn"], "unnecessary_referrals": c["fp"], "referrals": c["tp"] + c["fp"],
            "per100_patients": {"referrals": round((c["tp"] + c["fp"]) * k, 1),
                                "missed_eligible": round(c["fn"] * k, 1),
                                "unnecessary_referrals": round(c["fp"] * k, 1)}}


# ── sections ─────────────────────────────────────────────────────────────────
def section_clinical(conds, ref, ids):
    out = {}
    ref = {i: {**v, "pred": 0 if v["pred"] is None else v["pred"]} for i, v in ref.items()}
    for name, d in conds.items():
        if not complete(d, ids):
            continue
        # an abstention is not a referral at pre-screening: count it as "not referred"
        d = {i: {**v, "pred": 0 if v["pred"] is None else v["pred"]} for i, v in d.items()}
        row = clinical_row(d, ids)
        if name != "cloudZS":
            row["recall_diff"] = round(recall(d, ids) - recall(ref, ids), 3)
            row["acc_diff"] = round(acc(d, ids) - acc(ref, ids), 3)
            for m in ("trial", "patient", "twoway"):
                row[f"recall_diff_ci_{m}"] = boot_diff("recall", d, ref, ids, m)
                row[f"acc_diff_ci_{m}"] = boot_diff("acc", d, ref, ids, m)
            row["recall_noninferior_m010_twoway"] = row["recall_diff_ci_twoway"][0] > -0.10
            row["acc_noninferior_m005_twoway"] = row["acc_diff_ci_twoway"][0] > -0.05
        out[name] = row
    return out


def section_noise(ids, cloud_cached, cloud_rerun, e20_orig):
    runs_c = {"cached": cloud_cached, "rerun1": cloud_rerun}
    for k in range(3):
        d = review("NF_cloud120b", k)
        if complete(d, ids):
            runs_c[f"rep{k + 1}"] = d
    runs_e = {"orig": e20_orig}
    for k in range(3):
        d = review("NF_edge20b", k)
        if complete(d, ids):
            runs_e[f"rep{k + 1}"] = d
    accs_c = {k: round(acc(v, ids), 4) for k, v in runs_c.items()}
    accs_e = {k: round(acc(v, ids), 4) for k, v in runs_e.items()}

    def pairwise_agree(runs):
        ks = list(runs)
        return [round(float(np.mean([runs[a][i]["pred"] == runs[b][i]["pred"] for i in ids])), 4)
                for x, a in enumerate(ks) for b in ks[x + 1:]]

    def mean_correct(runs):
        return {i: float(np.mean([r[i]["pred"] == r[i]["y"] for r in runs.values()])) for i in ids}

    mc, me = mean_correct(runs_c), mean_correct(runs_e)
    # run-averaged accuracy difference with a trial-cluster bootstrap over pairs
    rng = np.random.default_rng(SEED)
    tr = sorted({cloud_cached[i]["trial"] for i in ids})
    byt = defaultdict(list)
    for i in ids:
        byt[cloud_cached[i]["trial"]].append(i)
    diffs = []
    for _ in range(B):
        sub = [i for t in rng.choice(tr, len(tr)) for i in byt[t]]
        diffs.append(np.mean([me[i] - mc[i] for i in sub]))
    within_c = [a - b for x, a in enumerate(accs_c.values()) for b in list(accs_c.values())[x + 1:]]
    return {"cloud_runs_acc": accs_c, "edge20b_runs_acc": accs_e,
            "cloud_mean": round(st.mean(accs_c.values()), 4),
            "cloud_sd": round(st.pstdev(accs_c.values()), 4) if len(accs_c) > 1 else None,
            "edge20b_mean": round(st.mean(accs_e.values()), 4),
            "edge20b_sd": round(st.pstdev(accs_e.values()), 4) if len(accs_e) > 1 else None,
            "cloud_pairwise_agreement": pairwise_agree(runs_c),
            "edge20b_pairwise_agreement": pairwise_agree(runs_e),
            "cloud_max_between_run_gap": round(max(abs(x) for x in within_c), 4) if within_c else None,
            "run_averaged_diff_edge20b_minus_cloud": round(float(np.mean([me[i] - mc[i] for i in ids])), 4),
            "run_averaged_diff_ci_trial": [round(float(x), 4) for x in np.percentile(diffs, [2.5, 97.5])]}


def section_capacity(ids, ref, conds):
    rows = {}
    meta = {"qwen3_1p7b_local": ("Qwen3-1.7B", "dense", 1.7, "local CPU"),
            "edgeFourB": ("Qwen3-4B-Instruct-2507", "dense", 4.0, "local CPU"),
            "qwen27b": ("Qwen3.8-27B", "dense", 27, "hosted"),
            "edgeTwentyB": ("gpt-oss-20b", "MoE, 3.6B active", 21, "hosted"),
            "edgeTwentyB_local": ("gpt-oss-20b", "MoE, 3.6B active", 21, "local CPU"),
            "cloudZS": ("gpt-oss-120b", "MoE, 5.1B active", 117, "hosted")}
    for k, (nm, arch, size, where) in meta.items():
        d = conds.get(k)
        if not complete(d, ids):
            continue
        lat = sorted(v["latency"] for v in d.values() if v.get("latency"))
        rows[k] = {"model": nm, "arch": arch, "params_b": size, "where": where,
                   "laptop_latency_p50_s": lat[len(lat) // 2] if (where == "local CPU" and lat) else None,
                   "acc": round(acc(d, ids), 3), "recall": round(recall(d, ids), 3),
                   "acc_diff_vs_cloud": None if k == "cloudZS" else round(acc(d, ids) - acc(ref, ids), 3),
                   "acc_diff_ci_trial": None if k == "cloudZS" else boot_diff("acc", d, ref, ids, "trial")}
    return rows


def section_long(ids, pairs_short):
    out = {}
    for name, (long_name, short) in pairs_short.items():
        dl = review(long_name)
        if not complete(dl, ids) or not complete(short, ids):
            continue
        out[name] = {"acc_short": round(acc(short, ids), 3), "acc_long": round(acc(dl, ids), 3),
                     "delta": round(acc(dl, ids) - acc(short, ids), 3),
                     "delta_ci_trial": boot_diff("acc", dl, short, ids, "trial"),
                     "recall_short": round(recall(short, ids), 3), "recall_long": round(recall(dl, ids), 3),
                     "mcnemar": stats.mcnemar(dl, short, ids)}
    f = RV / "long_notes_screened.json"
    if f.exists():
        d = json.loads(f.read_text(encoding="utf-8"))
        w = sorted(v["words_long"] for v in d.values())
        out["notes"] = {"n": len(d), "words_long_median": w[len(w) // 2], "words_long_min": w[0],
                        "words_long_max": w[-1], "filler_sentences": sum(v["n_filler"] for v in d.values()),
                        "filler_dropped_by_screen": sum(v["n_dropped"] for v in d.values())}
    return out


def acc_at_coverage(d, ids, cov):
    """Expected accuracy when abstaining on the least confident pairs until coverage = cov.
    Pairs tied on confidence at the cut-off are included at random (expectation over ties)."""
    k = cov * len(ids)
    groups = defaultdict(list)
    for i in ids:
        groups[d[i].get("conf") or 0.0].append(d[i]["pred"] == d[i]["y"])
    taken, correct = 0.0, 0.0
    for c in sorted(groups, reverse=True):
        g = groups[c]
        if taken + len(g) <= k:
            taken += len(g)
            correct += sum(g)
        else:
            frac = (k - taken) / len(g)
            correct += frac * sum(g)
            taken = k
            break
    return correct / taken if taken else float("nan")


def section_coverage(ids, offline_sel, conds):
    def off_stats(sub):
        dec = [i for i in sub if offline_sel[i]["pred"] is not None]
        return len(dec) / len(sub), float(np.mean([offline_sel[i]["pred"] == offline_sel[i]["y"] for i in dec]))

    cov, a_off = off_stats(ids)
    out = {"coverage": round(cov, 3), "offline_split_acc_decided": round(a_off, 3)}
    rng = np.random.default_rng(SEED)
    byt = defaultdict(list)
    for i in ids:
        byt[offline_sel[i]["trial"]].append(i)
    tr = sorted(byt)
    for k, d in conds.items():
        if not (complete(d, ids) and all(d[i].get("conf") is not None for i in ids)):
            continue
        diffs = []
        for _ in range(B):
            sub = [i for t in rng.choice(tr, len(tr)) for i in byt[t]]
            c, a = off_stats(sub)
            diffs.append(a - acc_at_coverage(d, sub, c))
        out[k] = {"acc_at_same_coverage": round(acc_at_coverage(d, ids, cov), 3),
                  "offline_minus_model": round(a_off - acc_at_coverage(d, ids, cov), 3),
                  "diff_ci_trial": [round(float(x), 3) for x in np.percentile(diffs, [2.5, 97.5])],
                  "distinct_confidence_values": len({d[i]["conf"] for i in ids})}
    return out


def section_bandwidth():
    """Characters sent to the cloud per patient (ASCII text, so characters ~ bytes)."""
    per = defaultdict(lambda: defaultdict(int))
    notes = {}
    import pandas as pd
    from splitmatch import data
    p = data.load_pairs("test")
    notes = dict(p.drop_duplicates("patient_id")[["patient_id", "note"]].values)
    runs = {"zs:ZS_cloud_test_rerun": "full_note", "rec:REC_cloud_test_proxy": "record_proxy",
            "rec:REC_cloud_test_deploy": "record_deploy", "run:TEST_deploy": "facts_deploy",
            "run:TEST_proxy": "facts_proxy"}
    seen = set()
    with open(paths.LLM_LOG, encoding="utf-8") as f:
        for line in f:
            try:
                r = json.loads(line)
            except Exception:
                continue
            lvl = runs.get(r.get("run_id"))
            if not lvl or r.get("channel") not in ("baseline_cloud", "cloud_fact"):
                continue
            key = (lvl, r.get("cache_key"), r.get("local_ref"))
            if key in seen:
                continue
            seen.add(key)
            pid = str(r.get("local_ref", "")).split("__")[0]
            if not pid.startswith("P"):
                continue
            pl = r.get("payload", "")
            if lvl == "full_note":
                patient = len(notes.get(pid, ""))           # patient part only; criteria are public
            elif lvl.startswith("record"):
                s = pl.split("PATIENT RECORD (structured, de-identified):", 1)[-1]
                patient = len(s.split("TRIAL INCLUSION CRITERIA:", 1)[0].strip())
            else:
                patient = len(pl.split("PATIENT FACTS:", 1)[-1].strip()) if "PATIENT FACTS:" in pl else 0
            per[lvl][pid] += patient
            per[lvl + "_total_incl_public"][pid] += r.get("payload_chars", 0)
    out = {}
    for lvl, d in per.items():
        v = sorted(d.values())
        out[lvl] = {"patients": len(v), "median_chars_per_patient": v[len(v) // 2] if v else 0,
                    "mean_chars_per_patient": round(st.mean(v), 1) if v else 0}
    out["nothing"] = {"median_chars_per_patient": 0}
    return out


def outage_sim(calls_per_patient, local_s, call_s=6.0, up_min=30.0, avail=0.9, window_min=30.0,
               retry_s=30.0, n=5000, seed=SEED):
    """Two-state on/off link (exponential up/down periods). Each cloud call needs the link up when
    attempted; failed attempts retry every retry_s. Returns completion rate within the window and
    median time to decision for completed patients."""
    rnd = random.Random(seed)
    down_min = up_min * (1 - avail) / avail if avail < 1 else 0.0
    done, times = 0, []
    for _ in range(n):
        up = rnd.random() < avail
        left = rnd.expovariate(1 / (up_min if up else max(down_min, 1e-9))) * 60
        t = 0.0
        need = calls_per_patient

        def advance(dt):
            nonlocal t, up, left
            while dt > 0:
                step = min(dt, left)
                t += step
                dt -= step
                left -= step
                if left <= 0:
                    up = not up
                    left = rnd.expovariate(1 / (up_min if up else max(down_min, 1e-9))) * 60
        advance(local_s)
        while need > 0 and t < window_min * 60:
            if up:
                advance(call_s)
                need -= 1
            else:
                advance(retry_s)
        if need == 0 and t <= window_min * 60:
            done += 1
            times.append(t)
    return {"completion_rate": round(done / n, 3),
            "median_time_to_decision_s": round(st.median(times), 1) if times else None}


def section_uniqueness():
    sys.path.insert(0, str(paths.ROOT / "data" / "tooling"))
    import generate_patients as gp
    rng = random.Random(SEED)
    pop = [gp.sample_patient_attributes(rng, f"S{i}") for i in range(100000)]

    def keyf(a, fields):
        return tuple(a[f] if f != "age_band" else a["age"] // 10 for f in fields)

    record_fields = ["age_band", "sex", "histology", "stage", "tnm", "measurable_disease", "disease_status",
                     "pleural_effusion", "ps_scale", "ps_value", "fev1_pct", "biomarker", "brain_mets",
                     "prior_chemo", "prior_radio", "prior_tki", "prior_io", "prior_timing", "neuropathy",
                     "cardiovascular", "active_infection", "creatinine", "anc", "platelets", "hemoglobin",
                     "bilirubin", "autoimmune", "pregnant"]
    fmap = {"stage_group": "stage", "tnm_t": "tnm", "tnm_n": "tnm", "tnm_m": "tnm", "anc_k_ul": "anc",
            "platelets_k_ul": "platelets", "hemoglobin_g_dl": "hemoglobin", "creatinine_mg_dl": "creatinine",
            "bilirubin_mg_dl": "bilirubin", "brain_mets": "brain_mets", "egfr": "biomarker", "kras": "biomarker",
            "alk": "biomarker", "ros1": "biomarker", "ret": "biomarker", "braf": "biomarker", "met": "biomarker",
            "malignant_effusion": "pleural_effusion", "disease_status": "disease_status", "ecog": "ps_value",
            "kps": "ps_value", "histology": "histology", "age": "age_band", "sex": "sex",
            "measurable_disease": "measurable_disease", "fev1_pct": "fev1_pct", "neuropathy_grade": "neuropathy",
            "active_infection": "active_infection", "autoimmune_active": "autoimmune", "pregnant": "pregnant"}
    sets, per_patient = [], defaultdict(set)
    seen = set()
    with open(paths.LLM_LOG, encoding="utf-8") as f:
        for line in f:
            try:
                r = json.loads(line)
            except Exception:
                continue
            if r.get("channel") == "cloud_fact" and r.get("run_id") == "run:TEST_deploy":
                k = (r.get("cache_key"), r.get("local_ref"))
                if k in seen:
                    continue
                seen.add(k)
                fs = sorted({fmap[x] for x in (r.get("disclosed_fields") or []) if x in fmap})
                sets.append(tuple(fs))
                per_patient[str(r.get("local_ref", "")).split("__")[0]] |= set(fs)

    def uniq_share(fields, n):
        c = Counter(keyf(a, fields) for a in pop[:n])
        return sum(1 for a in pop[:n] if c[keyf(a, fields)] == 1) / n

    out = {"population": "generator attribute sampler (synthetic), seed 20261109",
           "record_level": {str(n): round(uniq_share(record_fields, n), 3) for n in (10000, 100000)}}
    cnt = Counter(sets)
    res = {}
    for n in (10000, 100000):
        tot = 0.0
        cache = {}
        for fs, m in cnt.items():
            if fs not in cache:
                cache[fs] = uniq_share(list(fs), n) if fs else 0.0
            tot += cache[fs] * m
        res[str(n)] = round(tot / sum(cnt.values()), 3)
    out["fact_level_mean_uniqueness_over_payloads"] = res
    # Linkable threat model: the cloud links all queries of one screening session (one patient).
    lk = {}
    for n in (10000, 100000):
        vals = [uniq_share(sorted(fs), n) if fs else 0.0 for fs in per_patient.values()]
        lk[str(n)] = round(float(np.mean(vals)), 3)
    out["fact_level_linked_per_patient_mean_uniqueness"] = lk
    out["patients_with_fact_queries"] = len(per_patient)
    out["linked_fields_per_patient_median"] = sorted(len(v) for v in per_patient.values())[len(per_patient) // 2]
    out["fact_payloads"] = sum(cnt.values())
    out["fact_payloads_with_structured_fields"] = sum(m for fs, m in cnt.items() if fs)
    out["fact_payloads_with_a_lab_value"] = sum(m for fs, m in cnt.items()
                                                if set(fs) & {"anc", "platelets", "hemoglobin", "creatinine",
                                                              "bilirubin"})
    return out


def per_patient_median_s(d):
    """Median over patients of the summed per-pair latencies (CPU seconds per patient, 6 trials)."""
    per = defaultdict(float)
    for i, v in d.items():
        if v.get("latency") is None:
            return None
        per[i.split("__")[0]] += v["latency"]
    pv = sorted(per.values())
    return round(pv[len(pv) // 2], 1) if pv else None


def section_same_model(conds, ids):
    """Same device model (Qwen3-4B), two uses: reading the note vs driving SPLIT-Match (deploy).
    Adds patient- and two-way-cluster CIs next to the trial-cluster CI used in the paper."""
    def pair(a, b):
        b = {i: {**v, "pred": 0 if v["pred"] is None else v["pred"]} for i, v in b.items()}
        o = {"acc_read": round(acc(a, ids), 3), "acc_compiled": round(acc(b, ids), 3),
             "acc_diff": round(acc(a, ids) - acc(b, ids), 3), "mcnemar": stats.mcnemar(a, b, ids),
             "recall_read": round(recall(a, ids), 3), "recall_compiled": round(recall(b, ids), 3),
             "recall_diff": round(recall(a, ids) - recall(b, ids), 3)}
        pos = [i for i in ids if a[i]["y"] == 1]
        o["missed_read"] = sum(a[i]["pred"] != 1 for i in pos)
        o["missed_compiled"] = sum(b[i]["pred"] != 1 for i in pos)
        for m in ("trial", "patient", "twoway"):
            o[f"acc_diff_ci_{m}"] = boot_diff("acc", a, b, ids, m)
            o[f"recall_diff_ci_{m}"] = boot_diff("recall", a, b, ids, m)
        return o

    out = pair(conds["edgeFourB"], conds["splitDeploy"])  # Qwen3-4B on the laptop (top level, as before)
    # second device model: hosted gpt-oss-20b as SPLIT-Match's edge tier (TEST_proxy) vs the same model reading
    # the note and raw criteria with the zero-shot prompt -- the pre-specified "-compiler" ablation
    # (AB_nocompiler_proxy20b; same prompt as the Qwen3-4B reading condition ZS_edge_qwen4b_test)
    out["gptoss20b_hosted"] = pair(conds["edgeTwentyB"], conds["splitProxy"])
    return out


def section_local20b_full(ids, conds, cloud_runs, hosted_runs):
    """gpt-oss-20b reading the full note ON THE LAPTOP, all 270 test pairs (round-2 review run)."""
    rows = jsonl_rows(RV / "LOC_gptoss20b_test.jsonl")
    ok = [r for r in rows if "prediction" in r]
    loc = from_rows(ok)
    out = {"pairs_ok": len(ok), "error_rows": sum("error" in r for r in rows), "complete": complete(loc, ids)}
    if not out["complete"]:
        return out
    ref = conds["cloudZS"]
    out["clinical"] = clinical_row(loc, ids)
    # trial-cluster CI of the accuracy itself (difference against an all-wrong reference = accuracy)
    zero = {i: {**loc[i], "pred": 1 - loc[i]["y"]} for i in ids}
    out["acc_ci_trial"] = boot_diff("acc", loc, zero, ids, "trial")
    out["acc_diff_vs_cloud"] = round(acc(loc, ids) - acc(ref, ids), 3)
    out["recall_diff_vs_cloud"] = round(recall(loc, ids) - recall(ref, ids), 3)
    for m in ("trial", "patient", "twoway"):
        out[f"acc_diff_ci_{m}"] = boot_diff("acc", loc, ref, ids, m)
        out[f"recall_diff_ci_{m}"] = boot_diff("recall", loc, ref, ids, m)
    out["mcnemar_vs_cloud"] = stats.mcnemar(loc, ref, ids)
    # against the mean of the cloud runs (noise floor), trial-cluster bootstrap
    mc = {i: float(np.mean([r[i]["pred"] == r[i]["y"] for r in cloud_runs.values()])) for i in ids}
    ml = {i: float(loc[i]["pred"] == loc[i]["y"]) for i in ids}
    rng = np.random.default_rng(SEED)
    byt = defaultdict(list)
    for i in ids:
        byt[ref[i]["trial"]].append(i)
    tr = sorted(byt)
    diffs = [np.mean([ml[i] - mc[i] for t in rng.choice(tr, len(tr)) for i in byt[t]]) for _ in range(B)]
    out["diff_vs_cloud_run_mean"] = round(float(np.mean([ml[i] - mc[i] for i in ids])), 4)
    out["diff_vs_cloud_run_mean_ci_trial"] = [round(float(x), 4) for x in np.percentile(diffs, [2.5, 97.5])]
    # local vs the hosted runs of the same model
    out["hosted_runs_acc"] = {k: round(acc(v, ids), 3) for k, v in hosted_runs.items()}
    out["hosted_mean_acc"] = round(st.mean(acc(v, ids) for v in hosted_runs.values()), 4)
    out["agreement_with_hosted"] = {k: round(float(np.mean([loc[i]["pred"] == v[i]["pred"] for i in ids])), 3)
                                    for k, v in hosted_runs.items()}
    h0 = hosted_runs["orig"]
    out["acc_diff_vs_hosted_orig"] = round(acc(loc, ids) - acc(h0, ids), 3)
    out["acc_diff_vs_hosted_orig_ci_trial"] = boot_diff("acc", loc, h0, ids, "trial")
    out["mcnemar_vs_hosted_orig"] = stats.mcnemar(loc, h0, ids)
    # missed / unnecessary per run: the run-to-run spread of the primary clinical lens
    pos = [i for i in ids if ref[i]["y"] == 1]

    def miss_unn(d):
        return {"missed": sum(d[i]["pred"] != 1 for i in pos),
                "unnecessary": sum(d[i]["pred"] == 1 for i in ids if d[i]["y"] == 0)}
    out["cloud_runs_miss_unn"] = {k: miss_unn(v) for k, v in cloud_runs.items()}
    out["hosted_runs_miss_unn"] = {k: miss_unn(v) for k, v in hosted_runs.items()}
    # laptop 20B vs laptop 4B (both read the note on the same device)
    f4 = conds["edgeFourB"]
    out["vs_4b_acc_diff"] = round(acc(loc, ids) - acc(f4, ids), 3)
    out["vs_4b_acc_diff_ci_trial"] = boot_diff("acc", loc, f4, ids, "trial")
    out["vs_4b_mcnemar"] = stats.mcnemar(loc, f4, ids)
    out["vs_4b_eligible_caught_only"] = {
        "20b": sum(loc[i]["pred"] == 1 and f4[i]["pred"] != 1 for i in pos),
        "4b": sum(f4[i]["pred"] == 1 and loc[i]["pred"] != 1 for i in pos)}
    # cost on the laptop (latencies of replayed pairs are those measured when they first ran)
    lat = sorted(r["latency_s"] for r in ok if r.get("latency_s"))
    gen = [r["gen_tok_per_s"] for r in ok if r.get("gen_tok_per_s")]
    pr = [r["prompt_tok_per_s"] for r in ok if r.get("prompt_tok_per_s")]
    peaks = [r.get("peak_ram_mb") or 0 for f in ("LOC_gptoss20b_test", "LOC_gptoss20b_sub40")
             for r in jsonl_rows(RV / f"{f}.jsonl")]
    out["latency_p50_s"] = lat[len(lat) // 2]
    out["latency_p95_s"] = lat[int(0.95 * (len(lat) - 1))]
    out["latency_mean_s"] = round(st.mean(lat), 1)
    out["per_patient_median_s"] = per_patient_median_s(loc)
    out["total_cpu_hours"] = round(sum(lat) / 3600, 2)
    out["gen_tok_per_s_median"] = round(st.median(gen), 2) if gen else None
    out["prompt_tok_per_s_median"] = round(st.median(pr), 2) if pr else None
    out["peak_ram_mb"] = max(peaks) if peaks else None
    out["replayed_from_earlier_local_runs"] = sum(bool(r.get("cached")) for r in ok)
    return out


def section_local20b(ids_all, hosted):
    out = {}
    for name in ("LOC_gptoss20b_pilot", "LOC_gptoss20b_sub40"):
        rows = jsonl_rows(RV / f"{name}.jsonl")
        if not rows:
            continue
        ok = [r for r in rows if "prediction" in r]
        err = [r for r in rows if "error" in r]
        lat = sorted(r["latency_s"] for r in ok if r.get("latency_s"))
        gen = [r["gen_tok_per_s"] for r in ok if r.get("gen_tok_per_s")]
        pr = [r["prompt_tok_per_s"] for r in ok if r.get("prompt_tok_per_s")]
        d = from_rows(ok)
        sub = [i for i in d if i in hosted]
        out[name] = {"pairs_ok": len(ok), "errors": len(err),
                     "error_examples": [e["error"] for e in err[:2]],
                     "acc": round(acc(d, sub), 3) if sub else None,
                     "hosted_acc_same_pairs": round(acc(hosted, sub), 3) if sub else None,
                     "agreement_with_hosted": round(float(np.mean([d[i]["pred"] == hosted[i]["pred"] for i in sub])), 3)
                     if sub else None,
                     "latency_p50_s": lat[len(lat) // 2] if lat else None,
                     "latency_p95_s": lat[int(0.95 * (len(lat) - 1))] if lat else None,
                     "gen_tok_per_s_median": round(st.median(gen), 2) if gen else None,
                     "prompt_tok_per_s_median": round(st.median(pr), 2) if pr else None,
                     "peak_ram_mb": max((r.get("peak_ram_mb") or 0) for r in rows) if rows else None}
    return out



# ── round-5 review (2026-11-10): missed-patient inference, fixed-model decomposition, laptop repeats ──
def _safe(d):
    return {i: {**v, "pred": 0 if v["pred"] is None else v["pred"]} for i, v in d.items()}


def section_missed(conds, ids):
    """The safety outcome as an inferential endpoint: recall / false-negative rate with trial-cluster CIs,
    and the paired recall difference from cloud zero-shot under three clustering schemes, with an exact
    McNemar test restricted to the 69 eligible pairs."""
    ref = conds["cloudZS"]
    pos = [i for i in ids if ref[i]["y"] == 1]
    out = {}
    for k in ("cloudZS", "cloudRecord_deployFS", "splitDeploy", "offline", "edgeFourB", "edgeTwentyB_local",
              "edgeTwentyB", "qwen3_1p7b_local", "qwen27b"):
        if k not in conds:
            continue
        d = _safe(conds[k])
        zero = {i: {**d[i], "pred": 0} for i in ids}            # recall 0 -> diff = recall
        rec = recall(d, ids)
        row = {"recall": round(rec, 3), "fnr": round(1 - rec, 3),
               "missed": sum(d[i]["pred"] != 1 for i in pos), "eligible": len(pos),
               "recall_ci_trial": boot_diff("recall", d, zero, ids, "trial")}
        row["fnr_ci_trial"] = [round(1 - row["recall_ci_trial"][1], 3), round(1 - row["recall_ci_trial"][0], 3)]
        if k != "cloudZS":
            row["recall_diff_vs_cloud"] = round(rec - recall(ref, ids), 3)
            for m in ("trial", "patient", "twoway"):
                row[f"recall_diff_ci_{m}"] = boot_diff("recall", d, ref, ids, m)
            row["mcnemar_eligible_only"] = stats.mcnemar(d, ref, pos)
        out[k] = row
    return out


def section_decomposition(conds, ids):
    """Fixed device model, three inputs: the note; the model's own SPLIT-Match fact sheet without rules
    (run_record_cloud --decider); the full rule pipeline. Steps: note->fact sheet, fact sheet->rules."""
    chains = {"gptoss20b_hosted": ("edgeTwentyB", "REC_edge20b_test_proxy", "splitProxy"),
              "qwen4b_laptop": ("edgeFourB", "REC_edge4b_test_deploy", "splitDeploy")}
    out = {}
    for name, (note_k, rec_name, rule_k) in chains.items():
        rec = baseline(rec_name)
        if not complete(rec, ids):
            out[name] = {"complete": False, "fact_sheet_run": rec_name}
            continue
        a, f, r = _safe(conds[note_k]), _safe(rec), _safe(conds[rule_k])
        pos = [i for i in ids if a[i]["y"] == 1]
        row = {"complete": True}
        for lab, d in (("note", a), ("fact_sheet", f), ("rules", r)):
            row[lab] = {"acc": round(acc(d, ids), 3), "recall": round(recall(d, ids), 3),
                        "missed": sum(d[i]["pred"] != 1 for i in pos),
                        "unnecessary": sum(d[i]["pred"] == 1 for i in ids if d[i]["y"] == 0)}
        for lab, x, y in (("note_minus_fact_sheet", a, f), ("fact_sheet_minus_rules", f, r)):
            st_ = {"acc_diff": round(acc(x, ids) - acc(y, ids), 3),
                   "recall_diff": round(recall(x, ids) - recall(y, ids), 3),
                   "mcnemar": stats.mcnemar(x, y, ids)}
            for m in ("trial", "twoway"):
                st_[f"acc_diff_ci_{m}"] = boot_diff("acc", x, y, ids, m)
                st_[f"recall_diff_ci_{m}"] = boot_diff("recall", x, y, ids, m)
            row[lab] = st_
        out[name] = row
    return out


def section_local_repeats(ids, conds):
    """Fresh (uncached) repeat runs on the laptop: decision stability, latency distribution, cold start, memory."""
    out = {}

    def lat_stats(rows):
        lat = sorted(r["latency_s"] for r in rows if r.get("latency_s"))
        load = [r.get("load_s") or 0 for r in rows]
        return {"latency_p50_s": lat[len(lat) // 2] if lat else None,
                "latency_p95_s": lat[int(0.95 * (len(lat) - 1))] if lat else None,
                "cold_load_s": load[0] if load else None,
                "warm_load_s_median": sorted(load[1:])[len(load[1:]) // 2] if len(load) > 1 else None,
                "peak_ram_mb": max((r.get("peak_ram_mb") or 0) for r in rows) if rows else None,
                "gen_tok_per_s_median": (sorted(r["gen_tok_per_s"] for r in rows if r.get("gen_tok_per_s"))
                                         or [None])[len([r for r in rows if r.get("gen_tok_per_s")]) // 2]}

    for name, orig_key, file in (("qwen4b_full_test", "edgeFourB", "LOC_qwen4b_test_rep1"),
                                 ("gptoss20b_sub40", "edgeTwentyB_local", "LOC_gptoss20b_sub40_rep1")):
        rows = [r for r in jsonl_rows(RV / f"{file}.jsonl") if "prediction" in r]
        if not rows or orig_key not in conds:
            out[name] = {"complete": False}
            continue
        rep = from_rows(rows, rep=1)
        common = [i for i in ids if i in rep]
        o = conds[orig_key]
        out[name] = {"complete": len(common) == (270 if name.startswith("qwen") else 40), "pairs": len(common),
                     "agreement_with_first_run": round(float(np.mean([rep[i]["pred"] == o[i]["pred"]
                                                                      for i in common])), 3),
                     "acc_first_run_same_pairs": round(acc(o, common), 3), "acc_repeat": round(acc(rep, common), 3),
                     "uncached_rows": sum(not r.get("cached") for r in rows), **lat_stats(rows)}
    return out


def main():
    test_ids = sorted(jsonl_rows(R / "runs" / "TEST_proxy" / "predictions.jsonl") and
                      [r["pair_id"] for r in jsonl_rows(R / "runs" / "TEST_proxy" / "predictions.jsonl")])
    cloudZS = load_baseline("experiment1_testing_data_zero_shot.jsonl")
    conds = {
        "cloudZS": cloudZS,
        "cloudZSrerun": baseline("ZS_cloud_test_rerun"),
        "cloudFS": load_baseline("experiment1_testing_data_few_shot.jsonl"),
        "cloudRAG": load_baseline("experiment1_testing_data_rag_only.jsonl"),
        "indiconAdv": load_advisory(),
        "cloudRecord_proxyFS": baseline("REC_cloud_test_proxy"),
        "cloudRecord_deployFS": baseline("REC_cloud_test_deploy"),
        "splitDeploy": run(["TEST_deploy"], "forced"),
        "splitProxy": run(["TEST_proxy"], "forced"),
        "offline": run(["AB_noL2"], "forced"),
        "edgeTwentyB": baseline("AB_nocompiler_proxy20b"),
        "edgeFourB": baseline("ZS_edge_qwen4b_test"),
        "qwen27b": review("CAP_qwen27b"),
        "qwen3_1p7b_local": review("CAP_qwen3_1p7b_local"),
    }
    loc20 = review("LOC_gptoss20b_test")
    if complete(loc20, test_ids):
        conds["edgeTwentyB_local"] = loc20
    # forced SPLIT runs carry no confidence; selective has abstentions
    res = {"note": "Exploratory analyses for the pre-submission review; not part of the pre-specified plan."}
    res["clinical"] = section_clinical(conds, cloudZS, test_ids)
    res["noise"] = section_noise(test_ids, cloudZS, conds["cloudZSrerun"], conds["edgeTwentyB"])
    res["capacity"] = section_capacity(test_ids, cloudZS, conds)
    res["long_notes"] = section_long(test_ids, {
        "cloud120b": ("LONG_cloud120b", review("NF_cloud120b", 0) if complete(review("NF_cloud120b", 0), test_ids)
                      else conds["cloudZSrerun"]),
        "edge20b": ("LONG_edge20b", conds["edgeTwentyB"]),
        "edge4b": ("LONG_edge4b_local", conds["edgeFourB"])})
    res["coverage"] = section_coverage(test_ids, run(["AB_noL2"], "selective"),
                                       {k: conds[k] for k in ("cloudZS", "edgeTwentyB", "edgeTwentyB_local",
                                                              "edgeFourB") if k in conds})
    res["same_model"] = section_same_model(conds, test_ids)
    cloud_runs = {"cached": cloudZS, "rerun1": conds["cloudZSrerun"]}
    hosted20 = {"orig": conds["edgeTwentyB"]}
    for k in range(3):
        if complete(review("NF_cloud120b", k), test_ids):
            cloud_runs[f"rep{k + 1}"] = review("NF_cloud120b", k)
        if complete(review("NF_edge20b", k), test_ids):
            hosted20[f"rep{k + 1}"] = review("NF_edge20b", k)
    res["local20b_full"] = section_local20b_full(test_ids, conds, cloud_runs, hosted20)
    bw = section_bandwidth()
    res["bandwidth"] = bw
    calls = {"full_note_cloud": 6, "facts_deploy": round(2.10 * 6, 1), "record_cloud": 6}
    # measured local CPU seconds per patient (same definitions as paper_numbers.py: SPLIT-Match = median
    # structuring + median batched L1; full-note readers = median over patients of summed pair latencies)
    four_pp = per_patient_median_s(conds["edgeFourB"]) or 217.0
    res["outage_sim"] = {}
    for avail in (1.0, 0.9, 0.7, 0.5):
        res["outage_sim"][str(avail)] = {
            "cloud_full_note": outage_sim(6, 0, avail=avail),
            "split_match_deploy": outage_sim(int(round(2.10 * 6)), 1119, avail=avail),
            "edge_4b_full_note": outage_sim(0, four_pp, avail=avail)}
        if "edgeTwentyB_local" in conds:
            res["outage_sim"][str(avail)]["edge_20b_local_full_note"] = outage_sim(
                0, per_patient_median_s(conds["edgeTwentyB_local"]), avail=avail)
    res["outage_sim"]["assumptions"] = (
        f"per patient 6 trials; cloud call 6 s when link up; link up periods mean 30 min; retry every 30 s; "
        f"decision window 30 min; SPLIT-Match deploy 1119 s local CPU per patient + 13 cloud calls "
        f"(2.10 per pair); edge 4B {four_pp} s local CPU per patient (measured median). Time to decision = "
        f"local CPU time + cloud call time, so SPLIT-Match's exceeds its 1119 s CPU time")
    try:
        res["uniqueness"] = section_uniqueness()
    except Exception as e:
        res["uniqueness"] = {"error": f"{type(e).__name__}: {e}"}
    res["local20b"] = section_local20b(test_ids, conds["edgeTwentyB"])
    res["missed"] = section_missed(conds, test_ids)
    res["decomposition"] = section_decomposition(conds, test_ids)
    res["local_repeats"] = section_local_repeats(test_ids, conds)
    # outage sensitivity: mean length of link-up periods (down periods scale with availability)
    res["outage_sensitivity"] = {
        str(up): {str(av): {"cloud_full_note": outage_sim(6, 0, up_min=up, avail=av)["completion_rate"],
                            "split_match_deploy": outage_sim(int(round(2.10 * 6)), 1119, up_min=up,
                                                             avail=av)["completion_rate"]}
                  for av in (0.5, 0.7, 0.9)}
        for up in (5.0, 30.0, 120.0)}
    (R / "REVIEW_ANALYSIS.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print(json.dumps({k: res[k] for k in ("noise", "capacity", "long_notes", "coverage", "local20b")},
                     indent=1, default=str)[:6000])


if __name__ == "__main__":
    main()
