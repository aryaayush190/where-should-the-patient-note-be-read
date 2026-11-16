"""Privacy-gateway regression suite (round-5 review, 2026-11-10; exploratory, post-freeze).

Feeds the FROZEN runtime guard (splitmatch.llm.guard, unchanged) with prohibited and permitted payloads built
from the 45 test notes and from the real cloud payloads of the laptop run, and reports, per category, how
often the guard blocks. Prohibited payloads should be blocked; permitted payloads should pass.

    python experiments/gateway_suite.py   ->  results/review/GATEWAY_SUITE.json / .md

The guard blocks (a) any registered note sentence (>= 25 characters after lower-casing and whitespace
normalisation, not occurring in public criteria text) contained in the payload and (b) patient / pair
identifiers. The suite deliberately includes transformations it is NOT designed to catch, so that its
limits are measured and reported rather than assumed.
"""
import base64
import json
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from splitmatch import data, llm, paths  # noqa: E402
from splitmatch.llm import Channel, PrivacyViolation  # noqa: E402

SEED = 20261110
OUT = paths.RESULTS / "review"
SENT_SPLIT = re.compile(r"(?<=[.;:!?])\s+")


def blocked(payload: str) -> bool:
    try:
        llm.guard(Channel.CLOUD_FACT, payload)
        return False
    except PrivacyViolation:
        return True


def main():
    rng = random.Random(SEED)
    pairs = data.load_pairs("test")
    notes = {r.patient_id: r.note for r in pairs.itertuples()}
    for n in notes.values():
        llm.REGISTRY.register(n)
    pub = llm.REGISTRY._public()

    # note sentences and how many of them the registry protects at all
    sents, short_or_public = [], []
    for pid, n in notes.items():
        for s in SENT_SPLIT.split(n):
            norm = re.sub(r"\s+", " ", s.lower()).strip()
            if not norm:
                continue
            if len(norm) >= 25 and norm not in pub:
                sents.append((pid, s.strip()))
            else:
                short_or_public.append(s.strip())
    crit = [r.inclusion.splitlines()[0][:200] for r in pairs.drop_duplicates("trial_id").itertuples()]

    cases = defaultdict(list)
    for pid, s in sents:
        w = s.split()
        c = rng.choice(crit)
        cases["P1 exact note sentence"].append(s)
        cases["P2 case and spacing changed"].append("  ".join(s.upper().split()))
        cases["P3 sentence embedded in a criterion query"].append(f"Criterion: {c}\nContext: {s}\nAnswer yes/no.")
        cases["P4 patient identifier"].append(f"Fact for {pid}: value recorded.")
        cases["P5 pair identifier"].append(f"Pair {pid}__NCT00000000 requires review.")
        if len(w) >= 6:
            cases["P6 first half of a sentence"].append(" ".join(w[:len(w) // 2]))
            k = rng.randrange(len(w))
            cases["P7 one word deleted"].append(" ".join(w[:k] + w[k + 1:]))
        cases["P8 punctuation removed"].append(re.sub(r"[^\w\s]", "", s))
        cases["P9 base64-encoded sentence"].append(base64.b64encode(s.encode()).decode())

    # permitted: the real cloud payloads of the laptop run and the public compiler/judge calls
    seen = set()
    with open(paths.LLM_LOG, encoding="utf-8") as f:
        for line in f:
            try:
                r = json.loads(line)
            except Exception:
                continue
            ch, run = r.get("channel"), r.get("run_id", "")
            pl = r.get("payload")
            if not pl or pl in seen:
                continue
            if ch == "cloud_fact" and run == "run:TEST_deploy":
                seen.add(pl)
                cases["A1 real fact queries (laptop run)"].append(pl)
            elif ch == "cloud_public" and len(cases["A2 real public-criteria calls"]) < 2000:
                seen.add(pl)
                cases["A2 real public-criteria calls"].append(pl)

    res = {}
    for name, pls in sorted(cases.items()):
        b = sum(blocked(p) for p in pls)
        res[name] = {"n": len(pls), "blocked": b, "block_rate": round(b / len(pls), 4) if pls else None,
                     "expected": "allow" if name.startswith("A") else "block"}
    lens = Counter("lt25" if len(re.sub(r"\s+", " ", s).strip()) < 25 else "public" for s in short_or_public)

    # partial-leakage audit of the REAL traffic: longest run of consecutive note words (not occurring in public
    # criteria text) found in each real fact query, against the note of the patient that query belongs to
    def toks(t):
        return re.findall(r"[a-z0-9.%/-]+", t.lower())

    pub_toks = " " + " ".join(toks(pub)) + " "
    ref_pid = {}
    with open(paths.LLM_LOG, encoding="utf-8") as f:
        for line in f:
            try:
                r = json.loads(line)
            except Exception:
                continue
            if r.get("channel") == "cloud_fact" and r.get("run_id") == "run:TEST_deploy" and r.get("payload"):
                ref_pid.setdefault(r["payload"], str(r.get("local_ref", "")).split("__")[0])
    longest = []
    for pl, pid in ref_pid.items():
        nt, pt = toks(notes.get(pid, "")), " " + " ".join(toks(pl)) + " "
        best = 0
        for i in range(len(nt)):
            for j in range(i + best + 1, min(len(nt), i + 40) + 1):
                g = " " + " ".join(nt[i:j]) + " "
                if g in pt and g not in pub_toks:
                    best = j - i
                elif g not in pt:
                    break
        longest.append(best)
    ln = Counter(longest)
    out = {
        "note": "Exploratory regression test of the frozen guard (splitmatch.llm.guard); post-freeze, not pre-specified.",
        "notes": len(notes), "registered_sentences": len(sents),
        "unprotected_note_sentences": {"shorter_than_25_chars": lens.get("lt25", 0),
                                       "also_in_public_criteria": lens.get("public", 0),
                                       "examples_short": short_or_public[:8]},
        "cases": res,
        "real_traffic_partial_overlap": {
            "fact_queries": len(longest),
            "max_consecutive_note_words_not_in_criteria": max(longest) if longest else None,
            "queries_with_ge_5_words": sum(x >= 5 for x in longest),
            "queries_with_ge_8_words": sum(x >= 8 for x in longest),
            "histogram": dict(sorted(ln.items())),
        },
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "GATEWAY_SUITE.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    md = ["# Privacy-gateway regression suite", "", "| Case | Expected | n | Blocked | Rate |", "|---|---|---|---|---|"]
    for k, v in res.items():
        md.append(f"| {k} | {v['expected']} | {v['n']} | {v['blocked']} | {v['block_rate']:.1%} |")
    md += ["", f"Registered note sentences: {len(sents)}; note sentences not protected because they are shorter "
               f"than 25 characters: {lens.get('lt25', 0)}; because they also occur in public criteria: "
               f"{lens.get('public', 0)}."]
    (OUT / "GATEWAY_SUITE.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
