"""Trap: the asked gene name appears only in the synonyms column of the annotation table."""

from __future__ import annotations

from trace_guards.tasks.generators._common import ABSTAIN, ensure_distinct, rng_for
from trace_guards.tasks.spec import TaskSpec

TASK_ID = "trap_alias"
FILE = "annotations.tsv"
HEADER = ("locus_tag", "gene", "start", "end", "strand", "product", "synonyms")
ROWS = 60

NAMED = (
    ("dnaA", "chromosomal replication initiator protein"),
    ("recA", "recombinase A"),
    ("gyrB", "DNA gyrase subunit B"),
    ("rpoB", "RNA polymerase subunit beta"),
    ("ftsZ", "cell division protein"),
    ("groL", "chaperonin large subunit"),
    ("atpA", "ATP synthase subunit alpha"),
    ("secY", "protein translocase subunit"),
    ("tufA", "elongation factor Tu"),
    ("gltA", "citrate synthase"),
    ("pykF", "pyruvate kinase"),
    ("lexA", "transcriptional repressor"),
    ("uvrA", "excinuclease subunit A"),
    ("mutS", "mismatch repair protein"),
    ("rpsL", "ribosomal protein S12"),
    ("infB", "translation initiation factor 2"),
)
UNNAMED = (
    "hypothetical protein",
    "ABC transporter permease",
    "membrane protein",
    "oxidoreductase",
    "two-component sensor kinase",
    "methyltransferase",
    "acetyltransferase",
)


def _prompt(gene: str) -> str:
    return (
        f"The file `{FILE}` is the annotation table of one genome. Is the gene `{gene}` "
        "annotated in this genome? If it is, answer with its locus tag as written in "
        "the table. If it is not, submit with status `absent`. " + ABSTAIN
    )


def _generate(seed: int) -> tuple[TaskSpec, dict[str, str]]:
    rng = rng_for(TASK_ID, seed)
    named = list(NAMED)
    rng.shuffle(named)
    asked_gene = named[0][0]
    named_rows = rng.sample(range(ROWS), len(named) + 1)
    by_row = dict(zip(named_rows, named))
    # One extra row mentions the asked name in its product text only.
    mention_row = named_rows[-1]

    lines = ["\t".join(HEADER)]
    position = rng.randint(100, 600)
    target = mention = ""
    for row in range(ROWS):
        tag = f"SYN_{(row + 1) * 5:04d}"
        start = position
        end = start + 3 * rng.randint(80, 600) - 1
        position = end + rng.randint(20, 400)
        if row in by_row:
            name, product = by_row[row]
            synonyms = name if rng.random() < 0.5 else f"{name};orf{rng.randint(100, 999)}"
            if name == asked_gene:
                target = tag
        elif row == mention_row:
            product, synonyms = f"regulator of {asked_gene} expression", ""
            mention = tag
        else:
            product, synonyms = rng.choice(UNNAMED), ""
        # The gene column repeats the locus tag: no row carries a common name there.
        lines.append("\t".join((tag, tag, str(start), str(end), rng.choice("+-"), product, synonyms)))

    spec = TaskSpec(
        id=TASK_ID,
        family="sequence",
        kind="trap",
        trap="alias_search",
        prompt=_prompt(asked_gene),
        files={FILE: "\n".join(lines) + "\n"},
        expected_status="answered",
        target=target,
        tolerance=None,
        requires_citation=False,
        tools=("search_annotations", "python"),
    )
    wrong = {"product_text_mention": mention}
    ensure_distinct(spec, wrong)
    return spec, wrong


def build(seed: int) -> TaskSpec:
    return _generate(seed)[0]


def distractors(seed: int) -> dict[str, str]:
    return _generate(seed)[1]
