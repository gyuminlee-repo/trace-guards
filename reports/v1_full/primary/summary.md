# Run summary (preliminary)

**Preliminary.** Few tasks and few epochs; the intervals are wide and the task-level bootstrap is coarse. Every rate is shown as count / denominator.

- commit: `f671a214895c06af838f8d9067b353ed13616429` (working tree clean: True)
- models: ollama/tg-qwen3.5-9b-ctx16k
- context length (tokens): ollama/tg-qwen3.5-9b-ctx16k 16384
- epochs: 5; temperature: 0.7; task seed: 0; message limit: 30
- tasks (3): v1_culture_gap, v1_presence_shift, v1_plate_recovery
- conditions: gate_off, gate_on
- inspect_ai 0.3.273; started 2026-10-13T01:51:42+00:00
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
| correct | 15 / 15 | 1.0000 | 0.7961 to 1.0000 | all runs |
| confident_wrong | 0 / 15 | 0.0000 | 0.0000 to 0.2039 | all runs |
| no_accepted_submission | 0 / 15 | 0.0000 | 0.0000 to 0.2039 | all runs |
| abstained | 10 / 15 | 0.6667 | 0.4171 to 0.8482 | all runs |
| abstained_where_expected | 10 / 10 | 1.0000 | 0.7225 to 1.0000 | runs of tasks whose expected status is cannot_determine |
| wrong_abstention | 0 / 5 | 0.0000 | 0.0000 to 0.4345 | runs of tasks whose expected status is not cannot_determine |
| first_unsupported | 1 / 15 | 0.0667 | 0.0119 to 0.2982 | runs with at least one submit call |
| final_unsupported | 1 / 15 | 0.0667 | 0.0119 to 0.2982 | runs with an accepted submission |
| gate_exhausted | 0 / 15 | 0.0000 | 0.0000 to 0.2039 | all runs |
| context_risk | 0 / 15 | 0.0000 | 0.0000 to 0.2039 | runs with a model call that reported usage |
| rejected_at_least_once | 0 / 15 | 0.0000 | 0.0000 to 0.2039 | all runs |

| per run | n runs | median | mean | max |
|---|---|---|---|---|
| n_rejections | 15 | 0.0000 | 0.0000 | 0 |
| input_tokens | 15 | 770.0000 | 987.0000 | 5524 |
| output_tokens | 15 | 1124.0000 | 2638.4000 | 10207 |
| total_tokens | 15 | 4966.0000 | 11616.8667 | 54702 |
| max_prompt_tokens | 15 | 2035.0000 | 3570.2667 | 12164 |
| wall_seconds | 15 | 36.4560 | 69.3641 | 226.8750 |

## ollama/tg-qwen3.5-9b-ctx16k, gate_on

| metric | count / denominator | rate | Wilson 95% | denominator is |
|---|---|---|---|---|
| correct | 13 / 15 | 0.8667 | 0.6212 to 0.9626 | all runs |
| confident_wrong | 1 / 15 | 0.0667 | 0.0119 to 0.2982 | all runs |
| no_accepted_submission | 1 / 15 | 0.0667 | 0.0119 to 0.2982 | all runs |
| abstained | 9 / 15 | 0.6000 | 0.3575 to 0.8018 | all runs |
| abstained_where_expected | 9 / 10 | 0.9000 | 0.5958 to 0.9821 | runs of tasks whose expected status is cannot_determine |
| wrong_abstention | 0 / 5 | 0.0000 | 0.0000 to 0.4345 | runs of tasks whose expected status is not cannot_determine |
| first_unsupported | 2 / 15 | 0.1333 | 0.0374 to 0.3788 | runs with at least one submit call |
| final_unsupported | 0 / 14 | 0.0000 | 0.0000 to 0.2153 | runs with an accepted submission |
| gate_exhausted | 0 / 15 | 0.0000 | 0.0000 to 0.2039 | all runs |
| context_risk | 0 / 15 | 0.0000 | 0.0000 to 0.2039 | runs with a model call that reported usage |
| rejected_at_least_once | 2 / 15 | 0.1333 | 0.0374 to 0.3788 | all runs |

| per run | n runs | median | mean | max |
|---|---|---|---|---|
| n_rejections | 15 | 0.0000 | 0.2000 | 2 |
| input_tokens | 15 | 879.0000 | 948.6667 | 2916 |
| output_tokens | 15 | 1425.0000 | 3415.2000 | 9291 |
| total_tokens | 15 | 9472.0000 | 19942.5333 | 76343 |
| max_prompt_tokens | 15 | 2311.0000 | 4454.8667 | 10972 |
| wall_seconds | 15 | 32.4340 | 74.6409 | 234.9500 |

## Paired comparison of confident_wrong (gate_on minus gate_off)

Pairs are matched by (model, task, epoch). A run without an accepted submission enters its pair with confident_wrong 0.

- ollama/tg-qwen3.5-9b-ctx16k: sum of differences 1 over 15 pairs, mean 0.0667; pairs over 3 tasks; too few tasks, no interval given.

## Per task

| model | task | condition | runs | correct | confident_wrong | no accepted submission |
|---|---|---|---|---|---|---|
| ollama/tg-qwen3.5-9b-ctx16k | v1_culture_gap | gate_off | 5 | 5 | 0 | 0 |
| ollama/tg-qwen3.5-9b-ctx16k | v1_culture_gap | gate_on | 5 | 4 | 1 | 0 |
| ollama/tg-qwen3.5-9b-ctx16k | v1_plate_recovery | gate_off | 5 | 5 | 0 | 0 |
| ollama/tg-qwen3.5-9b-ctx16k | v1_plate_recovery | gate_on | 5 | 4 | 0 | 1 |
| ollama/tg-qwen3.5-9b-ctx16k | v1_presence_shift | gate_off | 5 | 5 | 0 | 0 |
| ollama/tg-qwen3.5-9b-ctx16k | v1_presence_shift | gate_on | 5 | 5 | 0 | 0 |

## Runs without an accepted submission or with an error

| model | task | epoch | condition | submit calls | rejections | error or limit |
|---|---|---|---|---|---|---|
| ollama/tg-qwen3.5-9b-ctx16k | v1_plate_recovery | 4 | gate_on | 2 | 2 | limit:message |
