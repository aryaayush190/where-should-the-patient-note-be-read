"""
splitmatch/stats.py — pre-registered statistics (PREREGISTRATION §4).

Procedures are ported from the authors' INDICON analysis (baselines_indicon/code/
exp9_significance.py, exp10_revision_fixes.py) so both studies use identical
tests: exact McNemar, trial-cluster sign-flip permutation (exact over 2^m), and
trial-cluster percentile bootstrap (B=5000, seed 20260815).

Inputs everywhere: dict pair_id -> {"pred": 0/1/None, "y": 0/1, "trial": str, "patient": str}
(pred None = abstention; counted incorrect for accuracy).
"""
from __future__ import annotations

import math

import numpy as np

B = 5000
SEED = 20260815


def rng():
    return np.random.default_rng(SEED)


def correct(d: dict, ids) -> np.ndarray:
    return np.array([1 if (d[i]["pred"] is not None and d[i]["pred"] == d[i]["y"]) else 0
                     for i in ids], dtype=np.int64)


def confusion(d: dict, ids=None) -> dict:
    ids = list(ids or d)
    tp = sum(1 for i in ids if d[i]["pred"] == 1 and d[i]["y"] == 1)
    fp = sum(1 for i in ids if d[i]["pred"] == 1 and d[i]["y"] == 0)
    fn = sum(1 for i in ids if d[i]["pred"] == 0 and d[i]["y"] == 1)
    tn = sum(1 for i in ids if d[i]["pred"] == 0 and d[i]["y"] == 0)
    dec = tp + fp + fn + tn
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    return {"n": len(ids), "decided": dec, "coverage": dec / len(ids), "acc": (tp + tn) / len(ids),
            "precision": p, "recall": r, "f1": 2 * p * r / (p + r) if p + r else 0.0,
            "tp": tp, "fp": fp, "fn": fn, "tn": tn}


def mcnemar(a: dict, b: dict, ids) -> dict:
    ca, cb = correct(a, ids), correct(b, ids)
    b10 = int(((ca == 1) & (cb == 0)).sum())
    b01 = int(((ca == 0) & (cb == 1)).sum())
    n, k = b01 + b10, min(b01, b10)
    p = min(1.0, 2.0 * sum(math.comb(n, i) for i in range(k + 1)) * 0.5 ** n) if n else 1.0
    return {"A_only_correct": b10, "B_only_correct": b01, "p_exact": p}


def _clusters(d: dict, ids, key: str) -> dict:
    cl: dict = {}
    for j, i in enumerate(ids):
        cl.setdefault(d[i][key], []).append(j)
    return cl


def sign_flip(a: dict, b: dict, ids, key: str = "trial") -> dict:
    ids = list(ids)
    dv = correct(a, ids) - correct(b, ids)
    S = np.array([int(dv[ix].sum()) for ix in _clusters(a, ids, key).values()], dtype=np.int64)
    m, T = len(S), abs(int(S.sum()))
    total, ge = 1 << m, 0
    chunk = 1 << min(m, 16)
    base = np.arange(chunk, dtype=np.int64)
    for start in range(0, total, chunk):
        idx = base[: min(chunk, total - start)] + start
        signs = 1 - 2 * ((idx[:, None] >> np.arange(m)) & 1)
        ge += int((np.abs(signs @ S) >= T).sum())
    return {"n_clusters": m, "net_diff": int(S.sum()), "p": ge / total}


def cluster_boot(fn, d_list: list[dict], ids, key: str = "trial") -> tuple[float, list[float]]:
    """Generic trial-cluster bootstrap of a statistic fn(*ds, ids_subset)."""
    ids = list(ids)
    cl = _clusters(d_list[0], ids, key)
    keys = list(cl)
    r = rng()
    vals = np.empty(B)
    for bi in range(B):
        chosen = r.integers(0, len(keys), size=len(keys))
        sub = [ids[j] for k in chosen for j in cl[keys[k]]]
        vals[bi] = fn(*d_list, sub)
    lo, hi = np.percentile(vals, [2.5, 97.5])
    return float(fn(*d_list, ids)), [float(lo), float(hi)]


def acc_diff(a, b, ids):
    return float((correct(a, ids) - correct(b, ids)).mean())


def f1_of(a, ids):
    return confusion(a, ids)["f1"]


def f1_diff(a, b, ids):
    return confusion(a, ids)["f1"] - confusion(b, ids)["f1"]


def non_inferiority(a: dict, b: dict, ids, margin: float = -0.05) -> dict:
    """H1: A non-inferior to B iff trial-cluster 95% CI lower bound of acc(A)-acc(B) > margin."""
    point, ci = cluster_boot(acc_diff, [a, b], ids)
    fpoint, fci = cluster_boot(f1_diff, [a, b], ids)
    return {"acc_diff": point, "acc_diff_ci95": ci, "margin": margin,
            "non_inferior": bool(ci[0] > margin), "f1_diff": fpoint, "f1_diff_ci95": fci,
            "mcnemar": mcnemar(a, b, ids), "sign_flip_trial": sign_flip(a, b, ids)}


def aurc(scores: list[float], correct_flags: list[int]) -> float:
    """Area under the risk-coverage curve; lower = better. Rank by ascending
    uncertainty (most confident first); ties broken by input order."""
    order = sorted(range(len(scores)), key=lambda i: (scores[i], i))
    risks, err = [], 0
    for k, i in enumerate(order, 1):
        err += 1 - correct_flags[i]
        risks.append(err / k)
    return float(np.mean(risks))
