"""Single source of truth for project paths (everything lives under TELEMED_PERCOM/)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DATA = ROOT / "data"
PAIRS = DATA / "pairs"
TRIALS = DATA / "trials"
EXPANSION_PATIENTS = DATA / "expansion_patients"

BASELINES = ROOT / "baselines_indicon"
BASELINE_CACHE = BASELINES / "cache"

RESULTS = ROOT / "results"
RUNTIME = ROOT / "runtime"            # raw LLM traffic + caches (gitignored)
LLM_LOG = RUNTIME / "llm_calls.jsonl"
LLM_CACHE = RUNTIME / "llm_cache"

PAIR_FILES = {
    "dev_train": PAIRS / "dev_train.csv",
    "dev_validation": PAIRS / "dev_validation.csv",
    "test": PAIRS / "testing_data.csv",
}
TRIAL_FILES = {
    "development": TRIALS / "trials_development.jsonl",
    "test": TRIALS / "trials_test.jsonl",
    "expansion": TRIALS / "trials_development_expansion.jsonl",
}

for _d in (RESULTS, RUNTIME, LLM_CACHE):
    _d.mkdir(parents=True, exist_ok=True)
