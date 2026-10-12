"""Scan labelled JSONL traces through the real guard and gate decision functions."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from . import VERSIONS, gate_decision, run_all
from ..trace import submission_from_dict, trace_from_dict


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("corpus", type=Path)
    parser.add_argument("--guard-version", choices=VERSIONS, default="v0")
    args = parser.parse_args()
    rows = [json.loads(line) for line in args.corpus.read_text().splitlines() if line.strip()]
    if not rows:
        parser.error("empty corpus")
    for row in rows:
        findings = run_all(trace_from_dict(row["trace"]), submission_from_dict(row["submission"]),
                           requires_citation=row["requires_citation"], guard_version=args.guard_version)
        print(json.dumps({"id": row["id"], "guard_version": args.guard_version,
                          "findings": [asdict(f) for f in findings],
                          "decision": asdict(gate_decision(findings, 0))}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
