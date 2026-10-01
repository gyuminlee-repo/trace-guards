# Run summary (preliminary)

**Preliminary.** Few tasks and few epochs; the intervals are wide and the task-level bootstrap is coarse. Every rate is shown as count / denominator.

- commit: `b02c8842e5d3eed6618cbd3b9ff462fdebda9206` (working tree clean: True)
- models: ollama/tg-qwen3.5-9b-ctx16k
- context length (tokens): ollama/tg-qwen3.5-9b-ctx16k 16384
- epochs: 5; temperature: 0.7; task seed: 0; message limit: 30
- tasks (3): seq_gc, lit_lookup, trap_alias
- conditions: gate_off, gate_on
- inspect_ai 0.3.273; started 2026-10-01T12:30:54+00:00
- logs read: 6; runs: 30

## Definitions

- confident_wrong: the accepted submission has status `answered` or `absent` and is graded incorrect.
- abstained: the accepted submission has status `cannot_determine`. wrong_abstention: abstained on a task whose expected status is not `cannot_determine`.
- A run without an accepted submission is graded incorrect and is counted under no_accepted_submission only, not under confident_wrong or abstained.
- first_unsupported: the scanner (the same guards as the gate) has at least one finding on the first submit call. final_unsupported: the same on the accepted submission.
- `total_tokens` is the Inspect `total_tokens` of the run, summed over every model call of the run. In the Ollama logs checked so far it equals input_tokens + output_tokens + input_tokens_cache_read; `input_tokens` counts only the prompt tokens that were not read from the prompt cache, so it is far smaller than the prompt that the model saw.
- max_prompt_tokens: the largest prompt of any model call of the run (input_tokens + input_tokens_cache_read of that call). context_risk: that value is at least 9/10 of the context length of the model, so an early message may have been cut.
- wall_seconds is the Inspect `total_time` of the sample; samples ran one at a time.

## ollama/tg-qwen3.5-9b-ctx16k, gate_off

| metric | count / denominator | rate | Wilson 95% | denominator is |
|---|---|---|---|---|
| correct | 9 / 15 | 0.6000 | 0.3575 to 0.8018 | all runs |
| confident_wrong | 6 / 15 | 0.4000 | 0.1982 to 0.6425 | all runs |
| no_accepted_submission | 0 / 15 | 0.0000 | 0.0000 to 0.2039 | all runs |
| abstained | 0 / 15 | 0.0000 | 0.0000 to 0.2039 | all runs |
| abstained_where_expected | 0 / 0 | n/a | n/a | runs of tasks whose expected status is cannot_determine |
| wrong_abstention | 0 / 15 | 0.0000 | 0.0000 to 0.2039 | runs of tasks whose expected status is not cannot_determine |
| first_unsupported | 6 / 15 | 0.4000 | 0.1982 to 0.6425 | runs with at least one submit call |
| final_unsupported | 6 / 15 | 0.4000 | 0.1982 to 0.6425 | runs with an accepted submission |
| gate_exhausted | 0 / 15 | 0.0000 | 0.0000 to 0.2039 | all runs |
| context_risk | 0 / 15 | 0.0000 | 0.0000 to 0.2039 | runs with a model call that reported usage |
| rejected_at_least_once | 0 / 15 | 0.0000 | 0.0000 to 0.2039 | all runs |

| per run | n runs | median | mean | max |
|---|---|---|---|---|
| n_rejections | 15 | 0.0000 | 0.0000 | 0 |
| input_tokens | 15 | 178.0000 | 384.5333 | 1484 |
| output_tokens | 15 | 364.0000 | 468.9333 | 1111 |
| total_tokens | 15 | 3510.0000 | 3431.9333 | 6939 |
| max_prompt_tokens | 15 | 1246.0000 | 1367.2667 | 2943 |
| wall_seconds | 15 | 4.5570 | 8.5586 | 47.2150 |

## ollama/tg-qwen3.5-9b-ctx16k, gate_on

| metric | count / denominator | rate | Wilson 95% | denominator is |
|---|---|---|---|---|
| correct | 10 / 15 | 0.6667 | 0.4171 to 0.8482 | all runs |
| confident_wrong | 5 / 15 | 0.3333 | 0.1518 to 0.5829 | all runs |
| no_accepted_submission | 0 / 15 | 0.0000 | 0.0000 to 0.2039 | all runs |
| abstained | 0 / 15 | 0.0000 | 0.0000 to 0.2039 | all runs |
| abstained_where_expected | 0 / 0 | n/a | n/a | runs of tasks whose expected status is cannot_determine |
| wrong_abstention | 0 / 15 | 0.0000 | 0.0000 to 0.2039 | runs of tasks whose expected status is not cannot_determine |
| first_unsupported | 5 / 15 | 0.3333 | 0.1518 to 0.5829 | runs with at least one submit call |
| final_unsupported | 0 / 15 | 0.0000 | 0.0000 to 0.2039 | runs with an accepted submission |
| gate_exhausted | 0 / 15 | 0.0000 | 0.0000 to 0.2039 | all runs |
| context_risk | 0 / 15 | 0.0000 | 0.0000 to 0.2039 | runs with a model call that reported usage |
| rejected_at_least_once | 5 / 15 | 0.3333 | 0.1518 to 0.5829 | all runs |

| per run | n runs | median | mean | max |
|---|---|---|---|---|
| n_rejections | 15 | 0.0000 | 0.3333 | 1 |
| input_tokens | 15 | 178.0000 | 518.3333 | 1860 |
| output_tokens | 15 | 615.0000 | 831.1333 | 2587 |
| total_tokens | 15 | 3577.0000 | 6900.8000 | 20514 |
| max_prompt_tokens | 15 | 1370.0000 | 2003.0667 | 5154 |
| wall_seconds | 15 | 7.0900 | 10.2553 | 32.6450 |

## Paired comparison of confident_wrong (gate_on minus gate_off)

Pairs are matched by (model, task, epoch). A run without an accepted submission enters its pair with confident_wrong 0.

- ollama/tg-qwen3.5-9b-ctx16k: sum of differences -1 over 15 pairs, mean -0.0667; pairs over 3 tasks; too few tasks, no interval given.

## Per task

| model | task | condition | runs | correct | confident_wrong | no accepted submission |
|---|---|---|---|---|---|---|
| ollama/tg-qwen3.5-9b-ctx16k | lit_lookup | gate_off | 5 | 5 | 0 | 0 |
| ollama/tg-qwen3.5-9b-ctx16k | lit_lookup | gate_on | 5 | 5 | 0 | 0 |
| ollama/tg-qwen3.5-9b-ctx16k | seq_gc | gate_off | 5 | 4 | 1 | 0 |
| ollama/tg-qwen3.5-9b-ctx16k | seq_gc | gate_on | 5 | 5 | 0 | 0 |
| ollama/tg-qwen3.5-9b-ctx16k | trap_alias | gate_off | 5 | 0 | 5 | 0 |
| ollama/tg-qwen3.5-9b-ctx16k | trap_alias | gate_on | 5 | 0 | 5 | 0 |

## Runs without an accepted submission or with an error

None (0 of 30 runs).
