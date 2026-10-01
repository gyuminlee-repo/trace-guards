# Run summary (preliminary)

**Preliminary.** Few tasks and few epochs; the intervals are wide and the task-level bootstrap is coarse. Every rate is shown as count / denominator.

- commit: `e24314578d30db4b4d938b70d06bcc513f5ecba1` (working tree clean: True)
- models: ollama/qwen3.5:9b
- epochs: 2; temperature: 0.7; task seed: 0; message limit: 30
- tasks (3): seq_gc, lit_lookup, trap_alias
- conditions: gate_off, gate_on
- inspect_ai 0.3.273; started 2026-10-01T12:18:09+00:00
- logs read: 6; runs: 12

## Definitions

- confident_wrong: the accepted submission has status `answered` or `absent` and is graded incorrect.
- abstained: the accepted submission has status `cannot_determine`. wrong_abstention: abstained on a task whose expected status is not `cannot_determine`.
- A run without an accepted submission is graded incorrect and is counted under no_accepted_submission only, not under confident_wrong or abstained.
- first_unsupported: the scanner (the same guards as the gate) has at least one finding on the first submit call. final_unsupported: the same on the accepted submission.
- `total_tokens` is the Inspect `total_tokens` of the run, summed over every model call of the run. With the Ollama provider it equals input_tokens + output_tokens + input_tokens_cache_read; `input_tokens` counts only the prompt tokens that were not read from the prompt cache, so it is far smaller than the prompt that the model saw.
- wall_seconds is the Inspect `total_time` of the sample; samples ran one at a time.

## ollama/qwen3.5:9b, gate_off

| metric | count / denominator | rate | Wilson 95% | denominator is |
|---|---|---|---|---|
| correct | 2 / 6 | 0.3333 | 0.0968 to 0.7000 | all runs |
| confident_wrong | 4 / 6 | 0.6667 | 0.3000 to 0.9032 | all runs |
| no_accepted_submission | 0 / 6 | 0.0000 | 0.0000 to 0.3903 | all runs |
| abstained | 0 / 6 | 0.0000 | 0.0000 to 0.3903 | all runs |
| abstained_where_expected | 0 / 0 | n/a | n/a | runs of tasks whose expected status is cannot_determine |
| wrong_abstention | 0 / 6 | 0.0000 | 0.0000 to 0.3903 | runs of tasks whose expected status is not cannot_determine |
| first_unsupported | 2 / 6 | 0.3333 | 0.0968 to 0.7000 | runs with at least one submit call |
| final_unsupported | 2 / 6 | 0.3333 | 0.0968 to 0.7000 | runs with an accepted submission |
| gate_exhausted | 0 / 6 | 0.0000 | 0.0000 to 0.3903 | all runs |
| rejected_at_least_once | 0 / 6 | 0.0000 | 0.0000 to 0.3903 | all runs |

| per run | n runs | median | mean |
|---|---|---|---|
| n_rejections | 6 | 0.0000 | 0.0000 |
| input_tokens | 6 | 188.5000 | 412.8333 |
| output_tokens | 6 | 569.0000 | 602.6667 |
| total_tokens | 6 | 2969.0000 | 3516.8333 |
| wall_seconds | 6 | 6.5370 | 6.7267 |

## ollama/qwen3.5:9b, gate_on

| metric | count / denominator | rate | Wilson 95% | denominator is |
|---|---|---|---|---|
| correct | 4 / 6 | 0.6667 | 0.3000 to 0.9032 | all runs |
| confident_wrong | 2 / 6 | 0.3333 | 0.0968 to 0.7000 | all runs |
| no_accepted_submission | 0 / 6 | 0.0000 | 0.0000 to 0.3903 | all runs |
| abstained | 0 / 6 | 0.0000 | 0.0000 to 0.3903 | all runs |
| abstained_where_expected | 0 / 0 | n/a | n/a | runs of tasks whose expected status is cannot_determine |
| wrong_abstention | 0 / 6 | 0.0000 | 0.0000 to 0.3903 | runs of tasks whose expected status is not cannot_determine |
| first_unsupported | 2 / 6 | 0.3333 | 0.0968 to 0.7000 | runs with at least one submit call |
| final_unsupported | 0 / 6 | 0.0000 | 0.0000 to 0.3903 | runs with an accepted submission |
| gate_exhausted | 0 / 6 | 0.0000 | 0.0000 to 0.3903 | all runs |
| rejected_at_least_once | 2 / 6 | 0.3333 | 0.0968 to 0.7000 | all runs |

| per run | n runs | median | mean |
|---|---|---|---|
| n_rejections | 6 | 0.0000 | 0.3333 |
| input_tokens | 6 | 289.5000 | 325.3333 |
| output_tokens | 6 | 637.5000 | 854.3333 |
| total_tokens | 6 | 5296.5000 | 7154.3333 |
| wall_seconds | 6 | 7.1595 | 9.5477 |

## Paired comparison of confident_wrong (gate_on minus gate_off)

Pairs are matched by (model, task, epoch). A run without an accepted submission enters its pair with confident_wrong 0.

- ollama/qwen3.5:9b: sum of differences -2 over 6 pairs, mean -0.3333; pairs over 3 tasks; too few tasks, no interval given.

## Per task

| model | task | condition | runs | correct | confident_wrong | no accepted submission |
|---|---|---|---|---|---|---|
| ollama/qwen3.5:9b | lit_lookup | gate_off | 2 | 2 | 0 | 0 |
| ollama/qwen3.5:9b | lit_lookup | gate_on | 2 | 2 | 0 | 0 |
| ollama/qwen3.5:9b | seq_gc | gate_off | 2 | 0 | 2 | 0 |
| ollama/qwen3.5:9b | seq_gc | gate_on | 2 | 2 | 0 | 0 |
| ollama/qwen3.5:9b | trap_alias | gate_off | 2 | 0 | 2 | 0 |
| ollama/qwen3.5:9b | trap_alias | gate_on | 2 | 0 | 2 | 0 |

## Runs without an accepted submission or with an error

None (0 of 12 runs).
