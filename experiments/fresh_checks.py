"""Label-free checks on never-inspected data (TELMED2027_PLAN §5.2).

    python experiments/fresh_checks.py extraction --edge proxy|local
    python experiments/fresh_checks.py compiler

extraction: structure the 25 expansion patients and score every fact against the
            generator's TRUE structured record (no eligibility labels involved).
            Reports field accuracy, and precision of VERIFIED vs UNVERIFIED facts.
compiler:   agreement / downgrade statistics for the 11 fresh expansion trials
            (+ writes an audit sheet for the human compiler audit).
"""
import argparse
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from splitmatch import data, paths  # noqa: E402
from splitmatch.llm import Channel  # noqa: E402
from splitmatch.structurer import structure  # noqa: E402

INF = math.inf
TIMING = {"within 1 month": [0, 1], "1-3 months ago": [1, 3], "3-6 months ago": [3, 6],
          "over 6 months ago": [6, INF]}
HIST = {"adenocarcinoma": "adenocarcinoma", "squamous cell carcinoma": "squamous",
        "large cell carcinoma": "large_cell", "NSCLC not otherwise specified": "nos"}
STATUS = {"newly diagnosed, treatment-naive": "newly_diagnosed",
          "progressed after prior therapy": "progressed_after_prior",
          "recurrent disease": "recurrent", "stable on current therapy": "stable_on_therapy"}


def truth(rec: dict) -> dict:
    """Facts the generator's narrative STATES (only those are scored)."""
    t = {"age": [rec["age"], rec["age"]], "sex": rec["sex"], "histology": HIST[rec["histology"]],
         "stage_group": rec["stage"], "disease_status": STATUS[rec["disease_status"]]}
    tn = rec["tnm"]
    import re
    m = re.match(r"(T\d[a-c]?)(N\d)(M\d[a-c]?)", tn)
    if m:
        t["tnm_t"], t["tnm_n"], t["tnm_m"] = m.group(1).upper(), m.group(2).upper(), m.group(3).upper()
    if rec["measurable_disease"]:
        t["measurable_disease"] = True
    if rec["pleural_effusion"]:
        t["malignant_effusion"] = True
    t["ecog" if rec["ps_scale"] == "ECOG" else "kps"] = [rec["ps_value"], rec["ps_value"]]
    if rec["fev1_stated"]:
        t["fev1_pct"] = [rec["fev1_pct"], rec["fev1_pct"]]
    b = rec["biomarker"]
    genes = ["egfr", "alk", "ros1", "kras", "ret"]
    if b == "no actionable mutation":
        for g in genes:
            t[g] = "negative"
    elif b == "not tested":
        for g in genes:
            t[g] = "not_tested"
    else:
        g = b.split()[0].lower()
        t[g] = "positive"
    if rec["brain_mets"] != "none":
        t["brain_mets"] = {"treated/stable": "treated_stable",
                           "untreated symptomatic": "untreated_or_symptomatic"}[rec["brain_mets"]]
    if rec["neuropathy"] != "none":
        g = float(rec["neuropathy"].split()[-1])
        t["neuropathy_grade"] = [g, g]
    cv = rec["cardiovascular"]
    if cv == "MI within 6 months":
        t["mi_history"], t["mi_months_ago"] = True, [0, 6]
    elif cv == "MI over 6 months ago":
        t["mi_history"], t["mi_months_ago"] = True, [6, INF]
    elif cv == "controlled arrhythmia":
        t["arrhythmia"] = "controlled"
    elif cv == "unstable angina recent":
        t["unstable_angina"] = True
    if rec["active_infection"]:
        t["active_infection"] = True
    if rec["autoimmune"]:
        t["autoimmune_active"] = True
    if rec["labs_stated"]:
        for k, f in (("creatinine", "creatinine_mg_dl"), ("anc", "anc_k_ul"), ("platelets", "platelets_k_ul"),
                     ("hemoglobin", "hemoglobin_g_dl"), ("bilirubin", "bilirubin_mg_dl")):
            t[f] = [rec[k], rec[k]]
    if rec["pregnant"]:
        t["pregnant"] = True
    ther = {c for c, k in (("chemo", "prior_chemo"), ("radio", "prior_radio"), ("tki", "prior_tki"),
                           ("io", "prior_io")) if rec[k]}
    t["_therapy"] = {"classes": ther, "timing": TIMING.get(rec["prior_timing"])}
    return t


def eq(a, b) -> bool:
    if isinstance(b, list):
        if not isinstance(a, list):
            return False
        return all((x == y) or (math.isfinite(x) and math.isfinite(y) and abs(x - y) <= 0.051 * max(abs(x), abs(y), 1))
                   for x, y in zip(a, b))
    return str(a).lower() == str(b).lower()


def extraction(edge_name: str):
    edge = Channel.EDGE_LOCAL if edge_name == "local" else Channel.EDGE_PROXY
    recs = data.expansion_patients()
    out_dir = paths.RESULTS / "fresh" / f"extraction_{edge_name}"
    out_dir.mkdir(parents=True, exist_ok=True)
    per_field = defaultdict(Counter)
    ver = Counter()
    rows = []
    for r in recs:
        f = out_dir / f"{r['patient_id']}.json"
        from splitmatch.schema import FactSheet
        if f.exists():
            fs = FactSheet.model_validate_json(f.read_text(encoding="utf-8"))
        else:
            fs = structure(r["patient_id"], r["narrative"], edge, run_id=f"fresh:extraction:{edge_name}")
            f.write_text(fs.model_dump_json(indent=1), encoding="utf-8")
        t = truth(r)
        for name, tv in t.items():
            if name.startswith("_"):
                continue
            fact = fs.get(name)
            got = fact.value if fact.status.value == "value" else None
            ok = got is not None and eq(got, tv)
            per_field[name]["stated"] += 1
            per_field[name]["correct"] += ok
            per_field[name]["extracted"] += got is not None
            if got is not None:
                ver[("verified" if fact.verified else "unverified", ok)] += 1
        # facts asserted but NOT stated (hallucinated), for scored fields only
        for name, fact in fs.fields.items():
            if name not in t and fact.status.value == "value" and name in (
                    "malignant_effusion", "active_infection", "pregnant", "unstable_angina", "mi_history"):
                if fact.value is True:
                    per_field[name]["hallucinated_true"] += 1
        th = t["_therapy"]
        got_cls = {e.cls for e in fs.events}
        rows.append({"patient": r["patient_id"], "therapy_true": sorted(th["classes"]),
                     "therapy_got": sorted(got_cls), "therapy_exact": got_cls == th["classes"],
                     "therapy_status": fs.therapy_status.value})
    tot = Counter()
    for c in per_field.values():
        tot.update(c)
    vt, vf = ver[("verified", True)], ver[("verified", False)]
    ut, uf = ver[("unverified", True)], ver[("unverified", False)]
    res = {"edge": edge_name, "patients": len(recs),
           "field_recall_correct": tot["correct"] / tot["stated"],
           "precision_extracted": tot["correct"] / max(tot["extracted"], 1),
           "verified_facts": vt + vf, "verified_precision": vt / max(vt + vf, 1),
           "unverified_facts": ut + uf, "unverified_precision": ut / max(ut + uf, 1),
           "share_verified": (vt + vf) / max(vt + vf + ut + uf, 1),
           "therapy_class_exact": sum(r["therapy_exact"] for r in rows) / len(rows),
           "per_field": {k: dict(v) for k, v in sorted(per_field.items())}}
    (paths.RESULTS / "fresh" / f"extraction_{edge_name}.json").write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps({k: (round(v, 3) if isinstance(v, float) else v) for k, v in res.items() if k != "per_field"}, indent=1))


def compiler():
    s = json.loads((paths.RESULTS / "programs" / "expansion_summary.json").read_text())
    d = json.loads((paths.RESULTS / "programs" / "development_summary.json").read_text())
    print("expansion (fresh):", s["total"])
    print("development     :", d["total"])
    # audit sheet
    from splitmatch.pipeline import load_programs
    from splitmatch.render import render
    lines = ["| trial | atom | type | pol | downgraded | compiled | source line | audit (OK/WRONG) |",
             "|---|---|---|---|---|---|---|---|"]
    for tid, p in sorted(load_programs("expansion").items()):
        for a in p.atoms:
            if a.type.value in ("JUDGE", "UNSCREENABLE"):
                continue
            lines.append(f"| {tid} | {a.id} | {a.type.value} | {a.polarity[:3]} | {a.downgraded} | "
                         f"{render(a)[:80]} | {a.source_line[:100].replace('|', '/')} | |")
    (paths.RESULTS / "fresh" / "compiler_audit_expansion.md").parent.mkdir(parents=True, exist_ok=True)
    (paths.RESULTS / "fresh" / "compiler_audit_expansion.md").write_text("\n".join(lines), encoding="utf-8")
    print("audit sheet rows:", len(lines) - 2)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=["extraction", "compiler"])
    ap.add_argument("--edge", choices=["proxy", "local"], default="proxy")
    a = ap.parse_args()
    extraction(a.edge) if a.what == "extraction" else compiler()
