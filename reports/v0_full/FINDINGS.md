# v0 findings (preliminary)

One model, ten generated tasks, five epochs per task per condition. Every number below is a count with its denominator, read from `runs.csv` in this folder. Guards were frozen at tag `guards-frozen-v0` (commit `6b90380`) before any of the seven held-out tasks was run.

## Setup

- Model: qwen3.5 9b, served by Ollama with a 16,384-token context (`ollama/tg-qwen3.5-9b-ctx16k`), temperature 0.7.
- Conditions: `gate_off` (plain submit) and `gate_on` (submit rejected when a guard fires, at most two rejections).
- 10 tasks x 5 epochs x 2 conditions = 100 runs. Message limit 30.
- A second model (gemma4 12b) was started and stopped by a wall-clock limit after 3 of its 100 runs. Run alone it produced 5,376 tokens for a one-paragraph request, so a run took minutes to tens of minutes. Its three rows remain in `runs.csv` and are not interpreted.

## Main outcome

The gate did not reduce confident wrong submissions in this setting.

| | gate_off | gate_on |
|---|---|---|
| confident wrong | 11 / 50 | 9 / 50 |
| correct | 35 / 50 | 37 / 50 |
| no accepted submission (message limit) | 4 / 50 | 4 / 50 |
| wrong abstention | 0 / 35 | 0 / 35 |

Paired by task and epoch, the difference in confident wrong is -2 over 50 pairs (task-level bootstrap 95% interval -0.10 to 0.00). Neither of the two pairs is a case of the gate correcting an answer:

- `seq_gc` epoch 2: the gate-off run computed a wrong value and the gate-on run computed the right one. No guard fired in either run.
- `trap_alias` epoch 2: the gate-on run was rejected once and then ran into the message limit, so it ended with no accepted submission instead of a wrong one.

## Against the criteria fixed in advance

`docs/DESIGN.md` section 10 named three outcomes that would count against the gate, before any run.

| Criterion | Observed | Met |
|---|---|---|
| No reduction in confident wrong rate | 11 / 50 to 9 / 50, interval -0.10 to 0.00, and neither differing pair is a correction by the gate | yes, counts against the gate |
| A rise in wrong abstention | 0 / 35 in both conditions | no |
| Token cost more than doubles | median per run 1.84 times, sum over runs 1.07 times, sum without `seq_orf` 1.41 times | no overall. On `trap_alias` alone the median is 6.9 times |

One of the three criteria is met. For this model and these tasks the gate is a candidate for removal as an automatic retry, and the guards remain useful as flags.

## What the gate did

It fired in 6 of 50 gate-on runs.

| Task | Guard | Runs rejected | After rejection |
|---|---|---|---|
| trap_alias | absence_control | 5 of 5 | 4 submitted `absent` again and were accepted, 1 hit the message limit. 0 became correct |
| expr_de_count | citation_in_trace | 1 of 5 | The agent had listed the input file name as a citation. It resubmitted without it and was correct |

On `trap_alias` four of the five rejected runs read the table, searched for a locus tag that exists, obtained a hit, and submitted the same answer again. The fifth made eight more zero-hit queries and ran into the message limit. In one of those runs the control query was the very locus tag that lists the gene as a synonym; the search returned it and the run still submitted `absent`. Median tokens for that task went from 2,106 (gate off) to 14,477 (gate on).

## What the scanner saw

Used after the fact on gate-off runs, the same guards flagged 5 of the 11 confident wrong submissions and none of the 35 correct ones. All five flags are `absence_control` on `trap_alias`.

The other 6 confident wrong submissions carried their own evidence:

- `trap_truncated`, 5 of 5 runs in each condition: the agent skipped the unparsable rows, counted the rest, and submitted that count. The number is in the tool output, so `value_evidence` passes.
- `seq_gc`, 1 run: a miscounted GC fraction that the agent code printed.

A check that asks "is there evidence for this value" cannot tell a correct computation from a wrong one. Here that was the larger share of the confident wrong submissions: 6 of 11 with the gate off and 5 of 9 with it on.

## Abstention

- `trap_no_replicates`: 5 of 5 runs in each condition submitted `cannot_determine`, which is the expected status.
- `trap_missing_lit`: 3 of 5 in each condition abstained correctly; the other 2 ran into the message limit while still searching.
- No ordinary task was abstained on (0 of 35 in each condition). The gate did not push the agent toward giving up.

## Cost

| | gate_off | gate_on |
|---|---|---|
| total tokens, sum over 50 runs | 864,629 | 922,857 |
| total tokens, median per run | 5,372.5 | 9,867.5 |
| wall time, sum over 50 runs | 1,356 s | 1,227 s |

`seq_orf` dominates both sums (median near 97k tokens per run with the gate off, 47k with it on, with no rejection in either) and that difference is run-to-run variation. Without `seq_orf` the token sums are 379,716 and 535,550. Most of that gap is `trap_alias`, where every gate-on run was rejected.

Five runs, all `seq_orf`, had a prompt above 90% of the context length (3 with the gate off, 2 with it on). Their early messages may have been cut.

## Reading

1. In this setting the agent rarely submitted a value it had not computed: 5 of 46 first submissions with the gate off were unsupported, all of them the zero-hit absence claim. The failure the gate targets was uncommon here.
2. Where the gate fired on a wrong answer, rejection did not change the answer. The agent satisfied the letter of the control and kept its answer.
3. The same guards were precise as flags: 5 flags, 5 confident wrong, 0 flags on correct runs. For this model and these tasks they are worth more as a signal for review than as an automatic retry.
4. The majority of confident wrong submissions were wrong computations with evidence attached. Catching those needs a different kind of check, such as validating the input before computing or recomputing independently.

## Limits

- One model, ten tasks, one task seed, five epochs. Intervals are wide.
- The tasks and the guards have the same author. Three tasks were used while developing guards; seven were held out until the freeze.
- Generated data. Local sandbox without container isolation.
- Token counts come from the Ollama provider through Inspect; `total_tokens` includes prompt tokens read from the cache.
