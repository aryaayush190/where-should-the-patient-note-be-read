"""Unpack the released runtime artifacts into runtime/ (git-ignored).

    python scripts/restore_artifacts.py

artifacts/llm_calls.jsonl.gz   every model call of the study (channel, model, run, cloud payloads, timings)
artifacts/llm_cache.tar.gz     cached replies of the pipeline (lets runs replay without API keys or GPUs)
artifacts/review_cache.tar.gz  cached replies of the review runs (experiments/review_runs.py)
artifacts/TEST_deploy.log.gz   log of the laptop SPLIT-Match run (laptop-judge timings; key prefixes redacted)

All patients in these files are synthetic; no API keys are included.
"""
import gzip
import shutil
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ART, RUN = ROOT / "artifacts", ROOT / "runtime"


def main():
    RUN.mkdir(exist_ok=True)
    for gz, out in (("llm_calls.jsonl.gz", "llm_calls.jsonl"), ("TEST_deploy.log.gz", "TEST_deploy.log")):
        dst = RUN / out
        if dst.exists():
            print(f"skip {out} (exists)")
            continue
        with gzip.open(ART / gz, "rb") as fi, open(dst, "wb") as fo:
            shutil.copyfileobj(fi, fo)
        print(f"restored runtime/{out}")
    for name in ("llm_cache", "review_cache"):
        if (RUN / name).exists() and any((RUN / name).iterdir()):
            print(f"skip {name}/ (exists)")
            continue
        with tarfile.open(ART / f"{name}.tar.gz", "r:gz") as t:
            if sys.version_info >= (3, 12):
                t.extractall(RUN, filter="data")
            else:
                t.extractall(RUN)
        print(f"restored runtime/{name}/")


if __name__ == "__main__":
    main()
