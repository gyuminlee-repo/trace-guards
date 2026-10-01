"""Inspect AI adapter: recorded tools, submit, gated submit, sample -> Trace.

Every tool call is appended to the sample store so that the gate (inside the
run) and the scanner (after the run, from the log) read the same record.
`submit` calls are not tool events; they are kept under their own store key.
"""

from __future__ import annotations

import csv
import io
import json
from dataclasses import asdict
from typing import Any, Mapping

from inspect_ai.agent import AgentSubmit
from inspect_ai.log import EvalSample
from inspect_ai.solver import Generate, Solver, TaskState, solver
from inspect_ai.tool import Tool, ToolError, tool
from inspect_ai.util import sandbox, store

from .guards import DEFAULT_MAX_REJECTIONS, gate_decision, run_all
from .guards.g2_citation_in_trace import SEPARATOR
from .trace import STATUSES, Finding, Submission, ToolEvent, Trace

PROMPT_KEY = "tg:prompt"
REQUIRES_CITATION_KEY = "tg:requires_citation"
EVENTS_KEY = "tg:events"
SUBMISSIONS_KEY = "tg:submissions"
REJECTIONS_KEY = "tg:rejections"

SUBMIT_NAME = "submit"

_LIST_FILES = (
    "import json, os\n"
    "sizes = {}\n"
    "for root, _, names in os.walk('.'):\n"
    "    for name in names:\n"
    "        path = os.path.normpath(os.path.join(root, name))\n"
    "        sizes[path.replace(os.sep, '/')] = os.path.getsize(path)\n"
    "print(json.dumps(sizes))\n"
)


# --------------------------------------------------------------------------
# Pure helpers (no sandbox, no store): tool output formats and trace building
# --------------------------------------------------------------------------


def search_corpus_text(records: list[dict], query: str) -> str:
    """`hits: N`, then one `id | title` line per record matching every term."""
    terms = query.lower().split()
    if not terms:
        raise ToolError("query is empty")
    hits = [
        r
        for r in records
        if all(t in f"{r['title']} {r['abstract']}".lower() for t in terms)
    ]
    lines = [f"hits: {len(hits)}"]
    lines.extend(f"{r['id']}{SEPARATOR}{r['title']}" for r in hits)
    return "\n".join(lines)


def read_document_text(records: list[dict], doc_id: str) -> str:
    """`id | title` header line, then the abstract."""
    for r in records:
        if r["id"] == doc_id:
            return f"{r['id']}{SEPARATOR}{r['title']}\n{r['abstract']}"
    raise ToolError("unknown document id")


def search_annotations_text(table: str, query: str) -> str:
    """Exact, case-sensitive match on the gene column. Synonyms are not searched."""
    rows = csv.DictReader(io.StringIO(table), delimiter="\t")
    hits = [r for r in rows if r["gene"] == query]
    lines = [f"hits: {len(hits)}"]
    lines.extend(
        SEPARATOR.join((r["locus_tag"], r["gene"], r["product"])) for r in hits
    )
    return "\n".join(lines)


def submissions_in(data: Mapping[str, Any]) -> list[dict]:
    """Submission records of one run in call order (rejected and accepted)."""
    return list(data.get(SUBMISSIONS_KEY, []))


def trace_from_store(
    data: Mapping[str, Any], task_id: str, submission_index: int = -1
) -> tuple[Trace, Submission]:
    """Trace as it stood when the chosen submission was made, and that submission."""
    record = submissions_in(data)[submission_index]
    events = tuple(
        ToolEvent(
            index=i,
            tool=e["tool"],
            arguments=dict(e["arguments"]),
            output=e["output"],
            error=bool(e["error"]),
        )
        for i, e in enumerate(data.get(EVENTS_KEY, [])[: record["event_count"]])
    )
    trace = Trace(
        task_id=task_id,
        prompt=data[PROMPT_KEY],
        events=events,
        workdir_files=dict(record["workdir_files"]),
    )
    fields = record["submission"]
    submission = Submission(
        status=fields["status"],
        answer=fields["answer"],
        citations=tuple(fields["citations"]),
        files=tuple(fields["files"]),
    )
    return trace, submission


def trace_from_sample(
    sample: EvalSample, submission_index: int = -1
) -> tuple[Trace, Submission]:
    """Build the trace of a logged sample. Raises IndexError if nothing was submitted."""
    return trace_from_store(sample.store, str(sample.id), submission_index)


def scan_sample(sample: EvalSample, submission_index: int = -1) -> list[Finding]:
    """Scanner: run all guards over one submission of a logged sample."""
    trace, submission = trace_from_sample(sample, submission_index)
    return run_all(
        trace, submission, requires_citation=sample.store[REQUIRES_CITATION_KEY]
    )


# --------------------------------------------------------------------------
# Inspect components
# --------------------------------------------------------------------------


@solver
def trace_setup() -> Solver:
    """Put the task prompt and citation requirement into the store. Run before the agent."""

    async def solve(state: TaskState, generate: Generate) -> TaskState:
        state.store.set(PROMPT_KEY, state.input_text)
        state.store.set(
            REQUIRES_CITATION_KEY, bool(state.metadata.get("requires_citation", False))
        )
        return state

    return solve


def _record(tool_name: str, arguments: dict, output: str, error: bool) -> None:
    s = store()
    event = {"tool": tool_name, "arguments": arguments, "output": output, "error": error}
    s.set(EVENTS_KEY, s.get(EVENTS_KEY, []) + [event])


async def _read_json_records(path: str) -> list[dict]:
    return json.loads(await sandbox().read_file(path))


@tool(name="python")
def recorded_python(timeout: int = 60) -> Tool:
    async def execute(code: str) -> str:
        """Run a Python script in the working directory and return what it printed.

        Each call is a fresh process; nothing is kept between calls. Use print()
        to see values.

        Args:
          code: Python source to run.
        """
        arguments = {"code": code}
        try:
            result = await sandbox().exec(["python3", "-"], input=code, timeout=timeout)
        except TimeoutError:
            _record("python", arguments, "timed out", True)
            raise
        output = f"{result.stderr}\n{result.stdout}" if result.stderr else result.stdout
        _record("python", arguments, output, not result.success)
        return output

    return execute


@tool
def search_corpus(corpus_file: str = "corpus.json") -> Tool:
    async def execute(query: str) -> str:
        """Keyword search over the local document corpus (titles and abstracts).

        The first output line is `hits: N`; each further line is `id | title`.
        A document matches when it contains every word of the query.

        Args:
          query: Words to search for, separated by spaces.
        """
        arguments = {"query": query}
        records = await _read_json_records(corpus_file)
        try:
            output = search_corpus_text(records, query)
        except ToolError as err:
            _record("search_corpus", arguments, err.message, True)
            raise
        _record("search_corpus", arguments, output, False)
        return output

    return execute


@tool
def read_document(corpus_file: str = "corpus.json") -> Tool:
    async def execute(id: str) -> str:
        """Return one corpus document: a line `id | title`, then its abstract.

        Args:
          id: Document id as shown by search_corpus.
        """
        arguments = {"id": id}
        records = await _read_json_records(corpus_file)
        try:
            output = read_document_text(records, id)
        except ToolError as err:
            _record("read_document", arguments, err.message, True)
            raise
        _record("read_document", arguments, output, False)
        return output

    return execute


@tool
def search_annotations(annotation_file: str = "annotations.tsv") -> Tool:
    async def execute(query: str) -> str:
        """Look up a gene name in the annotation table.

        Exact, case-sensitive match on the gene column. The first output line
        is `hits: N`; each further line is `locus_tag | gene | product`.

        Args:
          query: Gene name.
        """
        table = await sandbox().read_file(annotation_file)
        output = search_annotations_text(table, query)
        _record("search_annotations", {"query": query}, output, False)
        return output

    return execute


async def _workdir_files() -> dict[str, int]:
    result = await sandbox().exec(["python3", "-c", _LIST_FILES])
    if not result.success:
        raise RuntimeError(f"could not list the working directory: {result.stderr}")
    return json.loads(result.stdout)


def _make_submit(max_rejections: int | None) -> Tool:
    """One tool body for both conditions so name, schema and text are identical."""

    async def execute(
        status: str,
        answer: str,
        citations: list[str] | None = None,
        files: list[str] | None = None,
    ) -> str:
        """Submit the final report. This ends the task.

        Args:
          status: One of "answered" (you state a value), "absent" (the thing asked about does not exist in the provided data), "cannot_determine" (the provided material does not allow an answer).
          answer: The final value or a short statement. May be empty for cannot_determine.
          citations: Ids of corpus documents the answer relies on. Empty if none.
          files: Output files you wrote, relative to the working directory. Empty if none.
        """
        if status not in STATUSES:
            raise ToolError(f"status must be one of: {', '.join(STATUSES)}")
        submission = Submission(
            status=status,
            answer=answer,
            citations=tuple(citations or ()),
            files=tuple(files or ()),
        )
        s = store()
        record: dict[str, Any] = {
            "submission": asdict(submission),
            "event_count": len(s.get(EVENTS_KEY, [])),
            "workdir_files": await _workdir_files(),
            "accepted": True,
            "gate_exhausted": False,
            "findings": [],
        }
        message = ""
        if max_rejections is not None:
            data = {
                PROMPT_KEY: s.get(PROMPT_KEY),
                EVENTS_KEY: s.get(EVENTS_KEY, []),
                SUBMISSIONS_KEY: [record],
            }
            if data[PROMPT_KEY] is None:
                raise RuntimeError("trace_setup() must run before the agent")
            trace, _ = trace_from_store(data, task_id="live")
            findings = run_all(
                trace, submission, requires_citation=s.get(REQUIRES_CITATION_KEY)
            )
            rejections = s.get(REJECTIONS_KEY, 0)
            decision = gate_decision(findings, rejections, max_rejections)
            record["findings"] = [asdict(f) for f in findings]
            record["accepted"] = decision.accept
            record["gate_exhausted"] = decision.exhausted
            message = decision.message
            if not decision.accept:
                s.set(REJECTIONS_KEY, rejections + 1)
        s.set(SUBMISSIONS_KEY, s.get(SUBMISSIONS_KEY, []) + [record])
        if not record["accepted"]:
            raise ToolError(message)
        return json.dumps(record["submission"])

    return execute


@tool
def submit() -> Tool:
    """Gate-off submit: records the submission and accepts it."""
    return _make_submit(None)


@tool
def gated_submit(max_rejections: int = DEFAULT_MAX_REJECTIONS) -> Tool:
    """Gate-on submit: rejects a submission with findings, at most max_rejections times."""
    return _make_submit(max_rejections)


def agent_submit(
    gated: bool, max_rejections: int = DEFAULT_MAX_REJECTIONS
) -> AgentSubmit:
    """`submit=` argument for `react`; the tool is named `submit` in both conditions."""
    chosen = gated_submit(max_rejections) if gated else submit()
    return AgentSubmit(name=SUBMIT_NAME, tool=chosen)
