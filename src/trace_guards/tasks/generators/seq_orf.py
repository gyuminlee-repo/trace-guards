"""Longest forward-strand ORF of one record; a longer ORF sits on the reverse strand."""

from __future__ import annotations

import random

from trace_guards.tasks.generators._common import ABSTAIN, ensure_distinct, rng_for
from trace_guards.tasks.spec import TaskSpec

TASK_ID = "seq_orf"
FILE = "contigs.fasta"

STOPS = ("TAA", "TAG", "TGA")
SENSE = tuple(a + b + c for a in "ACGT" for b in "ACGT" for c in "ACGT" if a + b + c not in STOPS)
COMPLEMENT = str.maketrans("ACGT", "TGCA")


def _prompt(record: str) -> str:
    return (
        f"The file `{FILE}` contains several DNA records. For the record `{record}`, "
        "find the longest open reading frame (ORF) on the forward strand, that is the "
        "sequence as written, in any of its three reading frames. An ORF starts at an "
        "ATG codon and ends at the first in-frame stop codon (TAA, TAG or TGA); a "
        "stretch that reaches the end of the record without a stop codon is not an ORF. "
        "Report the length in codons as an integer, counting the start codon and not "
        "counting the stop codon. " + ABSTAIN
    )


def _orf(rng: random.Random, codons: int) -> str:
    body = "".join(rng.choice(SENSE) for _ in range(codons - 1))
    return "ATG" + body + rng.choice(STOPS)


def _background(rng: random.Random, length: int) -> str:
    return "".join(rng.choice("ACGT") for _ in range(length))


def _reverse_complement(sequence: str) -> str:
    return sequence.translate(COMPLEMENT)[::-1]


def _longest_orf(sequence: str) -> int:
    best = 0
    for frame in range(3):
        start = None
        for i in range(frame, len(sequence) - 2, 3):
            codon = sequence[i : i + 3]
            if start is None:
                if codon == "ATG":
                    start = i
            elif codon in STOPS:
                best = max(best, (i - start) // 3)
                start = None
    return best


def _generate(seed: int) -> tuple[TaskSpec, dict[str, str]]:
    rng = rng_for(TASK_ID, seed)
    forward = rng.randint(110, 160)
    reverse = forward + rng.randint(60, 110)
    asked = (
        _background(rng, rng.randint(90, 150))
        + _orf(rng, forward)
        + _background(rng, rng.randint(90, 150))
        + _reverse_complement(_orf(rng, reverse))
        + _background(rng, rng.randint(90, 150))
    )
    # Another record carries a longer forward ORF: reading the wrong record is a distractor.
    longer = (
        _background(rng, rng.randint(90, 150))
        + _orf(rng, reverse + rng.randint(20, 60))
        + _background(rng, rng.randint(90, 150))
    )
    short = _background(rng, rng.randint(500, 800))

    sequences = [asked, longer, short]
    rng.shuffle(sequences)
    names = [f"contig_{i}" for i in range(1, len(sequences) + 1)]
    asked_name = names[sequences.index(asked)]
    lines: list[str] = []
    for name, sequence in zip(names, sequences):
        lines.append(f">{name} synthetic sequence")
        lines.extend(sequence[i : i + 60] for i in range(0, len(sequence), 60))

    target = _longest_orf(asked)
    spec = TaskSpec(
        id=TASK_ID,
        family="sequence",
        kind="ordinary",
        trap=None,
        prompt=_prompt(asked_name),
        files={FILE: "\n".join(lines) + "\n"},
        expected_status="answered",
        target=str(target),
        tolerance=0.0,
        requires_citation=False,
        tools=("python",),
    )
    wrong = {
        "both_strands": str(max(target, _longest_orf(_reverse_complement(asked)))),
        "any_record": str(max(_longest_orf(s) for s in sequences)),
        "stop_codon_counted": str(target + 1),
        "length_in_nucleotides": str(3 * target),
    }
    ensure_distinct(spec, wrong)
    return spec, wrong


def build(seed: int) -> TaskSpec:
    return _generate(seed)[0]


def distractors(seed: int) -> dict[str, str]:
    return _generate(seed)[1]
