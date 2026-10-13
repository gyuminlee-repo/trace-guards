# Run summary (preliminary)

**Preliminary.** Few tasks and few epochs; the intervals are wide and the task-level bootstrap is coarse. Every rate is shown as count / denominator.

- commit: `f671a214895c06af838f8d9067b353ed13616429` (working tree clean: True)
- models: ollama/tg-qwen3.5-9b-ctx16k
- context length (tokens): ollama/tg-qwen3.5-9b-ctx16k 16384
- epochs: 5; temperature: 0.7; task seed: 0; message limit: 30
- tasks (1): v1_benign_missing
- conditions: gate_off, gate_on
- inspect_ai 0.3.273; started 2026-10-13T02:27:59+00:00
- logs read: 2; runs: 10

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
| correct | 5 / 5 | 1.0000 | 0.5655 to 1.0000 | all runs |
| confident_wrong | 0 / 5 | 0.0000 | 0.0000 to 0.4345 | all runs |
| no_accepted_submission | 0 / 5 | 0.0000 | 0.0000 to 0.4345 | all runs |
| abstained | 0 / 5 | 0.0000 | 0.0000 to 0.4345 | all runs |
| abstained_where_expected | 0 / 0 | n/a | n/a | runs of tasks whose expected status is cannot_determine |
| wrong_abstention | 0 / 5 | 0.0000 | 0.0000 to 0.4345 | runs of tasks whose expected status is not cannot_determine |
| first_unsupported | 3 / 5 | 0.6000 | 0.2307 to 0.8824 | runs with at least one submit call |
| final_unsupported | 3 / 5 | 0.6000 | 0.2307 to 0.8824 | runs with an accepted submission |
| gate_exhausted | 0 / 5 | 0.0000 | 0.0000 to 0.4345 | all runs |
| context_risk | 0 / 5 | 0.0000 | 0.0000 to 0.4345 | runs with a model call that reported usage |
| rejected_at_least_once | 0 / 5 | 0.0000 | 0.0000 to 0.4345 | all runs |

| per run | n runs | median | mean | max |
|---|---|---|---|---|
| n_rejections | 5 | 0.0000 | 0.0000 | 0 |
| input_tokens | 5 | 278.0000 | 368.0000 | 937 |
| output_tokens | 5 | 541.0000 | 534.2000 | 653 |
| total_tokens | 5 | 3751.0000 | 3712.6000 | 4073 |
| max_prompt_tokens | 5 | 1397.0000 | 1356.6000 | 1472 |
| wall_seconds | 5 | 10.8300 | 11.9290 | 16.9660 |

## ollama/tg-qwen3.5-9b-ctx16k, gate_on

| metric | count / denominator | rate | Wilson 95% | denominator is |
|---|---|---|---|---|
| correct | 5 / 5 | 1.0000 | 0.5655 to 1.0000 | all runs |
| confident_wrong | 0 / 5 | 0.0000 | 0.0000 to 0.4345 | all runs |
| no_accepted_submission | 0 / 5 | 0.0000 | 0.0000 to 0.4345 | all runs |
| abstained | 0 / 5 | 0.0000 | 0.0000 to 0.4345 | all runs |
| abstained_where_expected | 0 / 0 | n/a | n/a | runs of tasks whose expected status is cannot_determine |
| wrong_abstention | 0 / 5 | 0.0000 | 0.0000 to 0.4345 | runs of tasks whose expected status is not cannot_determine |
| first_unsupported | 2 / 5 | 0.4000 | 0.1176 to 0.7693 | runs with at least one submit call |
| final_unsupported | 2 / 5 | 0.4000 | 0.1176 to 0.7693 | runs with an accepted submission |
| gate_exhausted | 2 / 5 | 0.4000 | 0.1176 to 0.7693 | all runs |
| context_risk | 0 / 5 | 0.0000 | 0.0000 to 0.4345 | runs with a model call that reported usage |
| rejected_at_least_once | 2 / 5 | 0.4000 | 0.1176 to 0.7693 | all runs |

| per run | n runs | median | mean | max |
|---|---|---|---|---|
| n_rejections | 5 | 0.0000 | 0.8000 | 2 |
| input_tokens | 5 | 219.0000 | 357.2000 | 620 |
| output_tokens | 5 | 552.0000 | 963.6000 | 1871 |
| total_tokens | 5 | 3555.0000 | 8314.8000 | 18524 |
| max_prompt_tokens | 5 | 1316.0000 | 1943.2000 | 3136 |
| wall_seconds | 5 | 11.8190 | 31.7286 | 66.4990 |

## Paired comparison of confident_wrong (gate_on minus gate_off)

Pairs are matched by (model, task, epoch). A run without an accepted submission enters its pair with confident_wrong 0.

- ollama/tg-qwen3.5-9b-ctx16k: sum of differences 0 over 5 pairs, mean 0.0000; pairs over 1 tasks; too few tasks, no interval given.

## Per task

| model | task | condition | runs | correct | confident_wrong | no accepted submission |
|---|---|---|---|---|---|---|
| ollama/tg-qwen3.5-9b-ctx16k | v1_benign_missing | gate_off | 5 | 5 | 0 | 0 |
| ollama/tg-qwen3.5-9b-ctx16k | v1_benign_missing | gate_on | 5 | 5 | 0 | 0 |

## Runs without an accepted submission or with an error

None (0 of 10 runs).
