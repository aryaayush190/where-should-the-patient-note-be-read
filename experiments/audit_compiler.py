"""Compiler-fidelity audit on the FRESH expansion trials (never used in development).

    python experiments/audit_compiler.py [--model openai/gpt-oss-20b]

An independent third model (not one of the two compilers) checks every typed atom
against its verbatim criterion line. Only public trial text is sent (CLOUD_PUBLIC).
Atoms flagged WRONG are then adjudicated by the authors (results/fresh/
compiler_audit_adjudication.md); the reported precision uses the adjudicated labels.
Agreed atoms (downgraded == False) are the ones that carry deterministic authority.
"""
import argparse
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from splitmatch import llm, paths  # noqa: E402
from splitmatch.llm import Channel  # noqa: E402
from splitmatch.pipeline import load_programs  # noqa: E402
from splitmatch.render import render  # noqa: E402

SYSTEM = """You audit a compiler that turns clinical-trial eligibility criteria into typed checks.
You get ONE criterion line (verbatim, with its section INCLUSION or EXCLUSION) and ONE compiled check.
Semantics of the check's polarity:
  inclusion check: the patient must satisfy the check to be eligible.
  exclusion check: if the check is TRUE for the patient, the patient is excluded.
The line may contain several requirements; the check only needs to capture ONE of them correctly.
Judge whether the compiled check is FAITHFUL to what the line says: right field/concept, right
direction of comparison, right threshold and units (days/weeks converted to months is fine:
1 month = 30.4 days), right therapy class or agent, right time window, right polarity.
Mark WRONG only for a real semantic error that would change an eligibility decision
(e.g. inverted direction, wrong threshold, wrong polarity, wrong drug class, a requirement the
line does not state, or an exclusion compiled from a line that only grants permission).
Respond with JSON only: {"verdict": "OK" | "WRONG", "reason": "<one sentence>"}"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="openai/gpt-oss-20b")
    a = ap.parse_args()
    items = []
    for tid, p in sorted(load_programs("expansion").items()):
        for at in p.atoms:
            if at.type.value in ("JUDGE", "UNSCREENABLE"):
                continue
            items.append((tid, at))

    def one(it):
        tid, at = it
        user = (f"SECTION: {(at.section or at.polarity).upper()}\nCRITERION LINE: {at.source_line}\n\n"
                f"COMPILED CHECK ({at.polarity}): {render(at)}\n"
                f"CHECK JSON: {at.model_dump_json(exclude={'source_line', 'lines', 'question', 'answerable_by', 'id'})}")
        rep = llm.call(Channel.CLOUD_PUBLIC, [{"role": "system", "content": SYSTEM},
                                              {"role": "user", "content": user}],
                       model=a.model, max_tokens=2000, extra={"reasoning_effort": "medium"}, run_id="audit:compiler", tag="compiler_audit")
        m = re.search(r"\{.*\}", rep.text, re.S)
        try:
            j = json.loads(m.group(0)) if m else {}
        except Exception:
            j = {}
        v = str(j.get("verdict", "UNPARSED")).upper()
        return {"trial": tid, "atom": at.id, "type": at.type.value, "polarity": at.polarity,
                "downgraded": at.downgraded, "compiled": render(at), "line": at.source_line,
                "verdict": v, "reason": j.get("reason", rep.text[:200])}

    with ThreadPoolExecutor(6) as ex:
        rows = list(ex.map(one, items))
    out = paths.RESULTS / "fresh" / "compiler_audit_auto.jsonl"
    with open(out, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    for grp, sel in (("all_typed", rows), ("agreed", [r for r in rows if not r["downgraded"]]),
                     ("downgraded", [r for r in rows if r["downgraded"]])):
        ok = sum(r["verdict"] == "OK" for r in sel)
        print(grp, "n", len(sel), "OK", ok, "WRONG", sum(r["verdict"] == "WRONG" for r in sel),
              "rate_ok", round(ok / max(len(sel), 1), 3))


if __name__ == "__main__":
    main()
