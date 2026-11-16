"""[post-freeze] Run the frozen analyze.py with a corruption-tolerant call-log loader,
plus an audit-completeness check.

    python experiments/analyze_run.py --run TEST_deploy

Why: runtime/llm_calls.jsonl is appended to by several processes at once (Groq queue +
local queue). On Windows, two appends can race and one record's head can be
overwritten, leaving an unparseable line. The frozen privacy.load_log would crash
on it. This wrapper skips such lines, counts them, and checks completeness:
cloud_fact log records for the run vs the L2 calls the run itself counted
(sum of n_l2). The runtime guard is unaffected by logging (it runs before I/O).
Frozen files are not modified.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd  # noqa: E402

from splitmatch import paths, privacy  # noqa: E402

SKIPPED = []


def tolerant_load_log(run_id=None, path=None):
    p = path or paths.LLM_LOG
    recs = []
    for i, l in enumerate(open(p, encoding="utf-8")):
        try:
            recs.append(json.loads(l))
        except Exception:
            SKIPPED.append(i)
    return [r for r in recs if run_id is None or r.get("run_id") == run_id]


privacy.load_log = tolerant_load_log
import analyze  # noqa: E402

analyze.load_log = tolerant_load_log

if __name__ == "__main__":
    analyze.main()
    run = sys.argv[sys.argv.index("--run") + 1]
    if "--stress-edge" not in sys.argv:
        df = pd.read_json(paths.RESULTS / "runs" / run / "predictions.jsonl", lines=True)
        recs = tolerant_load_log(f"run:{run}")
        n_log = sum(r.get("channel") == "cloud_fact" for r in recs)
        comp = {"unparseable_log_lines_total": len(SKIPPED), "cloud_fact_log_records": n_log,
                "l2_calls_counted_by_run": int(df.n_l2.sum()),
                "note": "a difference means log records were lost to concurrent appends; "
                        "the guard still ran on every call"}
        f = paths.RESULTS / f"ANALYSIS_{run}.json"
        a = json.loads(f.read_text(encoding="utf-8"))
        a["H2_privacy"]["audit_completeness"] = comp
        f.write_text(json.dumps(a, indent=1, default=str), encoding="utf-8")
        print(json.dumps(comp, indent=1))
