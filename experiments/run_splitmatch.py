"""Run SPLIT-Match on a split.

    python experiments/run_splitmatch.py --split dev_train --edge proxy --name dev_train_proxy
    python experiments/run_splitmatch.py --split test --edge local --name TEST_deploy   (deploy; after freeze)

Ablations: --hard-veto --no-l1 --no-l2 --boolean-only --programs-variant _single
"""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from splitmatch import data, paths  # noqa: E402
from splitmatch.llm import Channel  # noqa: E402
from splitmatch.pipeline import boolean_only, load_programs, metrics, run  # noqa: E402
from splitmatch.policy import Config  # noqa: E402

PROGRAM_SET = {"dev_train": "development", "dev_validation": "development", "dev": "development",
               "test": "test"}

ap = argparse.ArgumentParser()
ap.add_argument("--split", required=True)
ap.add_argument("--edge", choices=["proxy", "local"], default="proxy")
ap.add_argument("--name", required=True)
ap.add_argument("--hard-veto", action="store_true")
ap.add_argument("--no-l1", action="store_true")
ap.add_argument("--no-l2", action="store_true")
ap.add_argument("--boolean-only", action="store_true")
ap.add_argument("--programs-variant", default="")
ap.add_argument("--factsheets-from", default="", help="reuse fact sheets of another run")
a = ap.parse_args()

if a.split == "test" and a.edge == "local":
    os.environ["SPLITMATCH_MODE"] = "deploy"
edge = Channel.EDGE_LOCAL if a.edge == "local" else Channel.EDGE_PROXY
pairs = data.load_pairs(a.split)
progs = load_programs(PROGRAM_SET[a.split], a.programs_variant)
missing = set(pairs.trial_id) - set(progs)
assert not missing, f"missing compiled programs: {missing}"
cfg = Config(hard_veto=a.hard_veto, use_l1=not a.no_l1, use_l2=not a.no_l2)

fss = None
if a.factsheets_from:
    from splitmatch.schema import FactSheet
    d = paths.RESULTS / "runs" / a.factsheets_from / "factsheets"
    fss = {p.stem: FactSheet.model_validate_json(p.read_text(encoding="utf-8"))
           for p in d.glob("P*.json") if not p.stem.endswith(".l1")}

df = run(pairs, progs, edge, a.name, cfg=cfg, factsheets=fss,
         transform=boolean_only if a.boolean_only else None)
m = metrics(df)
m["config"] = vars(a)
(paths.RESULTS / "runs" / a.name / "metrics.json").write_text(json.dumps(m, indent=1), encoding="utf-8")
print(json.dumps(m, indent=1))
