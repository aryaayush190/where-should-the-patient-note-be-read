"""Runs added in response to the TELMED pre-submission review (2026-11-09). EXPLORATORY.

None of these runs changes a frozen file or SPLIT-Match itself. Every condition uses the
same zero-shot prompt as the cloud baseline (splitmatch.baseline: BASELINE_SYSTEM, user_block).

Subcommands
    zs-groq   : hosted zero-shot, optionally repeated without the cache (noise floor)
                python experiments/review_runs.py zs-groq --model openai/gpt-oss-120b --name NF_cloud --reps 3
    zs-local  : local Ollama zero-shot with latency, tokens/s and peak RAM
                python experiments/review_runs.py zs-local --model gpt-oss:20b --name LOC_gptoss20b_pilot --pairs pilot20
    render-long : build long, cluttered versions of the 45 test notes (LLM clutter + verbatim original)
    screen-long : drop clutter sentences that an independent model finds relevant to a paired trial
    subset    : write the stratified pair subsets (pilot20, sub40)

Outputs go to results/review/<name>.jsonl (one row per pair and repetition; resumable).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from splitmatch import data, llm, paths  # noqa: E402
from splitmatch.baseline import BASELINE_SYSTEM, parse_vote, user_block  # noqa: E402
from splitmatch.llm import Channel  # noqa: E402

OUT = paths.RESULTS / "review"
OUT.mkdir(parents=True, exist_ok=True)
CACHE = paths.ROOT / "runtime" / "review_cache"
OLLAMA = "http://127.0.0.1:11434"
LONG_NOTES = OUT / "long_notes.json"
LONG_NOTES_SCREENED = OUT / "long_notes_screened.json"


# ── helpers ──────────────────────────────────────────────────────────────────
def load(split="test"):
    return data.load_pairs(split)


def notes_for(pairs, which: str) -> dict:
    notes = dict(pairs.drop_duplicates("patient_id")[["patient_id", "note"]].values)
    if which == "long":
        d = json.loads(LONG_NOTES_SCREENED.read_text(encoding="utf-8"))
        return {p: d[p]["long_note"] for p in notes}
    return notes


def done_keys(f: Path) -> set:
    if not f.exists():
        return set()
    out = set()
    for line in f.read_text(encoding="utf-8").splitlines():
        try:
            r = json.loads(line)
            if "prediction" in r:          # failed attempts are retried, not skipped
                out.add((r["pair_id"], r.get("rep", 0)))
        except Exception:
            continue
    return out


_wlock = threading.Lock()


def append(f: Path, row: dict) -> None:
    with _wlock, open(f, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def norm_pred(text: str):
    pred, conf = parse_vote(text)
    if pred is None:
        return "Not Eligible", 0.5, False
    return ("Eligible" if str(pred).strip().lower() == "eligible" else "Not Eligible"), conf, True


def subset_ids(pairs, name: str) -> list[str]:
    f = OUT / f"subset_{name}.json"
    return json.loads(f.read_text(encoding="utf-8"))


# ── subsets ──────────────────────────────────────────────────────────────────
def cmd_subset(a):
    """Stratified by trial and label: pilot20 (20 pairs) and sub40 (40 pairs, contains pilot20)."""
    pairs = load("test")
    rng = random.Random(20261109)
    by = {}
    for r in pairs.itertuples():
        by.setdefault((r.trial_id, int(r.label)), []).append(r.pair_id)
    for v in by.values():
        rng.shuffle(v)
    trials = sorted(pairs.trial_id.unique())
    order = []
    # round-robin over trials, alternating label, so every trial and both labels appear
    for rnd in range(20):
        for t in trials:
            lab = (rnd + trials.index(t)) % 2
            for lb in (lab, 1 - lab):
                lst = by.get((t, lb), [])
                if lst:
                    order.append(lst.pop())
                    break
    seen, uniq = set(), []
    for p in order:
        if p not in seen:
            seen.add(p)
            uniq.append(p)
    sub40 = uniq[:40]
    pilot = sub40[:20]
    (OUT / "subset_pilot20.json").write_text(json.dumps(pilot, indent=1), encoding="utf-8")
    (OUT / "subset_sub40.json").write_text(json.dumps(sub40, indent=1), encoding="utf-8")
    lab = dict(zip(pairs.pair_id, pairs.label))
    print("pilot20 eligible", sum(lab[p] for p in pilot), "sub40 eligible", sum(lab[p] for p in sub40),
          "trials in sub40", len({p.split("__")[1] for p in sub40}))


# ── hosted zero-shot (noise floor, capacity points, long notes) ──────────────
def groq_params(model: str):
    if model == "openai/gpt-oss-120b":
        return {"reasoning_effort": "low"}, 1000, Channel.BASELINE_CLOUD
    if model == "openai/gpt-oss-20b":
        return {"reasoning_effort": "low"}, 1500, Channel.EDGE_PROXY
    return {}, 4000, Channel.BASELINE_CLOUD


def cmd_zs_groq(a):
    pairs = load(a.split)
    notes = notes_for(pairs, a.notes)
    extra, mt, ch = groq_params(a.model)
    f = OUT / f"{a.name}.jsonl"
    done = done_keys(f)
    rows = [r for r in pairs.itertuples()]
    jobs = [(r, k) for k in range(a.reps) for r in rows if (r.pair_id, k) not in done]

    def one(job):
        r, k = job
        msgs = [{"role": "system", "content": BASELINE_SYSTEM},
                {"role": "user", "content": user_block(notes[r.patient_id], r.inclusion, r.exclusion)}]
        t0 = time.perf_counter()
        rep = llm.call(ch, msgs, model=a.model, max_tokens=mt, extra=dict(extra),
                       run_id=f"review:{a.name}:r{k}", tag="zero_shot", local_ref=r.pair_id,
                       use_cache=not a.nocache)
        pred, conf, ok = norm_pred(rep.text)
        append(f, {"pair_id": r.pair_id, "trial_id": r.trial_id, "patient_id": r.patient_id,
                   "label": int(r.label), "rep": k, "prediction": pred, "confidence": conf,
                   "parsed": ok, "latency_s": round(time.perf_counter() - t0, 3), "raw": rep.text[-600:]})

    with ThreadPoolExecutor(a.workers) as ex:
        list(ex.map(one, jobs))
    summarise(f)


def summarise(f: Path):
    rows = [json.loads(x) for x in f.read_text(encoding="utf-8").splitlines() if x.strip()]
    rows = [r for r in rows if "prediction" in r]
    reps = sorted({r.get("rep", 0) for r in rows})
    for k in reps:
        rr = [r for r in rows if r.get("rep", 0) == k]
        acc = sum((r["prediction"] == "Eligible") == (r["label"] == 1) for r in rr) / max(1, len(rr))
        print(f.stem, "rep", k, "n", len(rr), "acc", round(acc, 4),
              "unparsed", sum(not r.get("parsed", True) for r in rr), flush=True)


# ── local Ollama zero-shot with resource measurement ────────────────────────
class RamSampler(threading.Thread):
    """Samples the summed resident memory of Ollama / llama-server processes every 0.5 s."""

    def __init__(self):
        super().__init__(daemon=True)
        self.peak_mb, self.cur_peak_mb, self.stop_flag = 0.0, 0.0, False

    def run(self):
        import psutil
        while not self.stop_flag:
            tot = 0
            for p in psutil.process_iter(["name", "memory_info"]):
                n = (p.info["name"] or "").lower()
                if "ollama" in n or "llama" in n:
                    try:
                        tot += p.info["memory_info"].rss
                    except Exception:
                        pass
            mb = tot / 2**20
            self.peak_mb = max(self.peak_mb, mb)
            self.cur_peak_mb = max(self.cur_peak_mb, mb)
            time.sleep(0.5)

    def take(self) -> float:
        v, self.cur_peak_mb = self.cur_peak_mb, 0.0
        return round(v, 1)


def ollama_chat(model, msgs, opts, think, fmt_json, timeout, use_cache=True):
    body = {"model": model, "messages": msgs, "stream": False, "options": opts, "keep_alive": "30m"}
    if think is not None:
        body["think"] = think
    if fmt_json:
        body["format"] = "json"
    key = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
    cf = CACHE / key[:2] / f"{key}.json"
    if use_cache and cf.exists():
        return json.loads(cf.read_text(encoding="utf-8")), True
    r = requests.post(f"{OLLAMA}/api/chat", json=body, timeout=timeout)
    r.raise_for_status()
    j = r.json()
    if use_cache:  # fresh repeat runs must not overwrite the first run's cached replies
        cf.parent.mkdir(parents=True, exist_ok=True)
        cf.write_text(json.dumps(j), encoding="utf-8")
    return j, False


def parse_think(v: str):
    if v in ("", "none"):
        return None
    if v in ("false", "true"):
        return v == "true"
    return v  # "low" / "medium" / "high" for gpt-oss


def cmd_zs_local(a):
    pairs = load(a.split)
    notes = notes_for(pairs, a.notes)
    if a.pairs:
        keep = set(subset_ids(pairs, a.pairs))
        pairs = pairs[pairs.pair_id.isin(keep)]
    f = OUT / f"{a.name}.jsonl"
    done = done_keys(f)
    opts = {"temperature": 0.0, "num_predict": a.max_tokens, "num_ctx": a.num_ctx, "seed": 0}
    think = parse_think(a.think)
    ram = RamSampler()
    ram.start()
    for r in pairs.itertuples():
        if (r.pair_id, a.rep) in done:
            continue
        msgs = [{"role": "system", "content": BASELINE_SYSTEM},
                {"role": "user", "content": user_block(notes[r.patient_id], r.inclusion, r.exclusion)}]
        t0 = time.perf_counter()
        try:
            j, cached = ollama_chat(a.model, msgs, opts, think, a.json, a.timeout, use_cache=not a.nocache)
        except Exception as e:  # infrastructure failure is recorded, not hidden
            append(f, {"pair_id": r.pair_id, "trial_id": r.trial_id, "patient_id": r.patient_id,
                       "label": int(r.label), "rep": a.rep, "error": f"{type(e).__name__}: {str(e)[:200]}",
                       "wall_s": round(time.perf_counter() - t0, 1), "peak_ram_mb": ram.take()})
            print("ERROR", r.pair_id, type(e).__name__, flush=True)
            if a.stop_on_error:
                break
            continue
        wall = time.perf_counter() - t0
        text = (j.get("message") or {}).get("content", "")
        pred, conf, ok = norm_pred(text)
        ev_n, ev_s = j.get("eval_count") or 0, (j.get("eval_duration") or 0) / 1e9
        pe_n, pe_s = j.get("prompt_eval_count") or 0, (j.get("prompt_eval_duration") or 0) / 1e9
        row = {"pair_id": r.pair_id, "trial_id": r.trial_id, "patient_id": r.patient_id,
               "label": int(r.label), "rep": a.rep, "prediction": pred, "confidence": conf, "parsed": ok,
               "cached": cached, "wall_s": round(wall, 2),
               "latency_s": round((j.get("total_duration") or 0) / 1e9, 2),
               "load_s": round((j.get("load_duration") or 0) / 1e9, 2),
               "prompt_tokens": pe_n, "prompt_s": round(pe_s, 2),
               "prompt_tok_per_s": round(pe_n / pe_s, 2) if pe_s else None,
               "gen_tokens": ev_n, "gen_s": round(ev_s, 2),
               "gen_tok_per_s": round(ev_n / ev_s, 2) if ev_s else None,
               "peak_ram_mb": ram.take(), "thinking_chars": len((j.get("message") or {}).get("thinking") or ""),
               "raw": text[-400:]}
        append(f, row)
        print(a.name, r.pair_id, pred, "label", int(r.label), f"{row['latency_s']}s",
              f"gen {row['gen_tok_per_s']} tok/s", f"peakRAM {row['peak_ram_mb']} MB", flush=True)
    ram.stop_flag = True
    print("overall peak RAM MB", round(ram.peak_mb, 1))
    summarise(f)


# ── long, cluttered notes ───────────────────────────────────────────────────
CLUTTER_SYSTEM = (
    "You write realistic but eligibility-irrelevant filler for an oncology outpatient record. "
    "You will receive a short NSCLC patient summary. Return ONLY a JSON object with keys "
    "'admin', 'social', 'family', 'remote_history', 'logistics', 'other_specialties', each a list of "
    "plain sentences. Write 350-550 words in total. The filler must be consistent with the patient's "
    "age and sex, and must NOT mention or imply: cancer, tumours, staging, biomarkers or genetic tests; "
    "any cancer treatment, surgery, radiotherapy or trial; any medication, supplement, steroid, "
    "anticoagulant, antibiotic, vaccine or herbal remedy; heart, lung, kidney, liver, brain, nerve or "
    "blood conditions; infections, HIV, hepatitis, tuberculosis; autoimmune or psychiatric conditions; "
    "pregnancy, contraception or fertility; laboratory values, vital signs, weight loss, performance or "
    "functional status; smoking, alcohol or drug use; allergies; any symptom. Allowed content: clinic "
    "administration, appointment and referral logistics, transport, family composition and occupation "
    "(non-medical), hobbies, diet preferences without medical reasons, remote (more than 10 years ago) "
    "minor procedures unrelated to the chest such as cataract or dental extraction, spectacles, family "
    "history of non-cancer, non-cardiac conditions such as osteoarthritis or cataract."
)


FALLBACK_CLUTTER = {
    "admin": ["The patient attended the outreach clinic for a scheduled review.",
              "Registration details were confirmed at the front desk and the referral letter was scanned into the record.",
              "The consultation was conducted in the outpatient block with a family member present.",
              "The clinic coordinator noted that the hospital identity card had been renewed this year.",
              "A teleconsultation slot with the tertiary centre was requested through the referral portal."],
    "social": ["The patient lives with their spouse and one adult child in a two-room house.",
               "Family members share responsibility for household chores and for accompanying the patient to visits.",
               "The patient enjoys listening to the radio and following local news.",
               "Meals are prepared at home and the family prefers vegetarian food on weekdays.",
               "The patient attends community gatherings during festivals when travel allows."],
    "family": ["A sibling has osteoarthritis of the knees.",
               "A parent had cataract surgery in old age.",
               "There is no other family history recorded in this section."],
    "remote_history": ["A dental extraction was performed more than fifteen years ago without complications.",
                       "The patient has worn reading spectacles for many years."],
    "logistics": ["The family travels to the clinic by shared jeep, which takes about two hours each way.",
                  "Travel costs are reimbursed under the state scheme after submission of the bus or jeep receipts.",
                  "The next review date will be confirmed by telephone once the referral is accepted.",
                  "The coordinator explained how to reach the helpline in case appointments need to be moved.",
                  "A printed copy of the appointment schedule was handed to the accompanying relative."],
    "other_specialties": ["The ophthalmology outpatient card from a past spectacle prescription was noted.",
                          "No other specialist appointments are pending at this time."],
}


def cmd_render_long(a):
    pairs = load("test")
    notes = dict(pairs.drop_duplicates("patient_id")[["patient_id", "note"]].values)
    out = json.loads(LONG_NOTES.read_text(encoding="utf-8")) if LONG_NOTES.exists() else {}

    def one(pid):
        if pid in out:
            return
        msgs = [{"role": "system", "content": CLUTTER_SYSTEM},
                {"role": "user", "content": f"PATIENT SUMMARY:\n{notes[pid]}\n\nReturn the JSON object."}]
        obj, source = None, "llm_json"
        for extra in ({"reasoning_effort": "low", "response_format": {"type": "json_object"}},
                      {"reasoning_effort": "medium"}):
            try:
                rep = llm.call(Channel.BASELINE_CLOUD, msgs, model=llm.CLOUD_PRIMARY, max_tokens=4000,
                               extra=extra, run_id="review:render_long", tag="render_long", local_ref=pid)
                obj = llm.parse_json(rep.text)
                if isinstance(obj, dict) and sum(len(v) for v in obj.values() if isinstance(v, list)) >= 8:
                    break
                obj = None
            except Exception:
                obj = None
            source = "llm_plain"
        if obj is None:   # model refused twice: neutral fixed filler (still screened afterwards)
            obj, source = FALLBACK_CLUTTER, "fallback_template"
        out[pid] = {"source": source,
                    "clutter": {k: [s.strip() for s in v if isinstance(s, str) and s.strip()]
                                for k, v in obj.items() if isinstance(v, list)}}

    with ThreadPoolExecutor(6) as ex:
        list(ex.map(one, sorted(notes)))
    LONG_NOTES.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print("rendered", len(out))


SCREEN_SYSTEM = (
    "You check filler text added to a patient record. For each numbered sentence, decide whether it "
    "could change, support or contradict the patient's eligibility for the trial below under ANY "
    "inclusion or exclusion criterion (including indirect implications). Be strict: if in doubt, "
    "answer relevant. Return ONLY JSON: {\"relevant\": [list of sentence numbers]}."
)


def split_sents(t: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.!?])\s+", t.strip()) if s]


def assemble(pid: str, note: str, clutter: dict) -> str:
    """Original note verbatim, embedded in the cluttered record, plus a copied-forward block."""
    c = clutter
    parts = ["CLINIC: Regional Cancer Outreach Clinic (teleconsultation spoke). Record type: outpatient review.",
             " ".join(c.get("admin", [])),
             "HISTORY OF PRESENT ILLNESS: " + note,
             "SOCIAL HISTORY: " + " ".join(c.get("social", [])),
             "FAMILY HISTORY: " + " ".join(c.get("family", [])),
             "OTHER HISTORY: " + " ".join(c.get("remote_history", []) + c.get("other_specialties", [])),
             "LOGISTICS: " + " ".join(c.get("logistics", [])),
             "PREVIOUS VISIT SUMMARY (copied forward, unchanged): " + note]
    return "\n\n".join(p for p in parts if p.strip())


def cmd_screen_long(a):
    pairs = load("test")
    notes = dict(pairs.drop_duplicates("patient_id")[["patient_id", "note"]].values)
    longs = json.loads(LONG_NOTES.read_text(encoding="utf-8"))
    by_pid = {p: g for p, g in pairs.groupby("patient_id")}
    res = json.loads(LONG_NOTES_SCREENED.read_text(encoding="utf-8")) if LONG_NOTES_SCREENED.exists() else {}

    def one(pid):
        if pid in res:
            return
        clutter = longs[pid]["clutter"]
        flat = [(k, s) for k, v in clutter.items() for s in v]
        drop = set()
        for r in by_pid[pid].itertuples():
            listing = "\n".join(f"{i + 1}. {s}" for i, (_, s) in enumerate(flat))
            msgs = [{"role": "system", "content": SCREEN_SYSTEM},
                    {"role": "user", "content": f"TRIAL INCLUSION CRITERIA:\n{r.inclusion[:4000]}\n\n"
                                                f"TRIAL EXCLUSION CRITERIA:\n{r.exclusion[:4000]}\n\n"
                                                f"SENTENCES:\n{listing}\n\nReturn the JSON."}]
            rep = llm.call(Channel.BASELINE_CLOUD, msgs, model=llm.CLOUD_SECONDARY, max_tokens=4000,
                           extra={"response_format": {"type": "json_object"}},
                           run_id="review:screen_long", tag="screen_long", local_ref=r.pair_id)
            try:
                rel = llm.parse_json(rep.text).get("relevant", [])
                drop |= {int(i) - 1 for i in rel if str(i).strip().isdigit()}
            except Exception:
                drop |= set(range(len(flat)))  # unparseable verdict: drop all filler (fail safe)
        kept = {}
        for i, (k, s) in enumerate(flat):
            if i not in drop:
                kept.setdefault(k, []).append(s)
        long_note = assemble(pid, notes[pid], kept)
        assert notes[pid] in long_note
        res[pid] = {"long_note": long_note, "n_filler": len(flat), "n_dropped": len(drop),
                    "dropped": [flat[i][1] for i in sorted(drop) if i < len(flat)],
                    "words_short": len(notes[pid].split()), "words_long": len(long_note.split())}

    with ThreadPoolExecutor(4) as ex:
        list(ex.map(one, sorted(notes)))
    LONG_NOTES_SCREENED.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    w = sorted(v["words_long"] for v in res.values())
    print("screened", len(res), "filler", sum(v["n_filler"] for v in res.values()),
          "dropped", sum(v["n_dropped"] for v in res.values()),
          "long words median", w[len(w) // 2], "range", w[0], w[-1])


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("subset")
    s.set_defaults(fn=cmd_subset)
    g = sub.add_parser("zs-groq")
    g.add_argument("--model", required=True)
    g.add_argument("--name", required=True)
    g.add_argument("--split", default="test")
    g.add_argument("--notes", default="short", choices=["short", "long"])
    g.add_argument("--reps", type=int, default=1)
    g.add_argument("--nocache", action="store_true")
    g.add_argument("--workers", type=int, default=6)
    g.set_defaults(fn=cmd_zs_groq)
    lo = sub.add_parser("zs-local")
    lo.add_argument("--model", required=True)
    lo.add_argument("--name", required=True)
    lo.add_argument("--split", default="test")
    lo.add_argument("--notes", default="short", choices=["short", "long"])
    lo.add_argument("--pairs", default="")
    lo.add_argument("--think", default="")
    lo.add_argument("--json", action="store_true")
    lo.add_argument("--max-tokens", type=int, default=300)
    lo.add_argument("--num-ctx", type=int, default=8192)
    lo.add_argument("--timeout", type=int, default=3600)
    lo.add_argument("--stop-on-error", action="store_true")
    lo.add_argument("--nocache", action="store_true", help="fresh inference (repeat runs); cache untouched")
    lo.add_argument("--rep", type=int, default=0)
    lo.set_defaults(fn=cmd_zs_local)
    r = sub.add_parser("render-long")
    r.set_defaults(fn=cmd_render_long)
    sc = sub.add_parser("screen-long")
    sc.set_defaults(fn=cmd_screen_long)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
