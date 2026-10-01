"""GC fraction of a multi-record FASTA with soft-masked (lower-case) runs and N runs."""

from __future__ import annotations

from trace_guards.tasks.generators._common import ABSTAIN, ensure_distinct, rng_for
from trace_guards.tasks.spec import TaskSpec

TASK_ID = "seq_gc"
FILE = "genome.fasta"
TOLERANCE = 0.0005

PROMPT = (
    f"The file `{FILE}` contains several sequence records. Compute the overall GC "
    "fraction across all records: the number of G and C bases divided by the number "
    "of A, C, G and T bases. Count bases case-insensitively and leave N out of the "
    "denominator. Report the fraction rounded to 4 decimal places. " + ABSTAIN
)


def _generate(seed: int) -> tuple[TaskSpec, dict[str, str]]:
    rng = rng_for(TASK_ID, seed)
    gc = acgt = n_count = upper_gc = upper_acgt = total = 0
    lines: list[str] = []
    for record in range(1, 5):
        length = rng.randint(400, 900)
        # Every record opens with one run of each kind so all three always occur.
        kinds = ["upper", "lower", "n"]
        sequence: list[str] = []
        while len(sequence) < length:
            kind = kinds.pop(0) if kinds else rng.choices(("upper", "lower", "n"), (6, 3, 1))[0]
            if kind == "n":
                run = rng.randint(5, 20)
                sequence.extend("N" * run)
                n_count += run
                total += run
                continue
            # Masked runs are AT-rich so that ignoring them shifts the fraction.
            p_gc = 0.64 if kind == "upper" else 0.34
            for _ in range(rng.randint(20, 80)):
                is_gc = rng.random() < p_gc
                base = rng.choice("GC") if is_gc else rng.choice("AT")
                acgt += 1
                total += 1
                gc += is_gc
                if kind == "upper":
                    upper_acgt += 1
                    upper_gc += is_gc
                else:
                    base = base.lower()
                sequence.append(base)
        text = "".join(sequence)
        lines.append(f">record_{record} synthetic sequence")
        lines.extend(text[i : i + 60] for i in range(0, len(text), 60))

    spec = TaskSpec(
        id=TASK_ID,
        family="sequence",
        kind="ordinary",
        trap=None,
        prompt=PROMPT,
        files={FILE: "\n".join(lines) + "\n"},
        expected_status="answered",
        target=f"{gc / acgt:.4f}",
        tolerance=TOLERANCE,
        requires_citation=False,
        tools=("python",),
    )
    wrong = {
        "uppercase_only": f"{upper_gc / upper_acgt:.4f}",
        "n_in_denominator": f"{gc / (acgt + n_count):.4f}",
        "uppercase_gc_over_length": f"{upper_gc / total:.4f}",
    }
    ensure_distinct(spec, wrong)
    return spec, wrong


def build(seed: int) -> TaskSpec:
    return _generate(seed)[0]


def distractors(seed: int) -> dict[str, str]:
    return _generate(seed)[1]
