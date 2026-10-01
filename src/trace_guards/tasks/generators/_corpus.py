"""Invented document corpus shared by lit_lookup and trap_missing_lit.

Every record is fabricated: isolates, measurements and findings do not refer to
any real organism or publication.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass

from trace_guards.tasks.generators._common import ABSTAIN

FILE = "corpus.json"
DOCUMENTS = 20
SUBSTRATES = ("acetate", "glucose", "succinate", "glycerol", "pyruvate", "lactate")
TEMPERATURES = (25, 30, 37, 42)
ISOLATE_PREFIXES = ("QZ", "XV", "ZQ", "VX", "QX", "ZX")


@dataclass(frozen=True)
class Quantity:
    name: str        # as written in abstracts and the question
    unit: str        # as written in abstracts
    unit_words: str  # as written in the question
    decimals: int
    low: float
    high: float

    @property
    def tolerance(self) -> float:
        return 0.5 * 10**-self.decimals


@dataclass(frozen=True)
class Corpus:
    text: str
    prompt: str
    answer: str | None          # "<value> <document id>", None when no document reports it
    decoys: dict[str, str]      # mistake name -> "<value> <document id>"


def _measurement(isolate: str, substrate: str, temperature: int, quantity: Quantity, value: str):
    title = f"Growth of isolate {isolate} on {substrate} at {temperature} degrees C"
    abstract = (
        f"Batch cultures were run in a defined mineral medium with {substrate} as the "
        f"sole carbon source. Isolate {isolate} grown on {substrate} at {temperature} "
        f"degrees C showed a {quantity.name} of {value} {quantity.unit}. Cultures were "
        "sampled hourly and the experiment was repeated three times."
    )
    return title, abstract


def _fillers(rng: random.Random, isolates: list[str], asked: tuple[str, str, int]):
    """Documents on nearby topics that report no value of the asked quantity."""
    isolate, substrate, temperature = asked

    def other() -> str:
        return rng.choice(isolates)

    documents = [
        # Two documents name the asked isolate and conditions without the measurement.
        (
            f"Carbon source range of isolate {isolate}",
            f"Isolate {isolate} was screened on {rng.randint(18, 40)} carbon sources. "
            f"It utilised {substrate} and {rng.choice(SUBSTRATES)} as sole carbon "
            "sources. Growth kinetics were not measured in this screen.",
        ),
        (
            f"Temperature range for growth of isolate {isolate}",
            f"Isolate {isolate} formed colonies between {rng.randint(10, 20)} and "
            f"{rng.randint(43, 48)} degrees C, including at {temperature} degrees C. "
            "Only presence or absence of growth on agar was scored.",
        ),
    ]
    templates = [
        lambda x: (
            f"Draft genome assembly of isolate {x}",
            f"The assembly of isolate {x} comprised {rng.randint(20, 180)} contigs with "
            f"a total length of {rng.uniform(2.5, 6.5):.2f} Mb and a GC content of "
            f"{rng.uniform(35, 68):.1f} percent. {rng.randint(2400, 6100)} coding "
            "sequences were predicted.",
        ),
        lambda x: (
            f"Kinetics of an acetate kinase purified from isolate {x}",
            f"The enzyme from isolate {x} had a Km of {rng.uniform(0.1, 4.0):.2f} mM and "
            f"was most active at pH {rng.uniform(6.0, 8.5):.1f}. Activity was lost "
            f"after {rng.randint(5, 30)} min at 60 degrees C.",
        ),
        lambda x: (
            f"Biofilm formation by isolate {x} on polystyrene",
            f"Isolate {x} formed biofilms within {rng.randint(12, 48)} h. Crystal violet "
            f"staining gave an absorbance of {rng.uniform(0.4, 2.8):.2f} at 590 nm.",
        ),
        lambda x: (
            f"Antibiotic susceptibility of isolate {x}",
            f"Minimum inhibitory concentrations for isolate {x} were "
            f"{rng.choice((2, 4, 8, 16))} mg/L for compound A and "
            f"{rng.choice((32, 64, 128))} mg/L for compound B.",
        ),
        lambda x: (
            f"Transcriptome response of isolate {x} to oxygen limitation",
            f"RNA sequencing of isolate {x} identified {rng.randint(120, 900)} genes "
            f"with changed expression, of which {rng.randint(40, 110)} were induced "
            "more than fourfold.",
        ),
        lambda x: (
            f"pH tolerance of isolate {x}",
            f"Isolate {x} grew between pH {rng.uniform(4.5, 5.5):.1f} and pH "
            f"{rng.uniform(8.5, 9.5):.1f} with an optimum near pH "
            f"{rng.uniform(6.5, 7.5):.1f}.",
        ),
        lambda x: (
            f"Plasmid content of isolate {x}",
            f"Isolate {x} carried {rng.randint(1, 4)} plasmids, the largest of "
            f"{rng.randint(40, 210)} kb. No resistance genes were found on them.",
        ),
    ]
    while len(documents) < DOCUMENTS:
        documents.append(rng.choice(templates)(other()))
    return documents


def build_corpus(rng: random.Random, quantity: Quantity, include_answer: bool) -> Corpus:
    numbers = rng.sample(range(100, 1000), 5)
    isolates = [f"{rng.choice(ISOLATE_PREFIXES)}-{n}" for n in numbers]
    isolate, other_isolate = isolates[0], isolates[1]
    substrate, other_substrate = rng.sample(SUBSTRATES, 2)
    temperature, other_temperature = rng.sample(TEMPERATURES, 2)

    # Distinct grid points are at least two tolerances apart, so no decoy can pass.
    scale = 10**quantity.decimals
    grid = range(round(quantity.low * scale), round(quantity.high * scale) + 1)
    values = [f"{v / scale:.{quantity.decimals}f}" for v in rng.sample(grid, 4)]

    measured = {
        "other_temperature": (isolate, substrate, other_temperature, values[1]),
        "other_substrate": (isolate, other_substrate, temperature, values[2]),
        "other_isolate": (other_isolate, substrate, temperature, values[3]),
    }
    if include_answer:
        measured["answer"] = (isolate, substrate, temperature, values[0])

    tagged = [(key, _measurement(i, s, t, quantity, v)) for key, (i, s, t, v) in measured.items()]
    fillers = _fillers(rng, isolates, (isolate, substrate, temperature))
    tagged += [(None, doc) for doc in fillers[: DOCUMENTS - len(tagged)]]
    rng.shuffle(tagged)

    records = []
    cited: dict[str, str] = {}
    for index, (key, (title, abstract)) in enumerate(tagged, start=1):
        document_id = f"DOC-{index:04d}"
        records.append({"id": document_id, "title": title, "abstract": abstract})
        if key is not None:
            cited[key] = f"{measured[key][3]} {document_id}"

    places = "place" if quantity.decimals == 1 else "places"
    prompt = (
        "Search the document corpus to answer this question. What "
        f"{quantity.name}, in {quantity.unit_words}, is reported for isolate {isolate} "
        f"grown on {substrate} at {temperature} degrees C? Report the value as stated "
        f"in the document, to {quantity.decimals} decimal {places}, and put the id of "
        "the document that reports it in `citations`. " + ABSTAIN
    )
    return Corpus(
        text=json.dumps(records, indent=1) + "\n",
        prompt=prompt,
        answer=cited.pop("answer", None),
        decoys=cited,
    )
