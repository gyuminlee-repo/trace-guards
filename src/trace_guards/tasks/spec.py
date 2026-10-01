"""Task specification and grading.

Conventions fixed here (the design leaves them open):

* A target is numeric exactly when ``tolerance`` is not None. Otherwise it is
  a token that must appear as a whole token in the answer.
* When ``requires_citation`` is true and the task has a target, ``target`` is
  ``"<value> <document id>"`` separated by one space. ``target_value`` and
  ``target_citation`` split it.
* ``grade`` takes a plain mapping with keys ``status``, ``answer``,
  ``citations`` and ``files`` so that this package does not depend on the
  trace classes.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal

STATUSES = ("answered", "absent", "cannot_determine")
FAMILIES = ("sequence", "expression", "growth", "pangenome", "literature")
KINDS = ("ordinary", "trap")
TRAPS = ("missing_literature", "alias_search", "insufficient_design", "corrupted_input")
TOOL_NAMES = ("python", "search_corpus", "read_document", "search_annotations")


@dataclass(frozen=True)
class TaskSpec:
    id: str
    family: str
    kind: str
    trap: str | None
    prompt: str
    files: dict[str, str]
    expected_status: str
    target: str
    tolerance: float | None
    requires_citation: bool
    tools: tuple[str, ...]


# A number must stand alone: not glued to a word, a dot or a hyphenated id,
# so "0007" in "DOC-0007" and "16" in "2016" or "1.16" are not numbers.
_NUMBER = re.compile(
    r"(?<![\w.])(?<![\w.][-+])"
    r"[-+]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?(?:[eE][-+]?\d+)?"
    r"(?![\w]|\.\d)"
)
_TOKEN = re.compile(r"[A-Za-z0-9_\-]+")


def first_number(text: str) -> Decimal | None:
    """Return the first standalone number in ``text``, or None."""
    match = _NUMBER.search(text)
    if match is None:
        return None
    return Decimal(match.group(0).replace(",", ""))


def target_value(spec: TaskSpec) -> str:
    """The value part of the target (the whole target unless a citation is encoded)."""
    if spec.requires_citation and spec.target:
        return spec.target.split(" ")[0]
    return spec.target


def target_citation(spec: TaskSpec) -> str | None:
    """The document id a correct submission must cite, or None."""
    if spec.requires_citation and spec.target:
        value, _, document_id = spec.target.partition(" ")
        if not value or not document_id or " " in document_id:
            raise ValueError(f"{spec.id}: target must be '<value> <document id>'")
        return document_id
    return None


def grade(spec: TaskSpec, submission: Mapping[str, object]) -> bool:
    """True when the submission is correct for the task."""
    status = submission["status"]
    answer = submission["answer"]
    citations = submission["citations"]
    if not isinstance(answer, str):
        raise TypeError("submission['answer'] must be a string")
    if isinstance(citations, str):
        # A bare string would turn the membership test below into a substring test.
        raise TypeError("submission['citations'] must be a sequence of strings, not a string")

    if status != spec.expected_status:
        return False
    if spec.expected_status != "answered":
        return True

    value = target_value(spec)
    if spec.tolerance is not None:
        submitted = first_number(answer)
        if submitted is None:
            return False
        if abs(submitted - Decimal(value)) > Decimal(str(spec.tolerance)):
            return False
    elif value not in _TOKEN.findall(answer):
        return False

    document_id = target_citation(spec)
    if document_id is not None and document_id not in tuple(citations):
        return False
    return True
