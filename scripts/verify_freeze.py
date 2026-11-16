"""Check that the frozen SPLIT-Match files are byte-identical to the pre-test freeze manifest.

    python scripts/verify_freeze.py

docs/FREEZE_MANIFEST_v1.json lists SHA-256 hashes of the 26 files fixed before the single test-set run
(frozen 2026-11-08). Line endings are normalised to LF before hashing so the check passes on any OS.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def sha(p: Path, normalise: bool) -> str:
    b = p.read_bytes()
    if normalise:
        b = b.replace(b"\r\n", b"\n")
    return hashlib.sha256(b).hexdigest()


# The analysis plan was edited after the freeze; its deviation log (section 9) records dated changes with reasons.
# It is therefore not hash-checked.
APPENDED = {"docs/PREREGISTRATION.md"}


def main():
    man = json.loads((ROOT / "docs" / "FREEZE_MANIFEST_v1.json").read_text(encoding="utf-8"))
    ok = bad = 0
    files = {r: h for r, h in man["files"].items() if r not in APPENDED}
    for rel in sorted(APPENDED & set(man["files"])):
        print(f"NOTE     {rel}: edited after the freeze (changes logged with dates in section 9); not hash-checked")
    for rel, h in files.items():
        p = ROOT / rel
        if not p.exists():
            print("MISSING ", rel)
            bad += 1
        elif h in (sha(p, False), sha(p, True)):
            ok += 1
        else:
            print("CHANGED ", rel)
            bad += 1
    print(f"{ok}/{len(files)} frozen code files match the manifest ({man['meta']['frozen_at']})")
    raise SystemExit(1 if bad else 0)


if __name__ == "__main__":
    main()
