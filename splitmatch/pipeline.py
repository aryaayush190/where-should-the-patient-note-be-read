"""
splitmatch/pipeline.py — end-to-end SPLIT-Match run over a set of pairs.

Work is organised to make the O(P + T) cost structure explicit:
  per TRIAL  : one compiled program (cloud, cached on disk)
  per PATIENT: one structuring call + one batched L1 call (edge)
  per PAIR   : deterministic evaluation (+ occasional single-fact L2 calls)
"""
from __future__ import annotations

import json
import time
from dataclasses import asdict
from pathlib import Path

import pandas as pd

from . import paths
from .evaluator import evaluate_program
from .ladder import item_key, l1_batch
from .llm import Channel
from .policy import Config, decide, uncertainty
from .render import statement
from .schema import AtomType, FactSheet, TrialProgram
from .structurer import structure


def load_programs(which: str, variant: str = "") -> dict[str, TrialProgram]:
    d = paths.RESULTS / "programs" / (which + variant)
    return {p.stem: TrialProgram.model_validate_json(p.read_text(encoding="utf-8"))
            for p in d.glob("*.json")}


def boolean_only(prog: TrialProgram) -> TrialProgram:
    """Ablation H7: COUNT/WITHIN/SINCE/IF lose their typed form (become JUDGE)."""
    def conv(a):
        if a.type in (AtomType.COUNT, AtomType.WITHIN, AtomType.SINCE, AtomType.IF):
            return a.model_copy(update={"type": AtomType.JUDGE, "children": [],
                                        "text": a.source_line or a.text})
        return a.model_copy(update={"children": [conv(c) for c in a.children]})
    return TrialProgram(trial_id=prog.trial_id, atoms=[conv(a) for a in prog.atoms],
                        compiler_meta=prog.compiler_meta)


def residual_statements(prog: TrialProgram, fs: FactSheet, cfg: Config) -> dict[str, str]:
    out = {}
    for atom, r in evaluate_program(prog, fs):
        if r.unscreenable:
            continue
        v, pol = r.value.value, atom.polarity
        neg = (pol == "inclusion" and v == "F") or (pol == "exclusion" and v == "T")
        pos = (pol == "inclusion" and v == "T") or (pol == "exclusion" and v == "F")
        if (neg and (r.verified or cfg.hard_veto)) or (pos and atom.type is not AtomType.JUDGE):
            continue
        s = statement(atom)
        out[item_key(s)] = s
    return out


def run(pairs: pd.DataFrame, programs: dict[str, TrialProgram], edge: Channel, run_name: str,
        cfg: Config | None = None, factsheets: dict[str, FactSheet] | None = None,
        notes: dict[str, str] | None = None, transform=None, log=None) -> pd.DataFrame:
    """notes: optional {patient_id: note} override (stress variants);
    transform: optional program transform (ablations)."""
    cfg = cfg or Config()
    log = log or (lambda m: print(m, flush=True))
    out_dir = paths.RESULTS / "runs" / run_name
    (out_dir / "factsheets").mkdir(parents=True, exist_ok=True)
    (out_dir / "pairs").mkdir(parents=True, exist_ok=True)
    rid = f"run:{run_name}"
    notes = notes or dict(pairs.drop_duplicates("patient_id")[["patient_id", "note"]].values)
    progs = {t: (transform(p) if transform else p) for t, p in programs.items()}
    timing = {"structure_s": [], "l1_s": [], "eval_ms": []}

    # 1) structure each patient once (edge)
    fss = dict(factsheets or {})
    for pid in sorted(notes):
        if pid in fss:
            continue
        f = out_dir / "factsheets" / f"{pid}.json"
        if f.exists():
            fss[pid] = FactSheet.model_validate_json(f.read_text(encoding="utf-8"))
            continue
        t0 = time.perf_counter()
        fs = structure(pid, notes[pid], edge, run_id=rid)
        timing["structure_s"].append(time.perf_counter() - t0)
        f.write_text(fs.model_dump_json(indent=1), encoding="utf-8")
        fss[pid] = fs
        log(f"[{run_name}] structured {pid} ({timing['structure_s'][-1]:.1f}s)")

    # 2) batched L1 per patient (edge)
    l1_all: dict[str, dict] = {}
    for pid, g in pairs.groupby("patient_id"):
        f = out_dir / "factsheets" / f"{pid}.l1.json"
        stm = {}
        for tid in g.trial_id:
            stm.update(residual_statements(progs[tid], fss[pid], cfg))
        if f.exists():
            cached = json.loads(f.read_text(encoding="utf-8"))
            if set(stm) <= set(cached) and "_errors" not in cached and "_error" not in cached:
                l1_all[pid] = cached
                continue
        t0 = time.perf_counter()
        l1_all[pid] = l1_batch(pid, notes[pid], stm, edge, run_id=rid) if (stm and cfg.use_l1) else {}
        timing["l1_s"].append(time.perf_counter() - t0)
        f.write_text(json.dumps(l1_all[pid], indent=1), encoding="utf-8")
        log(f"[{run_name}] L1 {pid}: {len(stm)} statements ({timing['l1_s'][-1]:.1f}s)")

    # 3) per-pair decision
    rows = []
    for _, p in pairs.iterrows():
        t0 = time.perf_counter()
        res = evaluate_program(progs[p.trial_id], fss[p.patient_id])
        timing["eval_ms"].append((time.perf_counter() - t0) * 1000)
        d = decide(res, l1_all.get(p.patient_id, {}), cfg, local_ref=p.pair_id, run_id=rid,
                   fs=fss[p.patient_id])
        rec = {"pair_id": p.pair_id, "patient_id": p.patient_id, "trial_id": p.trial_id,
               "label": int(p.label), "selective": d.selective, "forced": d.forced,
               "n_l2": d.n_l2, "n_forced_unknown": d.n_forced_unknown,
               "n_provisional": d.n_provisional, "u": uncertainty(d),
               "asks": d.asks, "n_atoms": len(res)}
        (out_dir / "pairs" / f"{p.pair_id}.json").write_text(
            json.dumps({**rec, "trace": d.trace, "site_verify": d.site_verify}, indent=1),
            encoding="utf-8")
        rows.append(rec)
    df = pd.DataFrame(rows)
    df.to_json(out_dir / "predictions.jsonl", orient="records", lines=True)
    (out_dir / "timing.json").write_text(json.dumps(timing), encoding="utf-8")
    return df


def metrics(df: pd.DataFrame) -> dict:
    y = df["label"].values
    out = {"n": len(df)}
    for mode in ("forced", "selective"):
        pred = df[mode].values
        decided = [p in ("ELIGIBLE", "NOT_ELIGIBLE") for p in pred]
        yhat = [1 if p == "ELIGIBLE" else 0 for p in pred]
        tp = sum(1 for a, b, d in zip(y, yhat, decided) if d and a == 1 and b == 1)
        fp = sum(1 for a, b, d in zip(y, yhat, decided) if d and a == 0 and b == 1)
        fn = sum(1 for a, b, d in zip(y, yhat, decided) if d and a == 1 and b == 0)
        tn = sum(1 for a, b, d in zip(y, yhat, decided) if d and a == 0 and b == 0)
        nd = sum(decided)
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        out[mode] = {"coverage": nd / len(df), "acc_all": (tp + tn) / len(df),
                     "acc_decided": (tp + tn) / nd if nd else 0.0, "precision": prec,
                     "recall": rec, "f1": 2 * prec * rec / (prec + rec) if prec + rec else 0.0,
                     "tp": tp, "fp": fp, "fn": fn, "tn": tn,
                     "dist": pd.Series(pred).value_counts().to_dict()}
    # descriptive (not pre-registered): "eligible pending confirmation" — NEED_INFO counts as a
    # provisional ELIGIBLE with a question list; only DEFER abstains
    pend = df["selective"].replace({"NEED_INFO": "ELIGIBLE"})
    dec = pend.isin(["ELIGIBLE", "NOT_ELIGIBLE"])
    yh = (pend == "ELIGIBLE").astype(int)
    tp = int(((yh == 1) & (df.label == 1) & dec).sum())
    fp = int(((yh == 1) & (df.label == 0) & dec).sum())
    fn = int(((yh == 0) & (df.label == 1) & dec).sum())
    tn = int(((yh == 0) & (df.label == 0) & dec).sum())
    pr = tp / (tp + fp) if tp + fp else 0.0
    rc = tp / (tp + fn) if tp + fn else 0.0
    out["pending_as_eligible"] = {"coverage": float(dec.mean()), "acc_decided": (tp + tn) / max(int(dec.sum()), 1),
                                  "precision": pr, "recall": rc,
                                  "f1": 2 * pr * rc / (pr + rc) if pr + rc else 0.0,
                                  "tp": tp, "fp": fp, "fn": fn, "tn": tn}
    out["mean_l2_per_pair"] = float(df["n_l2"].mean())
    out["offline_decided"] = float(((df["n_l2"] == 0) &
                                    df["selective"].isin(["ELIGIBLE", "NOT_ELIGIBLE"])).mean())
    return out
