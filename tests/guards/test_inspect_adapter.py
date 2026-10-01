"""Unit tests that need no model: gate decision, tool output formats, trace building."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
# The package is not installed in the test environment.
sys.path.insert(0, str(ROOT / "src"))

from inspect_ai.tool import ToolError  # noqa: E402

from trace_guards import inspect_adapter as ia  # noqa: E402
from trace_guards.guards import gate_decision, run_all  # noqa: E402
from trace_guards.guards.g2_citation_in_trace import retrieved_ids  # noqa: E402
from trace_guards.guards.g3_absence_control import hit_count  # noqa: E402
from trace_guards.trace import Submission, ToolEvent, Trace  # noqa: E402

TARGET = "0.5714"
GUESS = "0.5"


def unsupported_guess() -> tuple[Trace, Submission]:
    """The tool printed the right value; the agent submits a different one."""
    event = ToolEvent(0, "python", {"code": "print(gc)"}, f"{TARGET}\n", False)
    trace = Trace("t", "Report the GC fraction of seq.fa.", (event,), {})
    return trace, Submission("answered", GUESS)


def test_rejection_message_names_rule_and_hides_values() -> None:
    trace, submission = unsupported_guess()
    findings = run_all(trace, submission)
    decision = gate_decision(findings, prior_rejections=0, max_rejections=2)
    assert not decision.accept and not decision.exhausted
    assert "value_evidence" in decision.message
    assert TARGET not in decision.message
    assert GUESS not in decision.message
    assert not any(ch.isdigit() for ch in decision.message)


def test_gate_accepts_and_flags_after_max_rejections() -> None:
    trace, submission = unsupported_guess()
    findings = run_all(trace, submission)
    outcomes = [gate_decision(findings, n, max_rejections=2) for n in range(4)]
    assert [d.accept for d in outcomes] == [False, False, True, True]
    assert [d.exhausted for d in outcomes] == [False, False, True, True]
    assert outcomes[2].message == ""


def test_gate_accepts_supported_submission_without_flag() -> None:
    trace, _ = unsupported_guess()
    findings = run_all(trace, Submission("answered", TARGET))
    assert findings == []
    assert gate_decision(findings, 0) == gate_decision([], 2)
    assert gate_decision(findings, 0).accept
    assert not gate_decision(findings, 0).exhausted


def test_gate_never_blocks_cannot_determine() -> None:
    trace = Trace("t", "prompt", (), {})
    submission = Submission("cannot_determine", "", ("D9",), ("missing.tsv",))
    findings = run_all(trace, submission, requires_citation=True)
    assert gate_decision(findings, 0).accept


RECORDS = [
    {"id": "D12", "title": "Growth of strain B", "abstract": "Rate was measured."},
    {"id": "D123", "title": "Growth of strain A", "abstract": "Follows D12."},
    {"id": "D7", "title": "Yield on methane", "abstract": "No growth data."},
]


def test_search_corpus_format_feeds_g2_and_g3() -> None:
    output = ia.search_corpus_text(RECORDS, "growth STRAIN")
    assert output.splitlines() == [
        "hits: 2",
        "D12 | Growth of strain B",
        "D123 | Growth of strain A",
    ]
    event = ToolEvent(0, "search_corpus", {"query": "growth strain"}, output, False)
    assert hit_count(event) == 2
    assert retrieved_ids(event) == {"D12", "D123"}
    assert ia.search_corpus_text(RECORDS, "plasmid") == "hits: 0"
    with pytest.raises(ToolError):
        ia.search_corpus_text(RECORDS, "   ")


def test_read_document_format_and_unknown_id() -> None:
    output = ia.read_document_text(RECORDS, "D123")
    assert output == "D123 | Growth of strain A\nFollows D12."
    event = ToolEvent(0, "read_document", {"id": "D123"}, output, False)
    assert retrieved_ids(event) == {"D123"}
    with pytest.raises(ToolError) as err:
        ia.read_document_text(RECORDS, "D1")
    assert "D1" not in str(err.value)


TABLE = (
    "locus_tag\tgene\tsynonyms\tproduct\n"
    "L_0001\tdnaA\t\tchromosomal replication initiator\n"
    "L_0002\tL_0002\tmmoX;smmo\tmethane monooxygenase component\n"
    "L_0003\tdnaAB\t\thypothetical protein\n"
)


def test_search_annotations_is_exact_and_ignores_synonyms() -> None:
    assert ia.search_annotations_text(TABLE, "dnaA").splitlines() == [
        "hits: 1",
        "L_0001 | dnaA | chromosomal replication initiator",
    ]
    assert ia.search_annotations_text(TABLE, "mmoX") == "hits: 0"
    assert ia.search_annotations_text(TABLE, "DNAA") == "hits: 0"
    assert "mmoX" not in ia.search_annotations_text(TABLE, "L_0002")


def test_trace_from_store_cuts_events_at_the_submission() -> None:
    def event(n: int) -> dict:
        return {"tool": "python", "arguments": {"code": f"c{n}"}, "output": str(n), "error": False}

    def record(answer: str, count: int, accepted: bool) -> dict:
        return {
            "submission": {"status": "answered", "answer": answer, "citations": [], "files": []},
            "event_count": count,
            "workdir_files": {"seq.fa": 10},
            "accepted": accepted,
            "gate_exhausted": False,
            "findings": [],
        }

    data = {
        ia.PROMPT_KEY: "prompt text",
        ia.REQUIRES_CITATION_KEY: False,
        ia.EVENTS_KEY: [event(7), event(8)],
        ia.SUBMISSIONS_KEY: [record("9", 0, False), record("8", 2, True)],
    }
    first_trace, first = ia.trace_from_store(data, "t", 0)
    assert first.answer == "9" and first_trace.events == ()
    last_trace, last = ia.trace_from_store(data, "t")
    assert last.answer == "8"
    assert [e.index for e in last_trace.events] == [0, 1]
    assert last_trace.prompt == "prompt text"
    assert last_trace.workdir_files == {"seq.fa": 10}
    assert [bool(run_all(*ia.trace_from_store(data, "t", i))) for i in (0, 1)] == [True, False]
    with pytest.raises(IndexError):
        ia.trace_from_store({ia.PROMPT_KEY: "p"}, "t")


def test_failed_tool_calls_are_recorded_as_error_events(tmp_path) -> None:
    """Missing input files and a python timeout must leave error events in the store.

    Driven by Inspect's scripted mock model in a local sandbox; no real model.
    """
    from inspect_ai import Task, eval
    from inspect_ai.agent import react
    from inspect_ai.dataset import Sample
    from inspect_ai.model import ModelOutput, ModelUsage, get_model

    calls = iter(
        [
            ("search_corpus", {"query": "growth"}),
            ("read_document", {"id": "D1"}),
            ("search_annotations", {"query": "dnaA"}),
            ("python", {"code": "import time\ntime.sleep(30)"}),
            ("python", {"code": "raise SystemExit(3)"}),
            ("python", {"code": "print('ok')"}),
            ("submit", {"status": "cannot_determine", "answer": ""}),
        ]
    )

    def respond(input, tools, tool_choice, config):
        name, arguments = next(calls)
        output = ModelOutput.for_tool_call("mockllm/model", name, arguments)
        # Explicit usage; without it mockllm downloads a tokenizer to count.
        output.usage = ModelUsage(input_tokens=1, output_tokens=1, total_tokens=2)
        return output

    task = Task(
        # No corpus.json and no annotations.tsv in the working directory.
        dataset=[Sample(id="s", input="prompt", files={"other.txt": "x"})],
        solver=[
            ia.trace_setup(),
            react(
                tools=[
                    ia.recorded_python(timeout=1),
                    ia.search_corpus(),
                    ia.read_document(),
                    ia.search_annotations(),
                ],
                submit=ia.agent_submit(True),
            ),
        ],
        sandbox="local",
        message_limit=30,
    )
    (log,) = eval(
        task,
        model=get_model("mockllm/model", custom_outputs=respond),
        log_dir=str(tmp_path),
        log_format="json",
        display="none",
    )
    assert log.status == "success"
    sample = log.samples[0]
    assert sample.error is None
    events = sample.store[ia.EVENTS_KEY]
    assert [(e["tool"], e["error"]) for e in events] == [
        ("search_corpus", True),
        ("read_document", True),
        ("search_annotations", True),
        ("python", True),
        ("python", True),
        ("python", False),
    ]
    assert events[0]["arguments"] == {"query": "growth"}
    assert all(e["output"] for e in events[:4])
    assert events[3]["output"] == "timed out"
    assert events[5]["output"] == "ok\n"
    # The failed calls reached the agent as tool errors, not as silent successes.
    tool_messages = [m for m in sample.messages if m.role == "tool"]
    assert [m.error is not None for m in tool_messages[:4]] == [True] * 4
    trace, _ = ia.trace_from_sample(sample)
    assert len(trace.events) == 6
