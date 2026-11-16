"""Proxy <-> local fidelity on identical inputs (DEVELOPMENT_PLAN §0, rule 2).

    python experiments/fidelity.py --local TEST_deploy --proxy TEST_proxy

Reports (i) field-level agreement of the two edge models' fact sheets, (ii) agreement of
the final decisions (forced and selective), so any result produced with the cloud
stand-in for the edge tier can be qualified by how closely it tracks the real edge model.
"""
import argparse
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from splitmatch import paths  # noqa: E402
from splitmatch.schema import FactSheet  # noqa: E402
from splitmatch.structurer import _equal  # noqa: E402


def load_fs(run):
    d = paths.RESULTS / "runs" / run / "factsheets"
    return {p.stem: FactSheet.model_validate_json(p.read_text(encoding="utf-8"))
            for p in d.glob("P*.json") if not p.name.endswith(".l1.json")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--local", required=True)
    ap.add_argument("--proxy", required=True)
    a = ap.parse_args()
    L, P = load_fs(a.local), load_fs(a.proxy)
    both = sorted(set(L) & set(P))
    agree = total = 0
    ver_agree = ver_total = 0
    for pid in both:
        names = set(L[pid].fields) | set(P[pid].fields)
        for n in names:
            fl, fp = L[pid].get(n), P[pid].get(n)
            total += 1
            same = fl.status == fp.status and (fl.status.value != "value" or _equal(n, fl.value, fp.value))
            agree += same
            if fl.verified or fp.verified:
                ver_total += 1
                ver_agree += same
    dl = pd.read_json(paths.RESULTS / "runs" / a.local / "predictions.jsonl", lines=True).set_index("pair_id")
    dp = pd.read_json(paths.RESULTS / "runs" / a.proxy / "predictions.jsonl", lines=True).set_index("pair_id")
    ids = dl.index.intersection(dp.index)
    res = {"patients": len(both), "field_agreement": agree / max(total, 1),
           "field_agreement_on_verified": ver_agree / max(ver_total, 1),
           "pairs": len(ids),
           "forced_decision_agreement": float((dl.loc[ids, "forced"] == dp.loc[ids, "forced"]).mean()),
           "selective_decision_agreement": float((dl.loc[ids, "selective"] == dp.loc[ids, "selective"]).mean())}
    out = paths.RESULTS / f"FIDELITY_{a.local}_vs_{a.proxy}.json"
    out.write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
