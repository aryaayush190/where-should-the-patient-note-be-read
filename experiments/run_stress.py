"""Stress studies on the frozen system (PREREGISTRATION §5).

    python experiments/run_stress.py redaction       --edge proxy|local
    python experiments/run_stress.py counterfactual  --edge proxy|local
    python experiments/run_stress.py noisy           --edge proxy|local

Each writes results/stress/<study>_<edge>.json (+ per-variant predictions).
SPLIT-Match uses the frozen test programs. The cloud zero-shot baseline uses the
exact INDICON prompt on the same variant notes.
"""
import argparse
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from splitmatch import data, paths, variants  # noqa: E402
from splitmatch.baseline import zero_shot  # noqa: E402
from splitmatch.llm import Channel  # noqa: E402
from splitmatch.pipeline import load_programs, run  # noqa: E402

# category -> independent reference (DATASET_CREATION v2 field checklist)
CHECKLIST = {"PS": ["ecog_kps"], "PRIOR_THERAPY": ["prior_chemo", "prior_radio"],
             "BRAIN_METS": ["cns_brain_mets"], "CARDIAC": ["cardiovascular_excl"],
             "LABS": ["renal_hepatic_labs"], "FEV1": ["fev1"], "BIOMARKER": ["egfr_alk_biomarker"]}


def trial_mentions(trial: dict, cat: str) -> bool:
    if cat == "EFFUSION":   # no checklist field; deviation logged in PREREGISTRATION §9
        return bool(re.search(r"effusion", (trial["inclusion_criteria"] + trial["exclusion_criteria"]).lower()))
    return any(trial["field_checklist"].get(k, False) for k in CHECKLIST[cat])


def variant_pairs(pairs: pd.DataFrame, vnotes: dict[str, tuple[str, str]]) -> pd.DataFrame:
    """vnotes: {variant_id: (patient_id, note)} -> pairs with patient_id := variant_id."""
    rows = []
    for vid, (pid, note) in vnotes.items():
        g = pairs[pairs.patient_id == pid].copy()
        g["orig_patient"] = pid
        g["patient_id"] = vid
        g["note"] = note
        g["pair_id"] = vid + "__" + g["trial_id"]
        rows.append(g)
    return pd.concat(rows, ignore_index=True)


def zs_many(vp: pd.DataFrame, name: str, workers=6) -> dict:
    def one(r):
        z = zero_shot(r.note, r.inclusion, r.exclusion, Channel.BASELINE_CLOUD,
                      local_ref=r.pair_id, run_id=f"zs:{name}")
        return r.pair_id, int(z["prediction"] == "Eligible")
    with ThreadPoolExecutor(workers) as ex:
        return dict(ex.map(one, list(vp.itertuples())))


def lab(pred: str):
    return 1 if pred == "ELIGIBLE" else 0 if pred == "NOT_ELIGIBLE" else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("study", choices=["redaction", "counterfactual", "noisy"])
    ap.add_argument("--edge", choices=["proxy", "local"], default="proxy")
    ap.add_argument("--base-run", default="", help="SPLIT run on the original test notes")
    a = ap.parse_args()
    edge = Channel.EDGE_LOCAL if a.edge == "local" else Channel.EDGE_PROXY
    pairs = data.load_pairs("test")
    progs = load_programs("test")
    trials = data.trials("test")
    notes = dict(pairs.drop_duplicates("patient_id")[["patient_id", "note"]].values)
    out_dir = paths.RESULTS / "stress"
    out_dir.mkdir(parents=True, exist_ok=True)
    tag = f"{a.study}_{a.edge}"

    if a.study == "redaction":
        vnotes, removed = {}, {}
        for pid, n in notes.items():
            for cat, (red, rem) in variants.redaction_variants(n).items():
                vid = f"{pid}~{cat}"
                vnotes[vid] = (pid, red)
                removed[vid] = rem
        vp = variant_pairs(pairs, vnotes)
        vp["category"] = vp.patient_id.str.split("~").str[1]
        vp["affected"] = [trial_mentions(trials[t], c) for t, c in zip(vp.trial_id, vp.category)]
        res = run(vp, progs, edge, f"STRESS_{tag}_redacted",
                  notes={v: n for v, (_, n) in vnotes.items()})
        # closed loop: the simulated health worker answers ASKs that target the removed category
        answered = {}
        for _, r in res.iterrows():
            cat = r.patient_id.split("~")[1]
            if r.selective == "NEED_INFO" and any(q["category"] == cat for q in r.asks):
                answered[r.patient_id] = True
        aug = {v: (vnotes[v][0], vnotes[v][1] + " " + " ".join(removed[v])) for v in answered}
        res2 = None
        if aug:
            vp2 = vp[vp.patient_id.isin(aug)].copy()
            vp2["patient_id"] = vp2.patient_id + "~ans"
            vp2["pair_id"] = vp2.patient_id + "__" + vp2.trial_id
            res2 = run(vp2, progs, edge, f"STRESS_{tag}_answered",
                       notes={v + "~ans": n for v, (_, n) in aug.items()})
        zs = zs_many(vp, f"{tag}_zs")
        rows = []
        after = {} if res2 is None else dict(zip(res2.pair_id.str.replace("~ans", ""), res2.forced))
        for (_, v), (_, r) in zip(vp.iterrows(), res.set_index("pair_id").loc[vp.pair_id].reset_index().iterrows()):
            cat = v.category
            rows.append({"pair_id": v.pair_id, "orig_pair": v.orig_patient + "__" + v.trial_id,
                         "trial_id": v.trial_id, "patient": v.orig_patient, "category": cat,
                         "affected": bool(v.affected), "label": int(v.label),
                         "split_selective": r.selective, "split_forced": r.forced,
                         "asked_removed": any(q["category"] == cat for q in r.asks),
                         "split_forced_after_answer": after.get(v.pair_id, r.forced),
                         "zs": zs[v.pair_id]})
        pd.DataFrame(rows).to_json(out_dir / f"{tag}.jsonl", orient="records", lines=True)
        print(tag, "variants", len(vnotes), "variant pairs", len(rows), "answered", len(aug))

    else:
        if a.study == "counterfactual":
            vnotes = {f"{p}~cue{i}": (p, variants.counterfactual(n, i)) for p, n in notes.items()
                      for i in range(len(variants.CUES))}
        else:
            vnotes = {f"{p}~noisy": (p, variants.noisy(n)) for p, n in notes.items()}
        vp = variant_pairs(pairs, vnotes)
        res = run(vp, progs, edge, f"STRESS_{tag}", notes={v: n for v, (_, n) in vnotes.items()})
        zs = zs_many(vp, f"{tag}_zs")
        rows = []
        r_by = res.set_index("pair_id")
        for _, v in vp.iterrows():
            r = r_by.loc[v.pair_id]
            rows.append({"pair_id": v.pair_id, "orig_pair": v.orig_patient + "__" + v.trial_id,
                         "trial_id": v.trial_id, "patient": v.orig_patient,
                         "variant": v.patient_id.split("~")[1], "label": int(v.label),
                         "split_selective": r.selective, "split_forced": r.forced,
                         "zs": zs[v.pair_id]})
        pd.DataFrame(rows).to_json(out_dir / f"{tag}.jsonl", orient="records", lines=True)
        print(tag, "variant pairs", len(rows))


if __name__ == "__main__":
    main()
