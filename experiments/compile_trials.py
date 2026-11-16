"""Compile trial sets into TrialPrograms (cloud tier, public text only).

    python experiments/compile_trials.py development expansion
    python experiments/compile_trials.py test            # ONLY after the freeze tag

Outputs results/programs/<set>/<NCT>.json and results/programs/<set>_summary.json.
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from splitmatch import data, paths  # noqa: E402
from splitmatch.compiler import compile_trial  # noqa: E402
from splitmatch.schema import AtomType  # noqa: E402


def main(sets):
    for which in sets:
        out = paths.RESULTS / "programs" / which
        out.mkdir(parents=True, exist_ok=True)
        summary = []

        def one(item):
            tid, trial = item
            t0 = time.time()
            return tid, compile_trial(trial, run_id=f"compile-{which}"), t0

        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(4) as ex:
            results = list(ex.map(one, data.trials(which).items()))
        for tid, prog, t0 in results:
            (out / f"{tid}.json").write_text(prog.model_dump_json(indent=1), encoding="utf-8")
            m = prog.compiler_meta
            types = {}
            for a in prog.atoms:
                types[a.type.value] = types.get(a.type.value, 0) + 1
            row = {"trial_id": tid, "lines": m["lines"], "atoms": len(prog.atoms),
                   "typed_atoms": m["typed_atoms"], "typed_atoms_agree": m["typed_atoms_agree"],
                   "downgraded": m["downgraded_atoms"], "types": types,
                   "chunk_failures": m["primary"]["chunk_failures"] + m["secondary"]["chunk_failures"],
                   "secs": round(time.time() - t0, 1)}
            summary.append(row)
            print(json.dumps(row), flush=True)
        tot = {k: sum(r[k] for r in summary) for k in ("lines", "atoms", "typed_atoms",
                                                       "typed_atoms_agree", "downgraded")}
        tot["agreement_rate"] = round(tot["typed_atoms_agree"] / max(tot["typed_atoms"], 1), 3)
        (paths.RESULTS / "programs" / f"{which}_summary.json").write_text(
            json.dumps({"total": tot, "trials": summary}, indent=1), encoding="utf-8")
        print(which, "TOTAL", tot, flush=True)


if __name__ == "__main__":
    main(sys.argv[1:] or ["development", "expansion"])
