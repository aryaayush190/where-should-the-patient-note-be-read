"""[post-freeze, exploratory replication] Re-measure the privacy frontier on the
development split (130 pairs; trials and patients disjoint from test).

    python experiments/run_replication_dev.py

Why: the test set has only 18 trial clusters. The headline frontier ordering
(cloud full-note > edge full-note >> compiled split pipeline) should also hold on a
second, independent sample. For the zero-shot conditions dev is an unbiased sample
(no zero-shot condition was tuned on it). SPLIT-Match was *designed* on dev, so its dev
numbers are optimistic: a gap that persists on dev is therefore conservative.

Runs the edge-class full-note condition (gpt-oss-20b, EDGE_PROXY, INDICON prompt) on
dev and writes results/baselines/AB_nocompiler_proxy20b_dev.jsonl. Reuses the frozen
`edge_zero_shot` from run_ablations.py unchanged. Cloud zero-shot on dev is already
cached (results/baselines/ZS_cloud_dev.jsonl); the local Qwen3-4B condition is run with
run_zero_shot.py --split dev --where local --name ZS_edge_qwen4b_dev.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from splitmatch import data  # noqa: E402
from run_ablations import edge_zero_shot  # noqa: E402

if __name__ == "__main__":
    edge_zero_shot(data.load_pairs("dev"), "AB_nocompiler_proxy20b_dev")
