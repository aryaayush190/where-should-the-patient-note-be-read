"""Zero-shot baseline (exact INDICON prompt) on a split, optionally on stress variants.

    python experiments/run_zero_shot.py --split test --where cloud --name ZS_cloud_test_rerun
    python experiments/run_zero_shot.py --split test --where local --name ZS_edge_test     (CPU, slow)
    python experiments/run_zero_shot.py --split test --where cloud --variant cue0 --name ZS_cloud_cue0
"""
import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from splitmatch import data, paths, variants  # noqa: E402
from splitmatch.baseline import zero_shot  # noqa: E402
from splitmatch.llm import Channel  # noqa: E402


def variant_notes(pairs, variant: str) -> dict:
    notes = dict(pairs.drop_duplicates("patient_id")[["patient_id", "note"]].values)
    if not variant:
        return notes
    if variant.startswith("cue"):
        return {p: variants.counterfactual(n, int(variant[3:])) for p, n in notes.items()}
    if variant == "noisy":
        return {p: variants.noisy(n) for p, n in notes.items()}
    raise ValueError(variant)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="test")
    ap.add_argument("--where", choices=["cloud", "local"], default="cloud")
    ap.add_argument("--variant", default="")
    ap.add_argument("--name", required=True)
    ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args()
    pairs = data.load_pairs(a.split)
    notes = variant_notes(pairs, a.variant)
    ch = Channel.BASELINE_CLOUD if a.where == "cloud" else Channel.EDGE_LOCAL
    out = paths.RESULTS / "baselines" / f"{a.name}.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)

    def one(row):
        r = zero_shot(notes[row.patient_id], row.inclusion, row.exclusion, ch,
                      local_ref=row.pair_id, run_id=f"zs:{a.name}")
        return {"pair_id": row.pair_id, "trial_id": row.trial_id, "label": int(row.label), **r}

    rows = list(pairs.itertuples())
    workers = 1 if a.where == "local" else a.workers
    with ThreadPoolExecutor(workers) as ex:
        res = list(ex.map(one, rows))
    with open(out, "w", encoding="utf-8") as f:
        for r in res:
            f.write(json.dumps(r) + "\n")
    acc = sum((r["prediction"] == "Eligible") == (r["label"] == 1) for r in res) / len(res)
    print(a.name, "n", len(res), "acc", round(acc, 4))


if __name__ == "__main__":
    main()
