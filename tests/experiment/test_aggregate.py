"""Aggregation on hand-made run records. No model, no Inspect run."""

from __future__ import annotations

import json
import math

import pytest

from trace_guards import inspect_adapter as ia
from trace_guards.experiment import aggregate, build, run
from trace_guards.tasks.spec import TaskSpec

PROMPT = "Report the requested value."


def spec(task_id: str, expected_status: str) -> TaskSpec:
    return TaskSpec(
        id=task_id, family="sequence", kind="ordinary", trap=None, prompt=PROMPT, files={},
        expected_status=expected_status, target="0.5" if expected_status == "answered" else "",
        tolerance=0.01, requires_citation=False, tools=("python",),
    )  # fmt: skip


NUMERIC = spec("t_num", "answered")
UNKNOWABLE = spec("t_unknown", "cannot_determine")


def python_event(printed: str) -> dict:
    return {"tool": "python", "arguments": {"code": "print(x)"}, "output": printed, "error": False}


def submit(status: str, answer: str, events_before: int, accepted: bool, exhausted: bool = False) -> dict:
    return {
        "submission": {"status": status, "answer": answer, "citations": [], "files": []},
        "event_count": events_before,
        "workdir_files": {},
        "accepted": accepted,
        "gate_exhausted": exhausted,
        "findings": [],
    }


def store(events: list[dict], submissions: list[dict]) -> dict:
    return {
        ia.PROMPT_KEY: PROMPT,
        ia.REQUIRES_CITATION_KEY: False,
        ia.EVENTS_KEY: events,
        ia.SUBMISSIONS_KEY: submissions,
    }


# name -> (condition, spec, store, expected measures of that run)
SCENARIOS = {
    "accepted_correct": (
        "gate_off", NUMERIC,
        store([python_event("0.5")], [submit("answered", "0.5", 1, True)]),
        dict(correct=1, confident_wrong=0, abstained=0, wrong_abstention=0, n_submit_calls=1,
             n_rejections=0, gate_exhausted=0, first_findings="", final_findings="",
             first_unsupported=0, accepted_submission_present=1, final_status="answered"),
    ),
    "confident_wrong": (  # the tool printed the wrong value, so the guards have no finding
        "gate_off", NUMERIC,
        store([python_event("0.7")], [submit("answered", "0.7", 1, True)]),
        dict(correct=0, confident_wrong=1, abstained=0, wrong_abstention=0, n_submit_calls=1,
             n_rejections=0, gate_exhausted=0, first_findings="", final_findings="",
             first_unsupported=0, accepted_submission_present=1, final_status="answered"),
    ),
    "confident_wrong_absent": (
        "gate_off", NUMERIC,
        store([], [submit("absent", "not there", 0, True)]),
        dict(correct=0, confident_wrong=1, abstained=0, wrong_abstention=0, n_submit_calls=1,
             n_rejections=0, gate_exhausted=0, first_findings="absence_control",
             final_findings="absence_control", first_unsupported=1,
             accepted_submission_present=1, final_status="absent"),
    ),
    "honest_abstention": (
        "gate_off", UNKNOWABLE,
        store([], [submit("cannot_determine", "", 0, True)]),
        dict(correct=1, confident_wrong=0, abstained=1, wrong_abstention=0, n_submit_calls=1,
             n_rejections=0, gate_exhausted=0, first_findings="", final_findings="",
             first_unsupported=0, accepted_submission_present=1, final_status="cannot_determine"),
    ),
    "wrong_abstention": (
        "gate_off", NUMERIC,
        store([], [submit("cannot_determine", "", 0, True)]),
        dict(correct=0, confident_wrong=0, abstained=1, wrong_abstention=1, n_submit_calls=1,
             n_rejections=0, gate_exhausted=0, first_findings="", final_findings="",
             first_unsupported=0, accepted_submission_present=1, final_status="cannot_determine"),
    ),
    "no_submission": (
        "gate_off", NUMERIC,
        store([python_event("0.5")], []),
        dict(correct=0, confident_wrong=0, abstained=0, wrong_abstention=0, n_submit_calls=0,
             n_rejections=0, gate_exhausted=0, first_findings="", final_findings="",
             first_unsupported="", accepted_submission_present=0, final_status=""),
    ),
    "rejected_then_correct": (
        "gate_on", NUMERIC,
        store(
            [python_event("0.5")],
            [submit("answered", "0.9", 0, False), submit("answered", "0.5", 1, True)],
        ),
        dict(correct=1, confident_wrong=0, abstained=0, wrong_abstention=0, n_submit_calls=2,
             n_rejections=1, gate_exhausted=0, first_findings="value_evidence",
             final_findings="", first_unsupported=1, accepted_submission_present=1,
             final_status="answered"),
    ),
    "gate_exhausted": (
        "gate_on", NUMERIC,
        store([], [
            submit("answered", "0.9", 0, False),
            submit("answered", "0.9", 0, False),
            submit("answered", "0.9", 0, True, exhausted=True),
        ]),
        dict(correct=0, confident_wrong=1, abstained=0, wrong_abstention=0, n_submit_calls=3,
             n_rejections=2, gate_exhausted=1, first_findings="value_evidence",
             final_findings="value_evidence", first_unsupported=1,
             accepted_submission_present=1, final_status="answered"),
    ),
    "rejected_until_limit": (  # a rejected submission is never graded
        "gate_on", NUMERIC,
        store([], [submit("answered", "0.5", 0, False)]),
        dict(correct=0, confident_wrong=0, abstained=0, wrong_abstention=0, n_submit_calls=1,
             n_rejections=1, gate_exhausted=0, first_findings="value_evidence",
             final_findings="", first_unsupported=1, accepted_submission_present=0,
             final_status=""),
    ),
}  # fmt: skip


def scenario_rows() -> list[dict]:
    rows = []
    for epoch, (name, (condition, task, data, _)) in enumerate(SCENARIOS.items(), start=1):
        correct, _ = build.grade_store(task, data)
        rows.append(
            aggregate.run_row(
                model="m", task_id=task.id, kind=task.kind, trap=task.trap, epoch=epoch,
                condition=condition, expected_status=task.expected_status, store=data,
                correct=correct, input_tokens=10 * epoch, output_tokens=epoch,
                total_tokens=11 * epoch, wall_seconds=float(epoch),
            )  # fmt: skip
        )
    return rows


@pytest.mark.parametrize("name", sorted(SCENARIOS))
def test_run_row_measures(name: str) -> None:
    expected = SCENARIOS[name][3]
    row = dict(zip(SCENARIOS, scenario_rows()))[name]
    assert set(row) == set(aggregate.RUN_COLUMNS)
    assert {k: row[k] for k in expected} == expected


def test_grading_a_correct_run_without_accepted_submission_is_an_error() -> None:
    _, task, data, _ = SCENARIOS["no_submission"]
    with pytest.raises(ValueError):
        aggregate.run_row(
            model="m", task_id=task.id, kind=task.kind, trap=None, epoch=1, condition="gate_off",
            expected_status="answered", store=data, correct=True,
        )  # fmt: skip


def test_condition_summary_counts_and_denominators() -> None:
    summary = aggregate.condition_summary(scenario_rows())
    got = {(s["condition"], s["metric"]): s for s in summary}

    def expected(condition: str, key: str, value=1, among=lambda e, t: True) -> tuple[int, int]:
        """Count scenarios by reading their expected measures (not the rows)."""
        members = [
            (e, t) for c, t, _, e in SCENARIOS.values() if c == condition and among(e, t)
        ]
        return sum(1 for e, _ in members if e[key] == value), len(members)

    for condition in ("gate_off", "gate_on"):
        n_runs = sum(1 for c, *_ in SCENARIOS.values() if c == condition)
        assert got[condition, "runs"]["count"] == n_runs
        checks = {
            "correct": expected(condition, "correct"),
            "confident_wrong": expected(condition, "confident_wrong"),
            "no_accepted_submission": expected(condition, "accepted_submission_present", 0),
            "abstained": expected(condition, "abstained"),
            "abstained_where_expected": expected(
                condition, "abstained",
                among=lambda e, t: t.expected_status == "cannot_determine",
            ),
            "wrong_abstention": expected(
                condition, "wrong_abstention",
                among=lambda e, t: t.expected_status != "cannot_determine",
            ),
            "first_unsupported": expected(
                condition, "first_unsupported", among=lambda e, t: e["n_submit_calls"] > 0
            ),
            "gate_exhausted": expected(condition, "gate_exhausted"),
        }  # fmt: skip
        for metric, (count, denominator) in checks.items():
            line = got[condition, metric]
            assert (line["count"], line["denominator"]) == (count, denominator), metric
            if denominator:
                assert line["rate"] == count / denominator
                assert 0.0 <= line["ci_low"] <= line["rate"] <= line["ci_high"] <= 1.0
            else:
                assert "rate" not in line and "ci_low" not in line

    # Spot values counted by hand from the scenario table above.
    assert (got["gate_off", "confident_wrong"]["count"], got["gate_off", "runs"]["count"]) == (2, 6)
    assert (got["gate_on", "confident_wrong"]["count"], got["gate_on", "runs"]["count"]) == (1, 3)
    assert got["gate_off", "abstained_where_expected"]["denominator"] == 1
    assert got["gate_on", "abstained_where_expected"]["denominator"] == 0
    assert got["gate_off", "first_unsupported"]["denominator"] == 5
    assert got["gate_on", "final_unsupported"]["count"] == 1
    assert got["gate_on", "final_unsupported"]["denominator"] == 2
    # gate_on scenarios are epochs 7, 8, 9: tokens 77, 88, 99; rejections 1, 2, 1.
    assert got["gate_on", "total_tokens"]["median"] == 88
    assert got["gate_on", "total_tokens"]["mean"] == 88
    assert got["gate_on", "n_rejections"]["mean"] == pytest.approx(4 / 3)
    assert got["gate_on", "n_rejections"]["median"] == 1
    assert got["gate_on", "wall_seconds"]["denominator"] == 3


# Wilson 95% intervals for n = 10 as printed in standard tables (z = 1.96).
WILSON_TABLE = {0: (0.0, 0.2775), 5: (0.2366, 0.7634), 10: (0.7225, 1.0)}


@pytest.mark.parametrize("count", sorted(WILSON_TABLE))
def test_wilson_matches_table_values(count: int) -> None:
    low, high = aggregate.wilson(count, 10)
    assert (low, high) == pytest.approx(WILSON_TABLE[count], abs=5e-4)


@pytest.mark.parametrize("count,n", [(0, 10), (1, 12), (5, 10), (7, 9), (10, 10), (3, 200)])
def test_wilson_bounds_solve_the_score_equation(count: int, n: int) -> None:
    """Each bound p satisfies (p_hat - p)^2 = z^2 p (1 - p) / n; checked by substitution."""
    z = 1.959964
    p_hat = count / n
    low, high = aggregate.wilson(count, n)
    assert low <= p_hat <= high
    for bound in (low, high):
        assert (p_hat - bound) ** 2 == pytest.approx(z * z * bound * (1 - bound) / n, abs=1e-7)
    # Closed forms at the edges.
    if count == 0:
        assert (low, high) == pytest.approx((0.0, z * z / (n + z * z)), abs=1e-6)
    if count == n:
        assert (low, high) == pytest.approx((n / (n + z * z), 1.0), abs=1e-6)


def test_wilson_rejects_an_empty_denominator() -> None:
    with pytest.raises(ValueError):
        aggregate.wilson(0, 0)
    with pytest.raises(ValueError):
        aggregate.wilson(3, 2)


def paired_rows(cells: dict[str, list[tuple[int, int]]]) -> list[dict]:
    """task -> per epoch (confident_wrong gate_off, confident_wrong gate_on)."""
    rows = []
    for task, epochs in cells.items():
        for epoch, (off, on) in enumerate(epochs, start=1):
            for condition, value in (("gate_off", off), ("gate_on", on)):
                rows.append({"model": "m", "task_id": task, "epoch": epoch,
                             "condition": condition, "confident_wrong": value})  # fmt: skip
    return rows


def test_paired_difference_and_task_bootstrap() -> None:
    cells = {
        "a": [(1, 0), (1, 0)], "b": [(1, 0), (0, 0)], "c": [(0, 0), (0, 0)],
        "d": [(0, 1), (0, 0)], "e": [(1, 1), (1, 0)], "f": [(0, 0), (1, 0)],
    }  # fmt: skip
    rows = paired_rows(cells)
    by_task = aggregate.paired_differences(rows)["m"]
    assert by_task == {"a": [-1, -1], "b": [-1, 0], "c": [0, 0], "d": [1, 0], "e": [0, -1], "f": [0, -1]}
    (line,) = aggregate.paired_summary(rows)
    assert (line["count"], line["denominator"]) == (-4, 12)
    assert line["rate"] == pytest.approx(-4 / 12)
    assert -1.0 <= line["ci_low"] < line["rate"] < line["ci_high"] <= 0.5
    # Seeded: the same input gives the same interval.
    assert aggregate.bootstrap_interval(by_task) == (line["ci_low"], line["ci_high"])
    # Task means are -1, -0.5, 0, 0.5, -0.5, -0.5; a resample mean cannot leave their range.
    assert line["ci_low"] >= -1.0 and line["ci_high"] <= 0.5
    # No variation between tasks: the interval collapses to the common value.
    same = {t: [-1, -1] for t in "abcde"}
    assert aggregate.bootstrap_interval(same) == (-1.0, -1.0)


def test_unpaired_runs_are_left_out_and_duplicates_raise() -> None:
    rows = paired_rows({"a": [(1, 0)]})
    rows.append({"model": "m", "task_id": "b", "epoch": 1, "condition": "gate_off", "confident_wrong": 1})
    assert aggregate.paired_differences(rows) == {"m": {"a": [-1]}}
    with pytest.raises(ValueError):
        aggregate.paired_differences(rows + rows[:1])


def test_no_interval_below_five_tasks() -> None:
    rows = paired_rows({t: [(1, 0)] for t in "abcd"})
    assert aggregate.bootstrap_interval(aggregate.paired_differences(rows)["m"]) is None
    (line,) = aggregate.paired_summary(rows)
    assert "ci_low" not in line and aggregate.TOO_FEW_TASKS in line["note"]
    assert math.isclose(line["rate"], -1.0)


def test_per_task_table_counts() -> None:
    cells = {(c["task_id"], c["condition"]): c for c in aggregate.per_task(scenario_rows())}
    assert set(cells) == {("t_num", "gate_off"), ("t_unknown", "gate_off"), ("t_num", "gate_on")}
    off = cells["t_num", "gate_off"]
    assert (off["runs"], off["correct"], off["confident_wrong"], off["no_accepted_submission"]) == (5, 1, 2, 1)
    on = cells["t_num", "gate_on"]
    assert (on["runs"], on["correct"], on["confident_wrong"], on["no_accepted_submission"]) == (3, 1, 1, 1)


META = {
    "commit": "0" * 40, "worktree_clean": True, "models": ["m"], "conditions": ["gate_off", "gate_on"],
    "temperature": 0.7, "message_limit": 30, "max_rejections": 2, "epochs": 9, "seed": 0,
    "task_ids": ["t_num", "t_unknown"], "inspect_ai_version": "x",
    "started_utc": "2026-01-01T00:00:00+00:00",
}  # fmt: skip


def test_summary_markdown_names_denominators_and_avoids_banned_text() -> None:
    rows = scenario_rows()
    summary = aggregate.condition_summary(rows) + aggregate.paired_summary(rows)
    text = aggregate.summary_markdown(META, rows, summary, n_logs=2)
    assert "preliminary" in text.splitlines()[0]
    assert "0" * 40 in text and "t_num, t_unknown" in text
    assert "| confident_wrong | 2 / 6 |" in text
    assert "| confident_wrong | 1 / 3 |" in text
    assert "| abstained_where_expected | 0 / 0 | n/a | n/a |" in text
    assert "No pair has both conditions." in text
    assert "—" not in text
    assert "results" not in text.lower()


def test_empty_folder_and_folder_without_logs_fail(tmp_path, capsys) -> None:
    assert aggregate.main([str(tmp_path)]) == 1
    (tmp_path / run.META_FILE).write_text(json.dumps(META), encoding="utf-8")
    assert aggregate.main([str(tmp_path)]) == 1
    (tmp_path / run.LOG_DIR).mkdir()
    assert aggregate.main([str(tmp_path)]) == 1
    assert "nothing written" in capsys.readouterr().err
    assert sorted(p.name for p in tmp_path.iterdir()) == [run.LOG_DIR, run.META_FILE]
