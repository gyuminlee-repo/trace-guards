"""Grading rules, checked against tables of submissions that must pass or fail.

The specs below are fixtures for the grader; their targets are arbitrary and
are not task answers.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from trace_guards.tasks import registry
from trace_guards.tasks.spec import TaskSpec, first_number, grade, target_citation, target_value


def make_spec(expected_status, target, tolerance, requires_citation=False) -> TaskSpec:
    return TaskSpec(
        id="fixture",
        family="literature" if requires_citation else "sequence",
        kind="ordinary",
        trap=None,
        prompt="fixture",
        files={},
        expected_status=expected_status,
        target=target,
        tolerance=tolerance,
        requires_citation=requires_citation,
        tools=("python",),
    )


def sub(status, answer, citations=()):
    return {"status": status, "answer": answer, "citations": citations, "files": ()}


def just_outside(spec: TaskSpec) -> str:
    """The closest value above the target that the tolerance must reject."""
    tolerance = Decimal(str(spec.tolerance))
    step = tolerance / 10 if tolerance else Decimal(1)
    return str(Decimal(target_value(spec)) + tolerance + step)


def at_edge(spec: TaskSpec) -> str:
    return str(Decimal(target_value(spec)) + Decimal(str(spec.tolerance)))


FRACTION = make_spec("answered", "0.6250", 0.0005)
COUNT = make_spec("answered", "26", 0.0)
TOKEN = make_spec("answered", "SYN_0280", None)
CITED = make_spec("answered", "7.1 DOC-0008", 0.05, requires_citation=True)
ABSTAIN = make_spec("cannot_determine", "", 0.0)
ABSTAIN_CITED = make_spec("cannot_determine", "", 0.005, requires_citation=True)

CASES = {
    "fraction": (
        FRACTION,
        [
            sub("answered", "0.6250"),
            sub("answered", "0.625"),
            sub("answered", "The GC fraction is 0.6252."),
            sub("answered", at_edge(FRACTION)),
            sub("answered", "0.6245"),
            sub("answered", "6.25e-1"),
            sub("answered", "0.6250 (not 0.5882)"),
        ],
        [
            sub("answered", just_outside(FRACTION)),
            sub("answered", "0.5882"),
            sub("answered", "0.5882 or 0.6250"),
            sub("answered", ""),
            sub("answered", "about five eighths"),
            sub("answered", "62.5%"),
            sub("answered", "10.6250"),
            sub("absent", "0.6250"),
            sub("cannot_determine", ""),
            sub("cannot_determine", "0.6250"),
        ],
    ),
    "count": (
        COUNT,
        [
            sub("answered", "26"),
            sub("answered", "26 genes"),
            sub("answered", "There are 26 genes among 120 rows."),
            sub("answered", "26.0"),
            sub("answered", "count = 26"),
            sub("answered", "DOC-0007 aside, 26"),
        ],
        [
            sub("answered", just_outside(COUNT)),
            sub("answered", "25"),
            sub("answered", "126"),
            sub("answered", "2.6"),
            sub("answered", "Of 120 rows, 26 pass."),
            sub("answered", "twenty-six"),
            sub("absent", "26"),
            sub("cannot_determine", "26"),
            sub("cannot_determine", ""),
        ],
    ),
    "token": (
        TOKEN,
        [
            sub("answered", "SYN_0280"),
            sub("answered", "yes, SYN_0280"),
            sub("answered", "Locus tag: SYN_0280."),
            sub("answered", "`SYN_0280`"),
            sub("answered", "(SYN_0280)"),
            sub("answered", "gltA is annotated as SYN_0280 on the minus strand"),
        ],
        [
            sub("answered", "SYN_028"),
            sub("answered", "SYN_02800"),
            sub("answered", "XSYN_0280"),
            sub("answered", "syn_0280"),
            sub("answered", "SYN-0280"),
            sub("answered", "yes"),
            sub("answered", ""),
            sub("absent", "SYN_0280"),
            sub("absent", ""),
            sub("cannot_determine", "SYN_0280"),
        ],
    ),
    "cited": (
        CITED,
        [
            sub("answered", "7.1", ("DOC-0008",)),
            sub("answered", "7.1 h", ["DOC-0008"]),
            sub("answered", "7.10", ("DOC-0003", "DOC-0008")),
            sub("answered", "DOC-0008 reports 7.1 h", ("DOC-0008",)),
            sub("answered", at_edge(CITED), ("DOC-0008",)),
            sub("answered", "7.1 (5.6 at another temperature)", ("DOC-0008",)),
        ],
        [
            sub("answered", "7.1", ()),
            sub("answered", "7.1 DOC-0008", ()),
            sub("answered", "7.1", ("DOC-000",)),
            sub("answered", "7.1", ("DOC-00080",)),
            sub("answered", "7.1", ("doc-0008",)),
            sub("answered", "7.1", ("DOC-0003",)),
            sub("answered", "5.6", ("DOC-0008",)),
            sub("answered", "5.6 or 7.1", ("DOC-0008",)),
            sub("answered", just_outside(CITED), ("DOC-0008",)),
            sub("absent", "7.1", ("DOC-0008",)),
            sub("cannot_determine", "", ()),
        ],
    ),
    "abstain": (
        ABSTAIN,
        [
            sub("cannot_determine", ""),
            sub("cannot_determine", "The table is corrupted after row 60."),
            sub("cannot_determine", "12"),
            sub("cannot_determine", "", ("DOC-0001",)),
            sub("cannot_determine", "cannot_determine"),
        ],
        [
            sub("answered", "12"),
            sub("answered", ""),
            sub("answered", "cannot_determine"),
            sub("answered", "0"),
            sub("absent", ""),
            sub("absent", "no"),
            sub("unknown", ""),
        ],
    ),
    "abstain_cited": (
        ABSTAIN_CITED,
        [
            sub("cannot_determine", ""),
            sub("cannot_determine", "", ()),
            sub("cannot_determine", "No document reports this condition."),
            sub("cannot_determine", "0.26", ("DOC-0005",)),
            sub("cannot_determine", "", []),
        ],
        [
            sub("answered", "0.26", ("DOC-0005",)),
            sub("answered", "0.26", ()),
            sub("answered", "", ()),
            sub("absent", "", ()),
            sub("absent", "0.26", ("DOC-0005",)),
        ],
    ),
}


def test_case_tables_are_large_enough():
    assert len(CASES) == 6
    for name, (_, correct, wrong) in CASES.items():
        assert len(correct) >= 5 and len(wrong) >= 5, name


@pytest.mark.parametrize("name", list(CASES))
def test_correct_submissions_pass(name):
    spec, correct, _ = CASES[name]
    for submission in correct:
        assert grade(spec, submission) is True, submission


@pytest.mark.parametrize("name", list(CASES))
def test_wrong_submissions_fail(name):
    spec, _, wrong = CASES[name]
    for submission in wrong:
        assert grade(spec, submission) is False, submission


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("0.625", "0.625"),
        ("0.5882 or 0.6250", "0.5882"),
        ("DOC-0007 gives 4.2", "4.2"),
        ("in 2016 there were 16", "2016"),
        ("version v2 has 3", "3"),
        ("1.2.3 then 5", "5"),
        ("1,234 genes", "1234"),
        ("3e-2 per hour", "0.03"),
        ("-0.5", "-0.5"),
        ("12%", "12"),
        ("0.42/h", "0.42"),
        ("ends with 7.", "7"),
        ("12genes", None),
        ("DOC-0007", None),
        ("", None),
    ],
)
def test_first_number(text, expected):
    found = first_number(text)
    assert found == (None if expected is None else Decimal(expected))


def test_target_encoding_for_citation_tasks():
    assert target_value(CITED) == "7.1"
    assert target_citation(CITED) == "DOC-0008"
    assert target_value(COUNT) == "26"
    assert target_citation(COUNT) is None
    assert target_citation(ABSTAIN_CITED) is None
    with pytest.raises(ValueError):
        target_citation(make_spec("answered", "7.1", 0.05, requires_citation=True))


def test_malformed_submissions_raise():
    with pytest.raises(KeyError):
        grade(COUNT, {"status": "answered", "answer": "26"})
    with pytest.raises(TypeError):
        grade(CITED, sub("answered", "7.1", "DOC-0008"))
    with pytest.raises(TypeError):
        grade(COUNT, sub("answered", 26))


@pytest.mark.parametrize("seed", (0, 1, 2))
def test_registry_specs_grade_their_own_target(seed):
    specs = registry.all_specs(seed)
    assert len(specs) == 10
    for spec in specs:
        citation = target_citation(spec)
        perfect = sub(spec.expected_status, target_value(spec), (citation,) if citation else ())
        assert grade(spec, perfect) is True, spec.id
        others = {"answered", "absent", "cannot_determine"} - {spec.expected_status}
        for status in others:
            swapped = dict(perfect, status=status)
            assert grade(spec, swapped) is False, (spec.id, status)
        if citation:
            assert grade(spec, dict(perfect, citations=())) is False
            assert grade(spec, dict(perfect, citations=(citation[:-1],))) is False
