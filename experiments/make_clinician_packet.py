"""Builds the clinician review packet (review point 7). No model calls.

    python experiments/make_clinician_packet.py

Writes docs/clinician_review/:
  PACKET.md        instructions + 20 notes for realism rating + every false exclusion of the edge models
  realism_form.csv one row per note (rate 1-5 on four items)
  severity_form.csv one row per false exclusion (severity and whether a clinician would also exclude)
"""
import csv
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from splitmatch import data, paths  # noqa: E402

OUT = paths.ROOT / "docs" / "clinician_review"
OUT.mkdir(parents=True, exist_ok=True)


def load_preds(name):
    f = paths.RESULTS / "baselines" / f"{name}.jsonl"
    return {json.loads(l)["pair_id"]: json.loads(l) for l in open(f, encoding="utf-8")}


def main():
    pairs = data.load_pairs("test")
    notes = dict(pairs.drop_duplicates("patient_id")[["patient_id", "note"]].values)
    rng = random.Random(20261109)
    sample = sorted(rng.sample(sorted(notes), 20))
    e20 = load_preds("AB_nocompiler_proxy20b")
    e4 = load_preds("ZS_edge_qwen4b_test")
    fe = []
    for r in pairs.itertuples():
        who = [m for m, p in (("edge-20B", e20), ("edge-4B", e4))
               if int(r.label) == 1 and p[r.pair_id]["prediction"] != "Eligible"]
        if who:
            fe.append((r, who))
    lines = ["# Clinician review packet (TELMED 2027 submission)", "",
             "Thank you for helping. Two short tasks; about 60-90 minutes in total. All patients are synthetic.", "",
             "## Task A - realism of 20 synthetic patient notes",
             "For each note, rate 1 (not at all) to 5 (fully) in `realism_form.csv`:",
             "1. *Clinically plausible* (the facts fit together for an NSCLC patient).",
             "2. *Reads like a real referral or clinic note.*",
             "3. *Contains what a pre-screening decision needs.*",
             "4. *Overall realism.* Add a free-text comment if anything is implausible.", ""]
    for pid in sample:
        lines += [f"### Note {pid}", "", notes[pid], ""]
    lines += ["## Task B - severity of missed eligible patients (false exclusions)",
              "Each case below is a patient whom both expert annotators labelled ELIGIBLE for the trial, but an "
              "on-device model labelled NOT ELIGIBLE. In `severity_form.csv`, record: (a) would a clinician also "
              "have hesitated to refer (yes/no/unsure); (b) severity of missing this patient: 1 = trivial "
              "(ambiguous criterion), 2 = moderate, 3 = serious (clearly eligible patient lost).", ""]
    for r, who in fe:
        lines += [f"### {r.pair_id} (missed by: {', '.join(who)})", "", f"**Patient note.** {r.note}", "",
                  f"**Inclusion criteria.** {r.inclusion[:3000]}", "", f"**Exclusion criteria.** {r.exclusion[:3000]}", ""]
    (OUT / "PACKET.md").write_text("\n".join(lines), encoding="utf-8")
    with open(OUT / "realism_form.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["note_id", "plausible_1to5", "reads_like_real_1to5", "has_needed_info_1to5", "overall_1to5",
                    "comment", "rater_initials", "rater_specialty_and_years"])
        for pid in sample:
            w.writerow([pid, "", "", "", "", "", "", ""])
    with open(OUT / "severity_form.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["pair_id", "missed_by", "clinician_would_hesitate_yes_no_unsure", "severity_1to3", "comment",
                    "rater_initials"])
        for r, who in fe:
            w.writerow([r.pair_id, "+".join(who), "", "", "", ""])
    print("notes", len(sample), "false exclusions", len(fe),
          "edge20B", sum("edge-20B" in w for _, w in fe), "edge4B", sum("edge-4B" in w for _, w in fe))


if __name__ == "__main__":
    main()
