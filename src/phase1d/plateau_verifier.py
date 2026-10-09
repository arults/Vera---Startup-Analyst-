"""Retired snapshot-only research-plateau acceptance path (CP6 correction).

Historical implementation is preserved in Git at 122c869911d838a8ed77e71b893b8e0104a1dd95.
Use research_plateau_gate for evidence-backed scoped research decisions. This
compatibility comparison cannot authorize a research stop or overwrite snapshots.
"""
import re
from src.phase1d.research_plateau_gate import compare_states

THRESHOLD = 0.05


def compare_snapshots(previous: dict, current: dict, threshold: float = THRESHOLD) -> dict:
    result = compare_states(previous, current, threshold)
    result["plateau"] = False  # Fail closed for legacy callers.
    result["interpretation"] = "Replay comparison only; CP6 research receipts required."
    return result


def safe_round_id(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", value or ""):
        raise ValueError("invalid round id")
    return value


def main() -> None:
    raise SystemExit("RETIRED: use src.phase1d.research_plateau_gate; legacy snapshots are read-only.")


if __name__ == "__main__":
    main()
