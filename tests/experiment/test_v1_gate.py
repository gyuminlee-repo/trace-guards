from __future__ import annotations

import os
from pathlib import Path

import pytest
from inspect_ai import eval

from trace_guards import inspect_adapter as ia
from trace_guards.experiment import aggregate, build, run
from trace_guards.tasks import registry
from trace_guards.tasks.spec import TaskSpec

RISKY = "import pandas as pd\nx=pd.to_numeric(pd.Series(['7','bad']), errors='coerce').dropna()\nprint(int(x.sum()))"
CLEAN = "print(sum([3,4]))"
SKIP = "import pandas as pd, io\nx=pd.read_csv(io.StringIO('x,y\\n3,a\\n99,b,extra\\n4,c\\n'), on_bad_lines='skip')\nprint(int(x.x.sum()))"


@pytest.mark.parametrize("case,version,condition,code,repeats,status,accepted", [
    ("coerce_rejected", "v1", "gate_on", RISKY, 1, "answered", [False, True]),
    ("skip_rejected", "v1", "gate_on", SKIP, 1, "answered", [False, True]),
    ("strict_accepted", "v1", "gate_on", CLEAN, 1, "answered", [True]),
    ("abstain_accepted", "v1", "gate_on", RISKY, 1, "cannot_determine", [True]),
    ("budget_exhausted", "v1", "gate_on", RISKY, 3, "answered", [False, False, True]),
    ("v0_preserved", "v0", "gate_on", RISKY, 1, "answered", [True]),
    ("off_scanned", "v1", "gate_off", RISKY, 1, "answered", [True]),
])
def test_scripted_runner_gate_and_scanner(case, version, condition, code, repeats, status, accepted,
                                         scripted_model, tmp_path) -> None:
    # Given
    spec = TaskSpec("g5_dev", "expression", "ordinary", None, "Report the total.",
                    {"input.txt": "development fixture"}, "answered", "7", 0.0, False, ("python",))
    answer = ("submit", {"status": status, "answer": "" if status == "cannot_determine" else "7"})
    calls = [("python", {"code": code})] + [answer] * repeats
    if accepted == [False, True]:
        calls.append(("submit", {"status": "cannot_determine", "answer": ""}))
    log_dir = Path(os.environ.get("TG_QA_DIR", str(tmp_path))) / case
    # When
    (log,) = eval(build.build_task(spec, condition, guard_version=version),
                  model=scripted_model(calls), log_dir=str(log_dir), log_format="json", display="none")
    # Then
    assert log.status == "success"
    sample = log.samples[0]
    assert sample.error is None
    assert sample.store[ia.EVENTS_KEY][0]["error"] is False
    records = ia.submissions_in(sample.store)
    assert [r["accepted"] for r in records] == accepted
    assert records[-1]["gate_exhausted"] == (case == "budget_exhausted")
    for index, record in enumerate(records):
        scanned = ia.scan_sample(sample, index)
        names = [f.guard for f in scanned]
        assert ("silent_discard" in names) == (
            version == "v1" and code != CLEAN and record["submission"]["status"] != "cannot_determine")
        assert aggregate._guards_at(sample.store, spec.id, index) == ";".join(dict.fromkeys(names))
        if condition == "gate_on":
            assert names == [f["guard"] for f in record["findings"]]
    print(f"PASS {case}: accepted={accepted}, log={log.location}")


def test_fixed_suite_loader_validates_seed_and_duplicates(monkeypatch, tmp_path) -> None:
    import json
    from dataclasses import asdict

    spec = TaskSpec("fixture", "expression", "ordinary", None, "Count.", {},
                    "answered", "7", 0.0, False, ("python",))
    monkeypatch.setattr(registry, "V1_TASK_DIR", tmp_path)
    (tmp_path / "v1_holdout.json").write_text(json.dumps([asdict(spec)]))
    assert run.select_specs("v1_holdout", 0) == [spec]
    with pytest.raises(ValueError):
        run.select_specs("v1_holdout", 1)
    (tmp_path / "v1_holdout.json").write_text(json.dumps([asdict(spec)] * 2))
    with pytest.raises(ValueError):
        run.select_specs("v1_holdout", 0)


def test_plan_only_never_contacts_model(monkeypatch, capsys) -> None:
    import json

    monkeypatch.setattr(run, "git_state", lambda: ("a" * 40, True))
    monkeypatch.setattr(run, "context_length", lambda model: pytest.fail("network forbidden"))
    monkeypatch.setattr(run, "eval", lambda *args, **kwargs: pytest.fail("inference forbidden"))
    assert run.main(["--tasks", "dev", "--epochs", "5", "--guard-version", "v1", "--plan-only"]) == 0
    plan = json.loads(capsys.readouterr().out)
    assert plan["runs"] == 30
    assert plan["guard_version"] == "v1"
