"""Pre-registered test-set ablations (PREREGISTRATION §4, "Ablations"), frozen configuration.

    python experiments/run_ablations.py [--only NAME ...]

All ablations use the cloud stand-in edge (EDGE_PROXY) and REUSE the TEST_proxy fact sheets,
so each one changes exactly one component relative to TEST_proxy:

  AB_hardveto      any decisive negative atom excludes (no evidence-conditioned authority)
  AB_noL1          -L1 (no edge judge; residuals go straight to L2 / ASK)
  AB_noL2          -L2 (offline only; no cloud fact queries)
  AB_boolean       COUNT/WITHIN/SINCE/IF converted to JUDGE (H7)
  AB_single        single-model compiler (gpt-oss-120b only; every typed atom keeps authority)
  AB_noverify      single SLM reader: SLM facts count as verified without the regex reader;
                   regex-only facts and regex-fallback therapy events are dropped
  AB_nocompiler    edge model judges the raw criteria per pair (INDICON zero-shot prompt,
                   gpt-oss-20b on EDGE_PROXY); the deployable version is ZS_edge_qwen4b_test

This driver was written after the freeze; it calls only frozen code paths
(pipeline.run, Config flags, boolean_only, compile_trial(single_model=True), baseline prompt).
"""
import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from splitmatch import data, llm, paths  # noqa: E402
from splitmatch.baseline import BASELINE_SYSTEM, parse_vote, user_block  # noqa: E402
from splitmatch.compiler import compile_trial  # noqa: E402
from splitmatch.llm import Channel  # noqa: E402
from splitmatch.pipeline import boolean_only, load_programs, metrics, run  # noqa: E402
from splitmatch.policy import Config  # noqa: E402
from splitmatch.schema import FactSheet  # noqa: E402

BASE = "TEST_proxy"


def base_factsheets() -> dict[str, FactSheet]:
    d = paths.RESULTS / "runs" / BASE / "factsheets"
    return {p.stem: FactSheet.model_validate_json(p.read_text(encoding="utf-8"))
            for p in d.glob("P*.json") if not p.name.endswith(".l1.json")}


def no_verify(fs: FactSheet) -> FactSheet:
    fields = {n: f.model_copy(update={"verified": True})
              for n, f in fs.fields.items() if f.readers and f.readers != ["regex"]}
    events = [e.model_copy(update={"verified": True}) for e in fs.events if e.evidence]
    meta = dict(fs.reader_meta, therapy_verified=True)
    return fs.model_copy(update={"fields": fields, "events": events, "reader_meta": meta})


def single_programs() -> dict:
    out = paths.RESULTS / "programs" / "test_single"
    out.mkdir(parents=True, exist_ok=True)
    trials = data.trials("test")

    def one(item):
        tid, t = item
        f = out / f"{tid}.json"
        if not f.exists():
            f.write_text(compile_trial(t, run_id="compile-test", single_model=True)
                         .model_dump_json(indent=1), encoding="utf-8")
    with ThreadPoolExecutor(4) as ex:
        list(ex.map(one, trials.items()))
    return load_programs("test", "_single")


def edge_zero_shot(pairs, name):
    def one(r):
        msgs = [{"role": "system", "content": BASELINE_SYSTEM},
                {"role": "user", "content": user_block(r.note, r.inclusion, r.exclusion)}]
        rep = llm.call(Channel.EDGE_PROXY, msgs, model=llm.EDGE_PROXY_MODEL, max_tokens=1500,
                       extra={"reasoning_effort": "low"}, run_id=f"run:{name}", tag="zero_shot",
                       local_ref=r.pair_id)
        pred, conf = parse_vote(rep.text)
        pred = "Eligible" if str(pred).strip().lower() == "eligible" else "Not Eligible"
        return {"pair_id": r.pair_id, "trial_id": r.trial_id, "label": int(r.label),
                "prediction": pred, "confidence": conf}
    with ThreadPoolExecutor(6) as ex:
        res = list(ex.map(one, list(pairs.itertuples())))
    out = paths.RESULTS / "baselines" / f"{name}.jsonl"
    with open(out, "w", encoding="utf-8") as f:
        for r in res:
            f.write(json.dumps(r) + "\n")
    acc = sum((r["prediction"] == "Eligible") == (r["label"] == 1) for r in res) / len(res)
    print(name, "n", len(res), "acc", round(acc, 4), flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", default=[])
    a = ap.parse_args()
    pairs = data.load_pairs("test")
    progs = load_programs("test")
    fss = base_factsheets()
    edge = Channel.EDGE_PROXY
    jobs = {
        "AB_hardveto": lambda: run(pairs, progs, edge, "AB_hardveto", Config(hard_veto=True), fss),
        "AB_noL1": lambda: run(pairs, progs, edge, "AB_noL1", Config(use_l1=False), fss),
        "AB_noL2": lambda: run(pairs, progs, edge, "AB_noL2", Config(use_l2=False), fss),
        "AB_boolean": lambda: run(pairs, progs, edge, "AB_boolean", Config(), fss, transform=boolean_only),
        "AB_single": lambda: run(pairs, single_programs(), edge, "AB_single", Config(), fss),
        "AB_noverify": lambda: run(pairs, progs, edge, "AB_noverify", Config(),
                                   {p: no_verify(f) for p, f in fss.items()}),
    }
    for name, job in jobs.items():
        if a.only and name not in a.only:
            continue
        df = job()
        m = metrics(df)
        m["ablation"] = name
        (paths.RESULTS / "runs" / name / "metrics.json").write_text(json.dumps(m, indent=1), encoding="utf-8")
        print(name, "forced acc", round(m["forced"]["acc_all"], 4), "f1", round(m["forced"]["f1"], 4),
              "sel cov", round(m["selective"]["coverage"], 3), "sel acc", round(m["selective"]["acc_decided"], 4),
              "l2/pair", round(m["mean_l2_per_pair"], 2), flush=True)
    if not a.only or "AB_nocompiler" in a.only:
        edge_zero_shot(pairs, "AB_nocompiler_proxy20b")


if __name__ == "__main__":
    main()
