"""Task construction: identical prompts and tools across conditions, task split, scoring."""

from __future__ import annotations

import json

import pytest
from inspect_ai import eval
from inspect_ai.tool import ToolDef

from trace_guards import inspect_adapter as ia
from trace_guards.experiment import aggregate, build, run
from trace_guards.tasks.registry import all_specs
from trace_guards.tasks.spec import TOOL_NAMES


def spec_by_id(task_id: str):
    return {s.id: s for s in all_specs(0)}[task_id]


def test_dev_and_holdout_partition_the_ten_tasks() -> None:
    ids = [s.id for s in all_specs(0)]
    dev, holdout = set(run.DEV_TASKS), set(run.holdout_tasks(0))
    assert len(ids) == 10 and len(set(ids)) == 10
    assert len(run.DEV_TASKS) == 3 and len(holdout) == 7
    assert dev.isdisjoint(holdout)
    assert dev | holdout == set(ids)
    assert [s.id for s in run.select_specs("dev", 0)] == list(run.DEV_TASKS)
    assert {s.id for s in run.select_specs("holdout", 0)} == holdout
    assert [s.id for s in run.select_specs("all", 0)] == ids
    assert [s.id for s in run.select_specs("seq_gc,trap_alias", 0)] == ["seq_gc", "trap_alias"]
    with pytest.raises(ValueError):
        run.select_specs("seq_gc,no_such_task", 0)
    with pytest.raises(ValueError):
        run.select_specs(",", 0)


def test_every_spec_tool_has_a_factory() -> None:
    assert set(build.TOOL_FACTORIES) == set(TOOL_NAMES)
    for spec in all_specs(0):
        assert [ToolDef(t).name for t in build.tools_for(spec)] == list(spec.tools)


def test_submit_tool_is_declared_identically_in_both_conditions() -> None:
    off = ia.agent_submit(False, build.MAX_REJECTIONS)
    on = ia.agent_submit(True, build.MAX_REJECTIONS)
    assert off._replace(tool=None) == on._replace(tool=None)
    assert off.name == "submit"
    d_off, d_on = ToolDef(off.tool), ToolDef(on.tool)
    assert d_off.description == d_on.description
    assert d_off.parameters.model_dump() == d_on.parameters.model_dump()


def test_build_task_rejects_unknown_condition() -> None:
    with pytest.raises(ValueError):
        build.build_task(spec_by_id("seq_gc"), "gate_maybe")


@pytest.mark.parametrize("task_id", run.DEV_TASKS)
def test_model_sees_the_same_prompt_and_tools_in_both_conditions(
    task_id, scripted_model, tmp_path
) -> None:
    """Run each condition with a scripted model and compare what the model was sent."""
    spec = spec_by_id(task_id)
    first_call = {}
    for condition in build.CONDITIONS:
        seen: list = []
        model = scripted_model([("submit", {"status": "cannot_determine", "answer": ""})], seen)
        (log,) = eval(
            build.build_task(spec, condition),
            model=model,
            log_dir=str(tmp_path / condition),
            log_format="json",
            display="none",
        )
        assert log.status == "success"
        assert len(seen) == 1
        first_call[condition] = seen[0]

    off, on = first_call["gate_off"], first_call["gate_on"]
    assert off["messages"] == on["messages"]
    assert json.dumps(off["tools"], sort_keys=True) == json.dumps(on["tools"], sort_keys=True)
    roles = [role for role, _ in off["messages"]]
    assert roles == ["system", "user"]
    assert off["messages"][1][1] == spec.prompt
    assert [t["name"] for t in off["tools"]] == [*spec.tools, "submit"]


def test_scorer_and_aggregate_on_scripted_runs(scripted_model, tmp_path) -> None:
    """End to end without a model: correct run, gated guess, run with no submission."""
    spec = spec_by_id("seq_gc")
    value = spec.target
    compute = ("python", {"code": f"print('{value}')"})
    answer = ("submit", {"status": "answered", "answer": value})
    scripts = {
        # condition -> tool calls of the single run
        "gate_off": [answer],  # right value, never computed: accepted, unsupported
        "gate_on": [answer, compute, answer],  # rejected once, then supported
    }
    logs_dir = tmp_path / run.LOG_DIR
    for condition, calls in scripts.items():
        (log,) = eval(
            build.build_task(spec, condition),
            model=scripted_model(calls),
            log_dir=str(logs_dir),
            log_format="json",
            display="none",
        )
        assert log.status == "success"
        sample = log.samples[0]
        assert sample.scores[build.SCORER_NAME].value == "C"
        assert sample.scores[build.SCORER_NAME].metadata == {"accepted_submission_present": True}

    meta = {
        "commit": "0" * 40, "worktree_clean": True, "models": ["mockllm/model"],
        "context_length": {"mockllm/model": 100},
        "conditions": list(build.CONDITIONS), "temperature": build.TEMPERATURE,
        "message_limit": build.MESSAGE_LIMIT, "max_rejections": build.MAX_REJECTIONS,
        "epochs": 1, "seed": 0, "task_ids": [spec.id], "inspect_ai_version": "x",
        "started_utc": "2026-01-01T00:00:00+00:00",
    }  # fmt: skip
    (tmp_path / run.META_FILE).write_text(json.dumps(meta), encoding="utf-8")
    assert aggregate.main([str(tmp_path)]) == 0

    lines = (tmp_path / "runs.csv").read_text(encoding="utf-8").splitlines()
    assert lines[0].split(",") == list(aggregate.RUN_COLUMNS)
    rows = {r["condition"]: r for r in map(lambda l: dict(zip(aggregate.RUN_COLUMNS, l.split(","))), lines[1:])}
    assert set(rows) == {"gate_off", "gate_on"}
    off, on = rows["gate_off"], rows["gate_on"]
    assert (off["correct"], off["n_submit_calls"], off["n_rejections"]) == ("1", "1", "0")
    assert off["first_findings"] == off["final_findings"] == "value_evidence"
    assert (on["correct"], on["n_submit_calls"], on["n_rejections"]) == ("1", "2", "1")
    assert (on["first_findings"], on["final_findings"]) == ("value_evidence", "")
    assert (on["n_tool_events"], off["n_tool_events"]) == ("1", "0")
    # Three scripted model calls of 3 + 2 tokens each in the gated run, one in the other.
    assert (on["input_tokens"], on["output_tokens"], on["total_tokens"]) == ("9", "6", "15")
    assert off["total_tokens"] == "5"
    # Every scripted call reports a prompt of 3 tokens; 3 is below 90 of 100.
    assert (on["max_prompt_tokens"], on["context_risk"]) == ("3", "0")

    # Without a context length for the model the aggregation refuses.
    for broken in ({}, {"context_length": {}}, {"context_length": {"mockllm/model": None}}):
        stripped = {k: v for k, v in meta.items() if k != "context_length"} | broken
        (tmp_path / run.META_FILE).write_text(json.dumps(stripped), encoding="utf-8")
        assert aggregate.main([str(tmp_path)]) == 1
    text = (tmp_path / "summary.md").read_text(encoding="utf-8")
    assert "preliminary" in text.splitlines()[0]
    assert aggregate.TOO_FEW_TASKS in text


def test_scorer_marks_a_run_without_accepted_submission_incorrect(scripted_model, tmp_path) -> None:
    spec = spec_by_id("seq_gc")
    guess = ("submit", {"status": "answered", "answer": "0.123"})
    task = build.build_task(spec, "gate_on")
    task.message_limit = 4  # system, user, one call, one rejection
    (log,) = eval(
        task,
        model=scripted_model([guess, guess, guess]),
        log_dir=str(tmp_path),
        log_format="json",
        display="none",
    )
    sample = log.samples[0]
    score = sample.scores[build.SCORER_NAME]
    assert score.value == "I"
    assert score.metadata == {"accepted_submission_present": False}
    assert "no accepted submission" in score.explanation
    (row,) = aggregate.rows_from_log(log, context_length=100)
    assert row["accepted_submission_present"] == 0
    assert (row["correct"], row["confident_wrong"], row["abstained"]) == (0, 0, 0)
    assert row["error"] == "limit:message"
    assert row["n_rejections"] == row["n_submit_calls"] >= 1


def test_context_length_lookup_and_url(monkeypatch) -> None:
    def server(ps_models, parameters):
        def fetch(path, body=None):
            if path == "/api/ps":
                return {"models": ps_models}
            assert (path, body) == ("/api/show", {"model": "tg-x"})
            return {"parameters": parameters}

        return fetch

    loaded = [{"name": "tg-x:latest", "context_length": 16384}, {"name": "other", "context_length": 4096}]
    # A loaded model reports the value in use, whatever its parameters say.
    assert run.context_length("ollama/tg-x", server(loaded, "num_ctx 8192")) == 16384
    # Not loaded: the num_ctx parameter. "num_ctx_extra" and "top_k" are not it.
    text = "top_k                64\nnum_ctx_extra 1\nnum_ctx              16384\ntemperature 1"
    assert run.context_length("ollama/tg-x", server(loaded[1:], text)) == 16384
    # Not loaded and no num_ctx: the server default applies and is not known.
    assert run.context_length("ollama/tg-x", server([], "top_k 64")) is None
    assert run.context_length("ollama/tg-x", server([], None)) is None
    # Not an Ollama model: no lookup at all.
    assert run.context_length("mockllm/model", lambda *a: pytest.fail("no call expected")) is None

    def down(path, body=None):
        raise OSError("connection refused")

    assert run.context_length("ollama/tg-x", down) is None

    monkeypatch.delenv(run.OLLAMA_URL_VARIABLE, raising=False)
    assert run.ollama_url() == "http://127.0.0.1:11434"
    monkeypatch.setenv(run.OLLAMA_URL_VARIABLE, "http://example.test:1234/v1/")
    assert run.ollama_url() == "http://example.test:1234"


def test_run_refuses_an_unknown_context_length(monkeypatch, tmp_path, capsys) -> None:
    monkeypatch.setattr(run, "git_state", lambda: ("0" * 40, True))
    monkeypatch.setattr(run, "context_length", lambda model: None)
    monkeypatch.setattr(run, "eval", lambda *a, **k: pytest.fail("eval must not start"))
    out = tmp_path / "out"
    code = run.main(["--tasks", "seq_gc", "--epochs", "1", "--models", "ollama/x", "--out", str(out)])
    assert code == 2
    assert "context length unknown" in capsys.readouterr().err
    assert not out.exists()


def test_run_writes_context_length_into_the_metadata(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(run, "git_state", lambda: ("0" * 40, True))
    monkeypatch.setattr(run, "context_length", lambda model: 16384)
    monkeypatch.setattr(run, "eval", lambda *a, **k: [])
    out = tmp_path / "out"
    assert run.main(["--tasks", "seq_gc", "--epochs", "1", "--models", "ollama/x", "--out", str(out)]) == 0
    meta = json.loads((out / run.META_FILE).read_text(encoding="utf-8"))
    assert meta["context_length"] == {"ollama/x": 16384}
    assert meta["task_ids"] == ["seq_gc"]
