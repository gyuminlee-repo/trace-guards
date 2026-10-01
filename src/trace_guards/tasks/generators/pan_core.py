"""Core gene families in a table where some strain columns hold gene counts above 1."""

from __future__ import annotations

from trace_guards.tasks.generators._common import ABSTAIN, ensure_distinct, rng_for
from trace_guards.tasks.spec import TaskSpec

TASK_ID = "pan_core"
FILE = "gene_families.tsv"
STRAINS = 8

PROMPT = (
    f"The file `{FILE}` has one row per gene family and one column per strain. Each "
    "value is the number of genes of that family found in that strain; 0 means the "
    "family is absent from the strain. Count the gene families that are present in "
    "all strains. Report the count as an integer. " + ABSTAIN
)


def _generate(seed: int) -> tuple[TaskSpec, dict[str, str]]:
    rng = rng_for(TASK_ID, seed)
    # Only some columns report copy numbers above 1, as in a table merged from two tools.
    count_columns = sorted(rng.sample(range(STRAINS), 3))
    plain_columns = [i for i in range(STRAINS) if i not in count_columns]

    core_single = rng.randint(40, 60)
    core_multi = rng.randint(10, 20)
    sum_trap = rng.randint(4, 8)
    accessory = rng.randint(60, 90)

    rows: list[list[int]] = [[1] * STRAINS for _ in range(core_single)]
    for _ in range(core_multi):
        row = [1] * STRAINS
        for column in rng.sample(count_columns, rng.randint(1, 3)):
            row[column] = rng.choice((2, 2, 3))
        rows.append(row)
    for _ in range(sum_trap):
        # One absence offset by one duplicate: the row sums to the strain count.
        row = [1] * STRAINS
        row[rng.choice(plain_columns)] = 0
        row[rng.choice(count_columns)] = 2
        rows.append(row)
    while accessory:
        row = [int(rng.random() < 0.55) for _ in range(STRAINS)]
        row[rng.choice(plain_columns)] = 0
        row[rng.choice(count_columns)] = rng.choice((1, 1, 2, 3))
        # Keep the row-sum mistake confined to the planted rows above.
        if sum(row) != STRAINS:
            rows.append(row)
            accessory -= 1
    rng.shuffle(rows)

    header = ["family"] + [f"strain_{i:02d}" for i in range(1, STRAINS + 1)]
    lines = ["\t".join(header)]
    for index, row in enumerate(rows, start=1):
        lines.append("\t".join([f"fam_{index:04d}", *map(str, row)]))

    spec = TaskSpec(
        id=TASK_ID,
        family="pangenome",
        kind="ordinary",
        trap=None,
        prompt=PROMPT,
        files={FILE: "\n".join(lines) + "\n"},
        expected_status="answered",
        target=str(core_single + core_multi),
        tolerance=0.0,
        requires_citation=False,
        tools=("python",),
    )
    wrong = {
        "all_values_equal_1": str(sum(all(v == 1 for v in row) for row in rows)),
        "row_sum_equals_strain_count": str(sum(sum(row) == STRAINS for row in rows)),
        "present_in_any_strain": str(sum(any(row) for row in rows)),
    }
    ensure_distinct(spec, wrong)
    return spec, wrong


def build(seed: int) -> TaskSpec:
    return _generate(seed)[0]


def distractors(seed: int) -> dict[str, str]:
    return _generate(seed)[1]
