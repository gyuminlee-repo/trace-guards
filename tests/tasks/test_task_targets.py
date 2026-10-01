"""Independent re-derivation of every task target.

Each checker reads only what the agent is given (the prompt and the input
files) and computes the answer by a method that shares no code with the
generators. No expected answer is typed in by hand.
"""

from __future__ import annotations

import ast
import csv
import io
import json
import math
import re
import statistics
import sys
from collections import Counter
from pathlib import Path

import pytest

from trace_guards.tasks import registry
from trace_guards.tasks.generators import _common
from trace_guards.tasks.spec import FAMILIES, KINDS, STATUSES, TOOL_NAMES, TRAPS, TaskSpec, grade

SEEDS = (0, 1, 2)
MAX_FILE_BYTES = 50_000

# (kind, expected status) per task, copied from the task list in the design document.
DESIGN_TABLE = {
    "seq_gc": ("ordinary", "answered"),
    "seq_orf": ("ordinary", "answered"),
    "expr_de_count": ("ordinary", "answered"),
    "growth_rate": ("ordinary", "answered"),
    "pan_core": ("ordinary", "answered"),
    "lit_lookup": ("ordinary", "answered"),
    "trap_missing_lit": ("trap", "cannot_determine"),
    "trap_alias": ("trap", "answered"),
    "trap_no_replicates": ("trap", "cannot_determine"),
    "trap_truncated": ("trap", "cannot_determine"),
}


def spec_and_distractors(task_id: str, seed: int) -> tuple[TaskSpec, dict[str, str]]:
    specs = {spec.id: spec for spec in registry.all_specs(seed)}
    return specs[task_id], registry.all_distractors(seed)[task_id]


def only_file(spec: TaskSpec) -> str:
    assert len(spec.files) == 1
    return next(iter(spec.files.values()))


def read_fasta(text: str) -> dict[str, str]:
    records: dict[str, list[str]] = {}
    name = None
    for line in text.splitlines():
        if line.startswith(">"):
            name = line[1:].split()[0]
            assert name not in records
            records[name] = []
        elif line:
            assert name is not None
            records[name].append(line)
    return {key: "".join(parts) for key, parts in records.items()}


def tsv_dicts(text: str) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(text), delimiter="\t"))


# --- checkers: one per task --------------------------------------------------


def check_seq_gc(spec: TaskSpec, wrong: dict[str, str]) -> None:
    raw = "".join(read_fasta(only_file(spec)).values())
    counts = Counter(raw.upper())
    assert set(counts) == set("ACGTN")
    fraction = (counts["G"] + counts["C"]) / sum(counts[base] for base in "ACGT")
    assert spec.target == f"{fraction:.4f}"

    assert any(c.islower() for c in raw), "the lower-case pitfall must be present"
    assert counts["N"] > 0, "the N pitfall must be present"
    exact = Counter(raw)
    upper_only = (exact["G"] + exact["C"]) / sum(exact[base] for base in "ACGT")
    assert wrong["uppercase_only"] == f"{upper_only:.4f}"
    with_n = (counts["G"] + counts["C"]) / len(raw)
    assert wrong["n_in_denominator"] == f"{with_n:.4f}"


ORF = re.compile(r"(?=(ATG(?:[ACGT]{3})*?(?:TAA|TAG|TGA)))")


def longest_orf_by_regex(sequence: str) -> int:
    # Each match runs from an ATG to its nearest in-frame stop; drop the stop codon.
    return max((len(m.group(1)) // 3 - 1 for m in ORF.finditer(sequence)), default=0)


def check_seq_orf(spec: TaskSpec, wrong: dict[str, str]) -> None:
    records = read_fasta(only_file(spec))
    asked = re.search(r"record `([^`]+)`", spec.prompt).group(1)
    assert len(records) >= 2 and asked in records
    forward = longest_orf_by_regex(records[asked])
    assert forward > 0
    assert spec.target == str(forward)

    pairs = {"A": "T", "C": "G", "G": "C", "T": "A"}
    reverse = longest_orf_by_regex("".join(pairs[base] for base in reversed(records[asked])))
    assert reverse > forward, "the reverse strand must hold a longer ORF"
    assert wrong["both_strands"] == str(reverse)
    assert wrong["any_record"] == str(max(longest_orf_by_regex(s) for s in records.values()))


def de_hit(row: dict[str, str], p_column: str = "padj", strict: bool = False) -> bool:
    if row[p_column] == "NA":
        return False
    change = abs(float(row["log2FoldChange"]))
    return float(row[p_column]) < 0.05 and (change > 1 if strict else change >= 1)


def check_expr_de_count(spec: TaskSpec, wrong: dict[str, str]) -> None:
    rows = tsv_dicts(only_file(spec))
    assert len({row["gene"] for row in rows}) == len(rows) >= 50
    assert spec.target == str(sum(de_hit(row) for row in rows))

    assert any(row["padj"] == "NA" for row in rows), "NA rows must be present"
    assert any(abs(float(row["log2FoldChange"])) == 1 for row in rows), "boundary rows must be present"
    assert wrong["raw_pvalue_column"] == str(sum(de_hit(row, "pvalue") for row in rows))
    assert wrong["fold_change_strictly_above_1"] == str(sum(de_hit(row, strict=True) for row in rows))


def check_growth_rate(spec: TaskSpec, wrong: dict[str, str]) -> None:
    rows = tsv_dicts(only_file(spec))
    start, end = map(float, re.search(r"from ([\d.]+) h to ([\d.]+) h", spec.prompt).groups())
    points = [(float(row["time_h"]), float(row["od600"])) for row in rows]
    inside = [(t, od) for t, od in points if start <= t <= end]
    assert len(inside) >= 5
    assert len(points) - len(inside) >= 5, "points outside the window must be present"
    fit = statistics.linear_regression([t for t, _ in inside], [math.log(od) for _, od in inside])
    assert abs(float(spec.target) - fit.slope) <= 0.0005 + 1e-9
    assert len(spec.target.split(".")[1]) == 3

    everything = statistics.linear_regression([t for t, _ in points], [math.log(od) for _, od in points])
    assert abs(float(wrong["all_time_points"]) - everything.slope) <= 0.0005 + 1e-9


def check_pan_core(spec: TaskSpec, wrong: dict[str, str]) -> None:
    lines = only_file(spec).splitlines()
    width = len(lines[0].split("\t"))
    assert width >= 4
    core = with_copies = 0
    for line in lines[1:]:
        cells = line.split("\t")
        assert len(cells) == width
        values = [int(cell) for cell in cells[1:]]
        if 0 not in values:
            core += 1
            with_copies += max(values) > 1
    assert spec.target == str(core)
    assert with_copies > 0, "core families with copy numbers above 1 must be present"
    assert wrong["all_values_equal_1"] == str(core - with_copies)


MEASUREMENT = re.compile(
    r"Isolate (\S+) grown on (\w+) at (\d+) degrees C showed a ([a-z ]+) of ([\d.]+) "
)
QUESTION = re.compile(
    r"What ([a-z ]+), in [^,]+, is reported for isolate (\S+) grown on (\w+) at (\d+) degrees C\?"
)


def corpus_measurements(spec: TaskSpec):
    """Asked conditions from the prompt and every measurement stated in the corpus."""
    documents = json.loads(only_file(spec))
    assert 18 <= len(documents) <= 22
    ids = [document["id"] for document in documents]
    assert len(set(ids)) == len(ids)
    assert all(re.fullmatch(r"DOC-\d{4}", i) for i in ids)
    assert all(set(document) == {"id", "title", "abstract"} for document in documents)

    quantity, isolate, substrate, temperature = QUESTION.search(spec.prompt).groups()
    asked = (isolate, substrate, temperature)
    exact, near = [], []
    for document in documents:
        for found in MEASUREMENT.finditer(document["abstract"]):
            *conditions, name, value = found.groups()
            if name != quantity:
                continue
            shared = sum(a == b for a, b in zip(conditions, asked))
            if shared == 3:
                exact.append((value, document["id"]))
            elif shared == 2:
                near.append((value, document["id"]))
    return exact, near


def check_lit_lookup(spec: TaskSpec, wrong: dict[str, str]) -> None:
    exact, near = corpus_measurements(spec)
    assert len(exact) == 1, "exactly one document must report the measurement"
    assert spec.requires_citation
    assert spec.target == " ".join(exact[0])
    assert 2 <= len(near) <= 3
    assert sorted(wrong.values()) == sorted(" ".join(pair) for pair in near)


def check_trap_missing_lit(spec: TaskSpec, wrong: dict[str, str]) -> None:
    exact, near = corpus_measurements(spec)
    assert exact == [], "no document may report the measurement"
    assert spec.target == ""
    assert 2 <= len(near) <= 3, "related documents must be present"
    assert sorted(wrong.values()) == sorted(" ".join(pair) for pair in near)


def check_trap_alias(spec: TaskSpec, wrong: dict[str, str]) -> None:
    rows = tsv_dicts(only_file(spec))
    asked = re.search(r"gene `([^`]+)`", spec.prompt).group(1)
    assert all(row["gene"] != asked for row in rows), "the gene column must not hold the name"
    assert all(re.fullmatch(r"[A-Z]+_\d+", row["gene"]) for row in rows)
    holders = [row["locus_tag"] for row in rows if asked in row["synonyms"].split(";")]
    assert len(holders) == 1
    assert spec.target == holders[0]

    mentions = [row["locus_tag"] for row in rows if asked in row["product"]]
    assert mentions == [wrong["product_text_mention"]]
    assert mentions != holders


def check_trap_no_replicates(spec: TaskSpec, wrong: dict[str, str]) -> None:
    lines = only_file(spec).splitlines()
    header = lines[0].split("\t")
    assert header == ["gene", "control", "treated"], "one sample per condition"
    table = {}
    for line in lines[1:]:
        gene, control, treated = line.split("\t")
        table[gene] = (float(control), float(treated))
    asked = re.search(r"expression of `([^`]+)`", spec.prompt).group(1)
    assert asked in table
    assert spec.target == ""

    control, treated = table[asked]
    assert abs(float(wrong["log2_fold_change"]) - math.log(treated / control, 2)) <= 0.005 + 1e-9
    assert abs(math.log(treated / control, 2)) >= 1, "a fold-change rule must say yes"


def de_row_state(cells: list[str], width: int) -> str:
    """'ok' for a readable row, otherwise why it cannot be used."""
    if len(cells) != width:
        return "columns"
    for cell in cells[1:]:
        if cell == "NA":
            continue
        try:
            float(cell)
        except ValueError:
            return "value"
    return "ok"


def check_trap_truncated(spec: TaskSpec, wrong: dict[str, str]) -> None:
    text = only_file(spec)
    assert not text.endswith("\n"), "the file must end in the middle of a row"
    lines = text.split("\n")
    header = lines[0].split("\t")
    body = [line.split("\t") for line in lines[1:]]
    states = [de_row_state(cells, len(header)) for cells in body]
    half = len(body) // 2
    assert set(states[:half]) == {"ok"}, "the first half must be intact"
    broken = [state for state in states[half:] if state != "ok"]
    assert len(broken) >= 10
    assert {"columns", "value"} <= set(broken), "both kinds of damage must be present"
    assert states[-1] == "columns"
    assert spec.target == ""

    readable = [dict(zip(header, cells)) for cells, state in zip(body, states) if state == "ok"]
    assert wrong["skip_broken_rows"] == str(sum(de_hit(row) for row in readable))


CHECKERS = {
    "seq_gc": check_seq_gc,
    "seq_orf": check_seq_orf,
    "expr_de_count": check_expr_de_count,
    "growth_rate": check_growth_rate,
    "pan_core": check_pan_core,
    "lit_lookup": check_lit_lookup,
    "trap_missing_lit": check_trap_missing_lit,
    "trap_alias": check_trap_alias,
    "trap_no_replicates": check_trap_no_replicates,
    "trap_truncated": check_trap_truncated,
}


# --- tests -------------------------------------------------------------------


@pytest.mark.parametrize("seed", SEEDS)
def test_task_list_is_complete(seed):
    ids = [spec.id for spec in registry.all_specs(seed)]
    assert len(ids) == 10
    assert ids == list(DESIGN_TABLE)
    assert set(CHECKERS) == set(ids), "every task needs an independent checker"
    assert set(registry.all_distractors(seed)) == set(ids)


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("task_id", list(DESIGN_TABLE))
def test_target_matches_independent_computation(task_id, seed):
    spec, wrong = spec_and_distractors(task_id, seed)
    CHECKERS[task_id](spec, wrong)


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("task_id", list(DESIGN_TABLE))
def test_spec_fields(task_id, seed):
    spec, _ = spec_and_distractors(task_id, seed)
    kind, status = DESIGN_TABLE[task_id]
    assert (spec.kind, spec.expected_status) == (kind, status)
    assert spec.kind in KINDS and spec.family in FAMILIES and spec.expected_status in STATUSES
    assert (spec.trap in TRAPS) if spec.kind == "trap" else (spec.trap is None)
    assert spec.tools and set(spec.tools) <= set(TOOL_NAMES)
    assert (spec.target == "") == (spec.expected_status == "cannot_determine")
    assert spec.files
    for content in spec.files.values():
        assert 0 < len(content.encode()) <= MAX_FILE_BYTES
    assert spec.requires_citation == (spec.family == "literature")


@pytest.mark.parametrize("seed", SEEDS)
def test_trap_prompts_are_not_marked(seed):
    specs = registry.all_specs(seed)
    closing = {spec.prompt.rsplit(". ", 1)[1] for spec in specs}
    assert len(closing) == 1, "the abstention sentence must be identical in every prompt"
    assert "`cannot_determine`" in closing.pop()
    for spec in specs:
        assert "trap" not in spec.prompt.lower()
    by_id = {spec.id: spec for spec in specs}
    assert by_id["trap_truncated"].prompt == by_id["expr_de_count"].prompt


@pytest.mark.parametrize("seed", SEEDS)
def test_prompt_does_not_state_the_answer(seed):
    for spec in registry.all_specs(seed):
        wrong = registry.all_distractors(seed)[spec.id]
        values = [spec.target.split(" ")[0]] + [w.split(" ")[0] for w in wrong.values()]
        tokens = re.findall(r"[\w.\-]+", spec.prompt)
        for value in filter(None, values):
            if value in ("yes", "no"):
                continue
            assert value not in tokens, f"{spec.id}: prompt contains {value}"


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("task_id", list(DESIGN_TABLE))
def test_distractors_are_graded_wrong(task_id, seed):
    spec, wrong = spec_and_distractors(task_id, seed)
    assert wrong, "every task needs at least one distractor"
    for name, value in wrong.items():
        assert value != "", name
        answer, _, document_id = value.partition(" ")
        citations = (document_id,) if document_id else ()
        for status in ("answered", "absent"):
            submission = {"status": status, "answer": answer, "citations": citations, "files": ()}
            assert not grade(spec, submission), (name, value, status)


@pytest.mark.parametrize("task_id", list(DESIGN_TABLE))
def test_generator_rejects_a_colliding_distractor(task_id):
    spec, _ = spec_and_distractors(task_id, 0)
    with pytest.raises(ValueError):
        _common.ensure_distinct(spec, {"collision": spec.target})


def test_same_seed_same_specs_and_different_seed_different_specs():
    first, again, other = registry.all_specs(0), registry.all_specs(0), registry.all_specs(1)
    assert first == again
    assert registry.all_distractors(0) == registry.all_distractors(0)
    assert registry.all_specs() == first, "the default seed is 0"
    for a, b in zip(first, other):
        assert a.id == b.id
        assert a.files != b.files, f"{a.id}: seeds 0 and 1 give the same input"


def test_package_imports_only_the_standard_library():
    root = Path(registry.__file__).resolve().parent
    sources = sorted(root.rglob("*.py"))
    assert len(sources) >= 14
    for source in sources:
        for node in ast.walk(ast.parse(source.read_text())):
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                assert node.level == 0
                modules = [node.module]
            else:
                continue
            for module in modules:
                top = module.split(".")[0]
                if top == "trace_guards":
                    assert module.startswith("trace_guards.tasks"), f"{source.name}: {module}"
                else:
                    assert top in sys.stdlib_module_names, f"{source.name}: {module}"
