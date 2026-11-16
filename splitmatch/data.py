"""Dataset access. Notes are returned EXACTLY as the INDICON baselines saw them
(no text repair), so every system is compared on identical input."""
from __future__ import annotations

import json
from functools import lru_cache

import pandas as pd

from . import paths
from .llm import REGISTRY

LABEL = {"Eligible": 1, "Not Eligible": 0}


def load_pairs(split: str) -> pd.DataFrame:
    """split ∈ {dev_train, dev_validation, dev (both), test}."""
    if split == "dev":
        return pd.concat([load_pairs("dev_train"), load_pairs("dev_validation")],
                         ignore_index=True)
    df = pd.read_csv(paths.PAIR_FILES[split])
    df = df.rename(columns={"patient_profiles": "patient_profile"})
    df = df.rename(columns={"patient_profile": "note", "inclusion_criteria": "inclusion",
                            "exclusion_criteria": "exclusion"})
    df["label"] = df["label_final"].str.strip().str.lower().map(
        {"eligible": 1, "not eligible": 0})
    assert df["label"].notna().all(), f"unexpected label values in {split}"
    df["split"] = split
    for note in df["note"].unique():
        REGISTRY.register(note)
    return df[["pair_id", "patient_id", "trial_id", "note", "inclusion", "exclusion",
               "label", "split"]]


def patients(split: str) -> dict[str, str]:
    df = load_pairs(split)
    return dict(df.drop_duplicates("patient_id")[["patient_id", "note"]].values)


@lru_cache(maxsize=None)
def trials(which: str) -> dict[str, dict]:
    """which ∈ {development, test, expansion}; keyed by NCT id."""
    out = {}
    for line in open(paths.TRIAL_FILES[which], encoding="utf-8"):
        t = json.loads(line)
        out[t["trial_id"]] = t
    return out


def all_trials() -> dict[str, dict]:
    d = {}
    for w in paths.TRIAL_FILES:
        d.update(trials(w))
    return d


def expansion_patients() -> list[dict]:
    """Expansion patients WITH true generator attributes (fresh extraction check)."""
    recs = [json.loads(l) for l in open(paths.EXPANSION_PATIENTS / "patients_expansion.jsonl",
                                        encoding="utf-8")]
    for r in recs:
        REGISTRY.register(r["narrative"])
    return recs
