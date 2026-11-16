"""Where do SPLIT-Match's extra missed patients come from when the cloud judge (L2) is on? (round-6 review, exploratory)

Compares, on the 69 eligible test pairs, the proxy run with L2 (TEST_proxy) against the same run without L2
(AB_noL2, which reuses TEST_proxy's fact sheets), and the laptop run (TEST_deploy). For every eligible pair that
is excluded in forced mode, the trace names the route that excluded it:
  exclude:program / exclude:program+l1 ...   two keys on the laptop (no cloud judge)
  exclude:program+l2 / exclude:l1+l2          two keys, one of them the cloud judge
  forced:exclude(l2-ask)                       forced mode: cloud judge alone, on "not stated in the note"
  forced:exclude(l2)                           forced mode: cloud judge alone, on a deferred criterion

    python experiments/l2_attribution.py  ->  results/review/L2_ATTRIBUTION.json
"""
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from splitmatch import paths  # noqa: E402

RUNS = paths.RESULTS / "runs"


def load(run):
    out = {}
    for f in (RUNS / run / "pairs").glob("*.json"):
        d = json.loads(f.read_text(encoding="utf-8"))
        out[d["pair_id"]] = d
    return out


def route_of(d):
    """The route that produced the forced exclusion (first excluding trace entry)."""
    for t in d.get("trace", []):
        r = t.get("route", "")
        if r.startswith("exclude") or r.startswith("forced:exclude"):
            return r
    return "none"


def group(r):
    if r.startswith("forced:exclude(l2"):
        return "cloud judge alone (forced mode)"
    if "l2" in r:
        return "two keys incl. cloud judge"
    if r.startswith("exclude"):
        return "two keys on the laptop"
    return "other"


def main():
    res = {}
    proxy, nol2, deploy = load("TEST_proxy"), load("AB_noL2"), load("TEST_deploy")
    for name, run in (("TEST_proxy", proxy), ("AB_noL2", nol2), ("TEST_deploy", deploy)):
        pos = [d for d in run.values() if d["label"] == 1]
        missed = [d for d in pos if d["forced"] == "NOT_ELIGIBLE"]
        res[name] = {"eligible": len(pos), "missed": len(missed),
                     "by_route": dict(Counter(group(route_of(d)) for d in missed)),
                     "by_route_detail": dict(Counter(route_of(d) for d in missed))}
    # pairs missed with L2 but referred without it (same fact sheets)
    extra = [pid for pid, d in proxy.items()
             if d["label"] == 1 and d["forced"] == "NOT_ELIGIBLE" and nol2.get(pid, {}).get("forced") == "ELIGIBLE"]
    res["extra_misses_with_l2"] = {"n": len(extra),
                                   "by_route": dict(Counter(group(route_of(proxy[p])) for p in extra)),
                                   "by_route_detail": dict(Counter(route_of(proxy[p]) for p in extra)),
                                   "selective_without_l2": dict(Counter(nol2[p]["selective"] for p in extra))}
    out = paths.RESULTS / "review" / "L2_ATTRIBUTION.json"
    out.write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
