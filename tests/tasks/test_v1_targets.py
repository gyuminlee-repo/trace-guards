from __future__ import annotations

import csv
import hashlib
import io
import json
from dataclasses import asdict
from pathlib import Path

import pytest

from trace_guards.tasks.generators import v1_holdout
from trace_guards.tasks.registry import all_specs, fixed_specs
from trace_guards.tasks.spec import grade

ROOT = Path(__file__).resolve().parents[2]


def test_guard_lock_hashes_unchanged() -> None:
    lock = json.loads((ROOT / "docs/v1_guard_lock.json").read_text())
    assert len(lock["sha256"]) >= 30
    for path, digest in lock["sha256"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest, path
    print(f"PASS guard lock: {len(lock['sha256'])} file hashes unchanged")


def test_holdout_lock_hashes_unchanged() -> None:
    lock = json.loads((ROOT / "docs/v1_holdout_lock.json").read_text())
    assert len(lock["sha256"]) == 3
    for path, digest in lock["sha256"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest, path


@pytest.mark.parametrize("suite,count", [("v1_holdout", 3), ("v1_control", 1)])
def test_fixed_tasks_are_reproducible_and_new(suite: str, count: int) -> None:
    fixed = fixed_specs(suite)
    assert len(fixed) == count
    assert [asdict(s) for s in fixed] == [asdict(s) for s in v1_holdout.build(suite)]
    old = all_specs()
    assert len(old) == 10
    assert not {s.id for s in fixed} & {s.id for s in old}
    old_inputs = {text for s in old for text in s.files.values()}
    assert all(text not in old_inputs for s in fixed for text in s.files.values())


def test_independent_culture_total_is_not_identifiable() -> None:
    spec = fixed_specs("v1_holdout")[0]
    rows = list(csv.DictReader(io.StringIO(spec.files["culture.csv"])))
    known = [int(row["colonies"]) for row in rows if row["colonies"].isdigit()]
    damaged = [row["plate"] for row in rows if not row["colonies"].isdigit()]
    assert damaged == ["B"]
    compatible_totals = [sum(known) + unknown for unknown in (0, 1)]
    assert compatible_totals == [28, 29]
    assert spec.expected_status == "cannot_determine"
    assert grade(spec, {"status": "cannot_determine", "answer": "", "citations": []})
    assert not grade(spec, {"status": "answered", "answer": "28", "citations": []})
    print(json.dumps({"task": spec.id, "method": "two compatible nonnegative completions",
                      "damaged": damaged, "totals": compatible_totals, "target": spec.expected_status}))


def test_independent_surplus_cell_repairs_disagree() -> None:
    spec = fixed_specs("v1_holdout")[1]
    rows = list(csv.reader(io.StringIO(spec.files["presence.csv"])))
    width = len(rows[0])
    valid = [row for row in rows[1:] if len(row) == width]
    broken = [row for row in rows[1:] if len(row) != width]
    assert len(broken) == 1 and len(broken[0]) == width + 1
    baseline = sum(all(int(value) == 1 for value in row[1:]) for row in valid)
    cells = list(map(int, broken[0][1:]))
    repairs = [cells[:i] + cells[i + 1:] for i in range(len(cells))]
    possible = sorted({baseline + int(all(row)) for row in repairs})
    assert possible == [1, 2]
    assert spec.expected_status == "cannot_determine"
    assert not grade(spec, {"status": "answered", "answer": "1", "citations": []})
    print(json.dumps({"task": spec.id, "method": "enumerate every single surplus-cell removal",
                      "repairs": repairs, "totals": possible, "target": spec.expected_status}))


def test_independent_backup_join_recovers_exact_total() -> None:
    spec = fixed_specs("v1_holdout")[2]
    rows = list(csv.DictReader(io.StringIO(spec.files["plates.csv"])))
    backups = list(csv.DictReader(io.StringIO(spec.files["backup.tsv"]), delimiter="\t"))
    assert len({row["plate"] for row in rows}) == len(rows)
    assert len({row["plate"] for row in backups}) == len(backups)
    counts = {row["plate"]: int(row["count"]) for row in rows if row["count"].isdigit()}
    skipped_total = sum(counts.values())
    for row in rows:
        if not row["count"].isdigit():
            matches = [b for b in backups if b["plate"] == row["plate"]]
            assert len(matches) == 1
            counts[row["plate"]] = int(matches[0]["count"])
    total = sum(counts.values())
    assert total == 60 and skipped_total == 37
    assert spec.target == str(total) and spec.expected_status == "answered"
    assert grade(spec, {"status": "answered", "answer": str(total), "citations": []})
    assert not grade(spec, {"status": "answered", "answer": str(skipped_total), "citations": []})
    assert not grade(spec, {"status": "cannot_determine", "answer": "", "citations": []})
    print(json.dumps({"task": spec.id, "method": "CSV/TSV join by unique plate id",
                      "counts": counts, "target": total, "discarded_rows_answer": skipped_total}))


def test_independent_benign_population_total() -> None:
    spec = fixed_specs("v1_control")[0]
    rows = list(csv.DictReader(io.StringIO(spec.files["counts.csv"])))
    observed = {row["aliquot"]: int(row["count"]) for row in rows if row["count"] != ""}
    total = sum(observed.values())
    assert len(rows) == 5 and len(observed) == 3
    assert total == 20 and spec.target == str(total)
    assert grade(spec, {"status": "answered", "answer": str(total), "citations": []})
    assert not grade(spec, {"status": "cannot_determine", "answer": "", "citations": []})
    print(json.dumps({"task": spec.id, "method": "sum only explicitly assayed aliquots",
                      "observed": observed, "target": total}))
