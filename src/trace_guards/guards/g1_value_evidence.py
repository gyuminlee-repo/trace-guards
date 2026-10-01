"""G1 value_evidence: every submitted value must be backed by a clean tool output."""

from __future__ import annotations

import re
from decimal import ROUND_HALF_UP, Decimal

from ..trace import Finding, Submission, Trace

GUARD = "value_evidence"

# A number is a token of its own: not glued to a letter, digit, underscore or
# another dotted group, so 16 is not found in 2016, 1.16, 16S or 1.16.2.
# A minus sign counts only when it does not follow a token (3-5 is a range).
_NUMBER = re.compile(
    r"(?<![\w.])-?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?(?:[eE][-+]?\d+)?(?!\w)(?!\.\d)"
)

_MSG_NUMBER = (
    "value_evidence: a number in the answer is not printed by any tool call of "
    "this run that finished without error. Compute it with a tool and submit "
    "the value as the tool printed it, or submit status cannot_determine."
)
_MSG_TEXT = (
    "value_evidence: the answer does not occur as a whole token in any tool "
    "output of this run that finished without error. Look it up with a tool "
    "first, or submit status cannot_determine."
)


def extract_numbers(text: str) -> list[Decimal]:
    return [Decimal(m.group().replace(",", "")) for m in _NUMBER.finditer(text)]


def supports(evidence: Decimal, submitted: Decimal) -> bool:
    exponent = submitted.as_tuple().exponent
    if exponent >= 0:
        return evidence == submitted
    quantum = Decimal(1).scaleb(exponent)
    return evidence.quantize(quantum, rounding=ROUND_HALF_UP) == submitted


def _has_token(text: str, token: str) -> bool:
    return re.search(rf"(?<!\w){re.escape(token)}(?!\w)", text) is not None


def check(
    trace: Trace, submission: Submission, *, requires_citation: bool = False
) -> list[Finding]:
    if submission.status != "answered":
        return []
    outputs = [e.output for e in trace.events if not e.error]
    submitted = extract_numbers(submission.answer)

    if not submitted:
        answer = submission.answer.strip()
        found = bool(answer) and any(
            _has_token(text, answer) for text in [trace.prompt, *outputs]
        )
        if found:
            return []
        return [Finding(GUARD, _MSG_TEXT, {"answer": answer})]

    prompt_numbers = extract_numbers(trace.prompt)
    evidence = [n for text in outputs for n in extract_numbers(text)]
    unsupported = [
        str(s)
        for s in submitted
        if s not in prompt_numbers and not any(supports(t, s) for t in evidence)
    ]
    if not unsupported:
        return []
    return [Finding(GUARD, _MSG_NUMBER, {"unsupported": unsupported})]
