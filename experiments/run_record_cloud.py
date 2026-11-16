"""EXPLORATORY (post-hoc, not pre-registered; added 2026-11-08 after the frozen test run).

Decomposes the SPLIT-Match accuracy gap: the cloud model makes the eligibility decision
from the DE-IDENTIFIED STRUCTURED FACT SHEET produced on the edge (no narrative, no
identifiers, age as a 10-year band) plus the public criteria, using the same zero-shot
prompt as the cloud baseline.

    python experiments/run_record_cloud.py --split test --factsheets-from TEST_proxy --name REC_cloud_test_proxy

If this approaches the narrative-to-cloud baseline, the edge extraction preserves the
decision-relevant information and the gap lies in the compiled decision layer.
"""
import argparse
import json
import math
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from splitmatch import data, llm, paths  # noqa: E402
from splitmatch.baseline import BASELINE_SYSTEM, parse_vote  # noqa: E402
from splitmatch.llm import Channel  # noqa: E402
from splitmatch.schema import FactSheet  # noqa: E402


def fmt_iv(v):
    lo, hi = v
    if lo == hi:
        return f"{lo:g}"
    if not math.isfinite(hi):
        return f">= {lo:g}"
    if not math.isfinite(lo):
        return f"<= {hi:g}"
    return f"{lo:g}-{hi:g}"


def render_record(fs: FactSheet) -> tuple[str, list[str]]:
    lines, fields = [], []
    for n, f in sorted(fs.fields.items()):
        if f.status.value == "not_mentioned":
            continue
        if n == "age" and f.status.value == "value":
            lo = int(f.value[0]) // 10 * 10
            lines.append(f"age band: {lo}-{lo + 9}")
        elif f.status.value == "negated":
            lines.append(f"{n}: absent")
        else:
            v = fmt_iv(f.value) if isinstance(f.value, list) else f.value
            lines.append(f"{n}: {v}")
        fields.append(n)
    if fs.therapy_status.value == "negated":
        lines.append("prior anticancer therapy: none")
    for e in fs.events:
        t = f"prior {e.cls}"
        if e.agents:
            t += f" ({', '.join(e.agents)})"
        if e.months_ago:
            t += f", last dose {fmt_iv(e.months_ago)} months ago"
        if e.ongoing:
            t += ", ongoing"
        lines.append(t)
    if fs.lines_of_therapy:
        lines.append(f"prior lines of therapy: {fmt_iv(fs.lines_of_therapy)}")
    return "\n".join(lines), fields


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="test")
    ap.add_argument("--factsheets-from", required=True)
    ap.add_argument("--name", required=True)
    # round-5 review (2026-11-10): the same model that drives SPLIT-Match decides from its own fact sheet,
    # isolating "fact-sheet representation" from "rule layer" at a fixed model
    ap.add_argument("--decider", default="cloud", choices=["cloud", "edge_proxy", "edge_local"])
    a = ap.parse_args()
    pairs = data.load_pairs(a.split)
    d = paths.RESULTS / "runs" / a.factsheets_from / "factsheets"
    fss = {p.stem: FactSheet.model_validate_json(p.read_text(encoding="utf-8"))
           for p in d.glob("P*.json") if not p.name.endswith(".l1.json")}

    def one(r):
        rec, fields = render_record(fss[r.patient_id])
        user = (f"PATIENT RECORD (structured, de-identified):\n{rec}\n\n"
                f"TRIAL INCLUSION CRITERIA:\n{r.inclusion[:4000]}\n\n"
                f"TRIAL EXCLUSION CRITERIA:\n{r.exclusion[:4000]}\n"
                "\nDecide eligibility. Respond in the required JSON format.")
        msgs = [{"role": "system", "content": BASELINE_SYSTEM}, {"role": "user", "content": user}]
        if a.decider == "cloud":
            rep = llm.call(Channel.CLOUD_FACT, msgs, model=llm.CLOUD_PRIMARY, max_tokens=1000,
                           extra={"reasoning_effort": "low"}, run_id=f"rec:{a.name}", tag="record_cloud",
                           local_ref=r.pair_id, disclosed_fields=fields)
        elif a.decider == "edge_proxy":   # same settings as the -compiler ablation (run_ablations.edge_zero_shot)
            rep = llm.call(Channel.EDGE_PROXY, msgs, model=llm.EDGE_PROXY_MODEL, max_tokens=1500,
                           extra={"reasoning_effort": "low"}, run_id=f"rec:{a.name}", tag="record_edge",
                           local_ref=r.pair_id)
        else:                              # same settings as the local zero-shot (baseline.zero_shot, EDGE_LOCAL)
            rep = llm.call(Channel.EDGE_LOCAL, msgs, model=llm.EDGE_LOCAL_MODEL, max_tokens=300,
                           extra={"json": True, "num_ctx": 8192}, run_id=f"rec:{a.name}", tag="record_edge",
                           local_ref=r.pair_id)
        pred, conf = parse_vote(rep.text)
        if pred is None:
            pred, conf = "Not Eligible", 0.5
        pred = "Eligible" if str(pred).strip().lower() == "eligible" else "Not Eligible"
        return {"pair_id": r.pair_id, "trial_id": r.trial_id, "label": int(r.label),
                "prediction": pred, "confidence": conf, "n_fields": len(fields),
                "latency_s": rep.meta.get("latency_s"), "cached": rep.cached}

    with ThreadPoolExecutor(1 if a.decider == "edge_local" else 4) as ex:
        res = list(ex.map(one, list(pairs.itertuples())))
    out = paths.RESULTS / "baselines" / f"{a.name}.jsonl"
    with open(out, "w", encoding="utf-8") as f:
        for r in res:
            f.write(json.dumps(r) + "\n")
    acc = sum((r["prediction"] == "Eligible") == (r["label"] == 1) for r in res) / len(res)
    print(a.name, "n", len(res), "acc", round(acc, 4))


if __name__ == "__main__":
    main()
