"""Regenerate the paper's numbers, tables and figures from the released outputs.

    python scripts/reproduce.py            # level 1: paper numbers from released analyses   (~5 min, CPU only)
    python scripts/reproduce.py --level 2  # level 2: also recompute analyses from per-pair predictions
    python scripts/reproduce.py --figures  # also redraw Figs. 1-3 (needs requirements-paper.txt)

Neither level calls a model. Re-running the experiments themselves (level 3) needs Groq API keys and Ollama;
see README.md. Outputs are written in place (results/, paper/generated/, paper/figures/), so
`git diff --stat` afterwards shows exactly what, if anything, changed.
"""
import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable

LEVEL2 = [
    ["experiments/analyze_run.py", "--run", "TEST_deploy"],   # frozen analyze.py, tolerant call-log loader
    ["experiments/analyze_run.py", "--run", "TEST_proxy"],
    ["experiments/analyze_run.py", "--run", "TEST_proxy", "--stress-edge", "proxy"],
    ["experiments/fidelity.py", "--local", "TEST_deploy", "--proxy", "TEST_proxy"],
    ["experiments/analyze_extra.py"],
]
LEVEL1 = [
    ["experiments/l2_attribution.py"],
    ["experiments/gateway_suite.py"],
    ["experiments/review_analysis.py"],
    ["experiments/paper_numbers.py"],
]


def run(cmd):
    print("\n$ python " + " ".join(cmd), flush=True)
    r = subprocess.run([PY, *cmd], cwd=ROOT, env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"},
                       stdout=subprocess.DEVNULL)
    if r.returncode:
        raise SystemExit(f"failed: {' '.join(cmd)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--level", type=int, default=1, choices=[1, 2])
    ap.add_argument("--figures", action="store_true")
    a = ap.parse_args()
    run(["scripts/restore_artifacts.py"])
    run(["scripts/verify_freeze.py"])
    if a.level >= 2:
        for c in LEVEL2:
            run(c)
    for c in LEVEL1:
        run(c)
    if a.figures:
        run(["paper/figures/make_figures.py"])
    print("\nDone. Paper numbers: paper/generated/numbers.tex; compare with `git diff --stat`.")


if __name__ == "__main__":
    main()
