from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from trace_guards.guards import run_all
from trace_guards.trace import Submission, Trace

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "tests/corpus/g5_silent_discard.jsonl"


@pytest.mark.parametrize("version", ["v0", "v1"])
def test_cli_matches_preregistered_labels(version: str) -> None:
    # Given
    rows = [json.loads(line) for line in CORPUS.read_text().splitlines()]
    command = [sys.executable, "-m", "trace_guards.guards", str(CORPUS), "--guard-version", version]
    # When
    done = subprocess.run(command, capture_output=True, text=True, check=True, cwd=ROOT)
    # Then
    output = [json.loads(line) for line in done.stdout.splitlines()]
    assert len(output) == len(rows) == 19
    for expected, actual in zip(rows, output, strict=True):
        fired = any(f["guard"] == "silent_discard" for f in actual["findings"])
        assert fired == (version == "v1" and expected["label"] == "fire"), expected["id"]
        if fired:
            assert actual["decision"]["accept"] is False
    print("COMMAND", command)
    print(done.stdout)


def test_unknown_version_fails() -> None:
    # Given
    trace = Trace("t", "p", ())
    # When / Then
    with pytest.raises(ValueError):
        run_all(trace, Submission("cannot_determine", ""), guard_version="v2")
