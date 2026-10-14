# trace-guards

Deterministic evidence checks over the execution trace of an LLM agent, measured on small science tasks with a local open-weight model.

The question: when an agent submits an answer to a science task, is that answer backed by what the agent actually ran, and does rejecting unbacked submissions make the agent wrong less often?

## What is here

| Part | Where | What it does |
|---|---|---|
| Trace model | `src/trace_guards/trace.py` | Framework-neutral record of one run: prompt, tool events, structured submission |
| Guards | `src/trace_guards/guards/` | Five pure functions with no model call: value evidence, citation in trace, absence control, artifact and failure (v0), and silent discard (v1, opt-in) |
| Inspect adapter | `src/trace_guards/inspect_adapter.py` | Recorded tools, a structured `submit`, and a gated `submit` that rejects when a guard fires |
| Tasks | `src/trace_guards/tasks/` | Ten generated v0 tasks in microbial genomics, transcriptomics and literature lookup, four of them traps where the honest answer is "cannot determine" or where a naive lookup misleads; plus four fixed v1 tasks (three corrupted-input holdouts and one benign control) |
| Experiment | `src/trace_guards/experiment/` | Runner and aggregation: per-run rows, Wilson intervals, task-level paired bootstrap, context-length check |
| Design | `docs/DESIGN.md`, `docs/DESIGN_v1.md` | Written and frozen before the code of each version. Change log records every revision and why |
| Reports | `reports/` | Pilot runs on development tasks, the v0 run, and the v1 run |

The same guard functions are used two ways. As a **scanner** they label a finished run. As a **gate** they sit inside the submit tool and reject a submission that lacks evidence, so the agent continues working.

## v0 outcome in short

qwen3.5 9b through Ollama, 10 tasks x 5 epochs x 2 conditions = 100 runs, guards frozen beforehand. Full account in `reports/v0_full/FINDINGS.md`.

- The gate did not reduce confident wrong submissions: 11 of 50 runs with the gate off, 9 of 50 with it on, and neither of the two differing pairs was the gate correcting an answer.
- The gate fired in 6 of 50 runs. On the trap where a zero-hit search suggests a gene is absent, all 5 runs were rejected; 4 found a way to satisfy the control and submitted the same wrong answer, at about seven times the tokens.
- On the seven tasks held out until the guards were frozen, confident wrong submissions were 5 of 35 in both conditions and no guard fired on any of them.
- Used as a scanner, the guards flagged 5 of the 11 confident wrong submissions and none of the 35 correct ones, but all five flags fall on one development task.
- The larger share of confident wrong submissions (6 of 11) were wrong computations whose value did appear in tool output. An evidence check cannot see those.

These are preliminary values from one model and ten tasks.

## How this relates to earlier work

That an evidence gate can reduce false completion has been reported before, in coding and ML research settings (arXiv 2609.20812, 2511.05524, 2607.14890; preprints, not peer reviewed as of 2026-10-01). This repository does not claim that finding. Its scope is narrower: science tasks with known answers, checks that need no model call, and a local open-weight model with token and time cost measured. See `docs/DESIGN.md` section 2.

## Run it

The opt-in silent-discard v1 experiment is preregistered in
[`docs/DESIGN_v1.md`](docs/DESIGN_v1.md). G5 adds a conservative Python AST
check for explicit discard operations. v0 remains the default. The three new
corrupted tasks and separate benign control are fixed after the guard lock.
See [`docs/V1_RUNBOOK.md`](docs/V1_RUNBOOK.md) for clean-checkout validation and
the parent-owned paired Ollama commands. The v1 run is reported in
[`reports/v1_full/FINDINGS.md`](reports/v1_full/FINDINGS.md): the agent made no
confident wrong submission on the new corrupted tasks with the gate off (0 of
15), so G5 had nothing to prevent. G5 rejected three runs whose first submission
already held the correct answer: one on a corrupted task and two on the
benign control.

Requirements: Python 3.11 or later, [Inspect AI](https://github.com/UKGovernmentBEIS/inspect_ai), and an Ollama server with a tool-calling model.

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[inspect,dev]"
.venv/bin/python -m pytest -q

# a model variant with a larger context (the Ollama default of 4,096 tokens is too small)
printf 'FROM qwen3.5:9b\nPARAMETER num_ctx 16384\n' > Modelfile
ollama create tg-qwen3.5-9b-ctx16k -f Modelfile

.venv/bin/python -m trace_guards.experiment.run --tasks dev --epochs 2 --out runs/try
.venv/bin/python -m trace_guards.experiment.aggregate runs/try
```

The runner refuses to start from a dirty working tree, so that the recorded commit describes the code that ran.

## Rules this project holds itself to

- Each guard has a labelled corpus of firing and non-firing cases, written and committed before the guard.
- Every task target is computed by its generator and checked by a second computation that shares no code with it. This rule exists because the first hand-typed target in this project was wrong.
- Tasks are split into development and held-out sets. Guards are frozen before held-out tasks are run.
- Every reported rate names its denominator. An empty input to a checker is a failure, not a pass.
- A rejection message never contains the answer or a hint toward it.

## Limits

Ten tasks, generated data, one small local model, one task seed. Local sandbox without container isolation. Guards catch missing evidence; they do not catch a wrong computation that carries evidence. Every confident wrong submission on the held-out tasks was of that kind: the agent dropped the unparsable rows of a table, counted the rest, and the count it submitted was in its own tool output.

## Provenance

Guards and tasks are written for this repository. The evaluation framework is Inspect AI (MIT). No code is copied from other projects.
