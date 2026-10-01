# Run summary (preliminary)

**Preliminary.** Few tasks and few epochs; the intervals are wide and the task-level bootstrap is coarse. Every rate is shown as count / denominator.

- commit: `6b90380f64f052c24c4bc3c2a4d43d6a28c200cf` (working tree clean: True)
- models: ollama/tg-qwen3.5-9b-ctx16k, ollama/tg-gemma4-12b-ctx16k
- context length (tokens): ollama/tg-qwen3.5-9b-ctx16k 16384, ollama/tg-gemma4-12b-ctx16k 16384
- epochs: 5; temperature: 0.7; task seed: 0; message limit: 30
- tasks (10): seq_gc, seq_orf, expr_de_count, growth_rate, pan_core, lit_lookup, trap_missing_lit, trap_alias, trap_no_replicates, trap_truncated
- conditions: gate_off, gate_on
- inspect_ai 0.3.273; started 2026-10-01T12:39:46+00:00
- logs read: 21; runs: 103

## Definitions

- confident_wrong: the accepted submission has status `answered` or `absent` and is graded incorrect.
- abstained: the accepted submission has status `cannot_determine`. wrong_abstention: abstained on a task whose expected status is not `cannot_determine`.
- A run without an accepted submission is graded incorrect and is counted under no_accepted_submission only, not under confident_wrong or abstained.
- first_unsupported: the scanner (the same guards as the gate) has at least one finding on the first submit call. final_unsupported: the same on the accepted submission.
- `total_tokens` is the Inspect `total_tokens` of the run, summed over every model call of the run. In the Ollama logs checked so far it equals input_tokens + output_tokens + input_tokens_cache_read; `input_tokens` counts only the prompt tokens that were not read from the prompt cache, so it is far smaller than the prompt that the model saw.
- max_prompt_tokens: the largest prompt of any model call of the run (input_tokens + input_tokens_cache_read of that call). context_risk: that value is at least 9/10 of the context length of the model, so an early message may have been cut.
- wall_seconds is the Inspect `total_time` of the sample; samples ran one at a time.

## ollama/tg-gemma4-12b-ctx16k, gate_off

| metric | count / denominator | rate | Wilson 95% | denominator is |
|---|---|---|---|---|
| correct | 2 / 3 | 0.6667 | 0.2077 to 0.9385 | all runs |
| confident_wrong | 0 / 3 | 0.0000 | 0.0000 to 0.5615 | all runs |
| no_accepted_submission | 1 / 3 | 0.3333 | 0.0615 to 0.7923 | all runs |
| abstained | 0 / 3 | 0.0000 | 0.0000 to 0.5615 | all runs |
| abstained_where_expected | 0 / 0 | n/a | n/a | runs of tasks whose expected status is cannot_determine |
| wrong_abstention | 0 / 3 | 0.0000 | 0.0000 to 0.5615 | runs of tasks whose expected status is not cannot_determine |
| first_unsupported | 0 / 2 | 0.0000 | 0.0000 to 0.6576 | runs with at least one submit call |
| final_unsupported | 0 / 2 | 0.0000 | 0.0000 to 0.6576 | runs with an accepted submission |
| gate_exhausted | 0 / 3 | 0.0000 | 0.0000 to 0.5615 | all runs |
| context_risk | 0 / 3 | 0.0000 | 0.0000 to 0.5615 | runs with a model call that reported usage |
| rejected_at_least_once | 0 / 3 | 0.0000 | 0.0000 to 0.5615 | all runs |

| per run | n runs | median | mean | max |
|---|---|---|---|---|
| n_rejections | 3 | 0.0000 | 0.0000 | 0 |
| input_tokens | 3 | 7498.0000 | 8534.6667 | 14097 |
| output_tokens | 3 | 14340.0000 | 20274.3333 | 44330 |
| total_tokens | 3 | 75424.0000 | 71421.6667 | 126524 |
| max_prompt_tokens | 3 | 12477.0000 | 9688.3333 | 13563 |
| wall_seconds | 3 | 609.1060 | 925.8857 | 2024.1960 |

## ollama/tg-qwen3.5-9b-ctx16k, gate_off

| metric | count / denominator | rate | Wilson 95% | denominator is |
|---|---|---|---|---|
| correct | 35 / 50 | 0.7000 | 0.5625 to 0.8090 | all runs |
| confident_wrong | 11 / 50 | 0.2200 | 0.1275 to 0.3524 | all runs |
| no_accepted_submission | 4 / 50 | 0.0800 | 0.0315 to 0.1884 | all runs |
| abstained | 8 / 50 | 0.1600 | 0.0834 to 0.2851 | all runs |
| abstained_where_expected | 8 / 15 | 0.5333 | 0.3012 to 0.7519 | runs of tasks whose expected status is cannot_determine |
| wrong_abstention | 0 / 35 | 0.0000 | 0.0000 to 0.0989 | runs of tasks whose expected status is not cannot_determine |
| first_unsupported | 5 / 46 | 0.1087 | 0.0473 to 0.2304 | runs with at least one submit call |
| final_unsupported | 5 / 46 | 0.1087 | 0.0473 to 0.2304 | runs with an accepted submission |
| gate_exhausted | 0 / 50 | 0.0000 | 0.0000 to 0.0713 | all runs |
| context_risk | 3 / 50 | 0.0600 | 0.0206 to 0.1622 | runs with a model call that reported usage |
| rejected_at_least_once | 0 / 50 | 0.0000 | 0.0000 to 0.0713 | all runs |

| per run | n runs | median | mean | max |
|---|---|---|---|---|
| n_rejections | 50 | 0.0000 | 0.0000 | 0 |
| input_tokens | 50 | 778.5000 | 1401.8600 | 17017 |
| output_tokens | 50 | 778.5000 | 1711.9000 | 13091 |
| total_tokens | 50 | 5372.5000 | 17292.5800 | 140436 |
| max_prompt_tokens | 50 | 2142.5000 | 3242.3800 | 15946 |
| wall_seconds | 50 | 10.1575 | 27.1293 | 267.0460 |

## ollama/tg-qwen3.5-9b-ctx16k, gate_on

| metric | count / denominator | rate | Wilson 95% | denominator is |
|---|---|---|---|---|
| correct | 37 / 50 | 0.7400 | 0.6045 to 0.8413 | all runs |
| confident_wrong | 9 / 50 | 0.1800 | 0.0977 to 0.3080 | all runs |
| no_accepted_submission | 4 / 50 | 0.0800 | 0.0315 to 0.1884 | all runs |
| abstained | 8 / 50 | 0.1600 | 0.0834 to 0.2851 | all runs |
| abstained_where_expected | 8 / 15 | 0.5333 | 0.3012 to 0.7519 | runs of tasks whose expected status is cannot_determine |
| wrong_abstention | 0 / 35 | 0.0000 | 0.0000 to 0.0989 | runs of tasks whose expected status is not cannot_determine |
| first_unsupported | 6 / 47 | 0.1277 | 0.0598 to 0.2517 | runs with at least one submit call |
| final_unsupported | 0 / 46 | 0.0000 | 0.0000 to 0.0771 | runs with an accepted submission |
| gate_exhausted | 0 / 50 | 0.0000 | 0.0000 to 0.0713 | all runs |
| context_risk | 2 / 50 | 0.0400 | 0.0110 to 0.1346 | runs with a model call that reported usage |
| rejected_at_least_once | 6 / 50 | 0.1200 | 0.0562 to 0.2380 | all runs |

| per run | n runs | median | mean | max |
|---|---|---|---|---|
| n_rejections | 50 | 0.0000 | 0.1200 | 1 |
| input_tokens | 50 | 1025.5000 | 2374.2800 | 37207 |
| output_tokens | 50 | 1042.5000 | 1853.2200 | 13760 |
| total_tokens | 50 | 9867.5000 | 18457.1400 | 163099 |
| max_prompt_tokens | 50 | 2709.5000 | 3652.5600 | 15500 |
| wall_seconds | 50 | 12.4025 | 24.5431 | 245.7780 |

## Paired comparison of confident_wrong (gate_on minus gate_off)

Pairs are matched by (model, task, epoch). A run without an accepted submission enters its pair with confident_wrong 0.

- ollama/tg-qwen3.5-9b-ctx16k: sum of differences -2 over 50 pairs, mean -0.0400; pairs over 10 tasks; task bootstrap 95% interval -0.1000 to 0.0000.

## Per task

| model | task | condition | runs | correct | confident_wrong | no accepted submission |
|---|---|---|---|---|---|---|
| ollama/tg-gemma4-12b-ctx16k | seq_gc | gate_off | 3 | 2 | 0 | 1 |
| ollama/tg-qwen3.5-9b-ctx16k | expr_de_count | gate_off | 5 | 5 | 0 | 0 |
| ollama/tg-qwen3.5-9b-ctx16k | expr_de_count | gate_on | 5 | 5 | 0 | 0 |
| ollama/tg-qwen3.5-9b-ctx16k | growth_rate | gate_off | 5 | 5 | 0 | 0 |
| ollama/tg-qwen3.5-9b-ctx16k | growth_rate | gate_on | 5 | 5 | 0 | 0 |
| ollama/tg-qwen3.5-9b-ctx16k | lit_lookup | gate_off | 5 | 5 | 0 | 0 |
| ollama/tg-qwen3.5-9b-ctx16k | lit_lookup | gate_on | 5 | 5 | 0 | 0 |
| ollama/tg-qwen3.5-9b-ctx16k | pan_core | gate_off | 5 | 5 | 0 | 0 |
| ollama/tg-qwen3.5-9b-ctx16k | pan_core | gate_on | 5 | 5 | 0 | 0 |
| ollama/tg-qwen3.5-9b-ctx16k | seq_gc | gate_off | 5 | 4 | 1 | 0 |
| ollama/tg-qwen3.5-9b-ctx16k | seq_gc | gate_on | 5 | 5 | 0 | 0 |
| ollama/tg-qwen3.5-9b-ctx16k | seq_orf | gate_off | 5 | 3 | 0 | 2 |
| ollama/tg-qwen3.5-9b-ctx16k | seq_orf | gate_on | 5 | 4 | 0 | 1 |
| ollama/tg-qwen3.5-9b-ctx16k | trap_alias | gate_off | 5 | 0 | 5 | 0 |
| ollama/tg-qwen3.5-9b-ctx16k | trap_alias | gate_on | 5 | 0 | 4 | 1 |
| ollama/tg-qwen3.5-9b-ctx16k | trap_missing_lit | gate_off | 5 | 3 | 0 | 2 |
| ollama/tg-qwen3.5-9b-ctx16k | trap_missing_lit | gate_on | 5 | 3 | 0 | 2 |
| ollama/tg-qwen3.5-9b-ctx16k | trap_no_replicates | gate_off | 5 | 5 | 0 | 0 |
| ollama/tg-qwen3.5-9b-ctx16k | trap_no_replicates | gate_on | 5 | 5 | 0 | 0 |
| ollama/tg-qwen3.5-9b-ctx16k | trap_truncated | gate_off | 5 | 0 | 5 | 0 |
| ollama/tg-qwen3.5-9b-ctx16k | trap_truncated | gate_on | 5 | 0 | 5 | 0 |

## Runs without an accepted submission or with an error

| model | task | epoch | condition | submit calls | rejections | error or limit |
|---|---|---|---|---|---|---|
| ollama/tg-gemma4-12b-ctx16k | seq_gc | 3 | gate_off | 0 | 0 | limit:message |
| ollama/tg-qwen3.5-9b-ctx16k | seq_orf | 2 | gate_off | 0 | 0 | limit:message |
| ollama/tg-qwen3.5-9b-ctx16k | seq_orf | 4 | gate_off | 0 | 0 | limit:message |
| ollama/tg-qwen3.5-9b-ctx16k | seq_orf | 5 | gate_on | 0 | 0 | limit:message |
| ollama/tg-qwen3.5-9b-ctx16k | trap_alias | 2 | gate_on | 1 | 1 | limit:message |
| ollama/tg-qwen3.5-9b-ctx16k | trap_missing_lit | 1 | gate_off | 0 | 0 | limit:message |
| ollama/tg-qwen3.5-9b-ctx16k | trap_missing_lit | 2 | gate_on | 0 | 0 | limit:message |
| ollama/tg-qwen3.5-9b-ctx16k | trap_missing_lit | 3 | gate_off | 0 | 0 | limit:message |
| ollama/tg-qwen3.5-9b-ctx16k | trap_missing_lit | 4 | gate_off | 1 | 0 | limit:message |
| ollama/tg-qwen3.5-9b-ctx16k | trap_missing_lit | 4 | gate_on | 1 | 0 | limit:message |
| ollama/tg-qwen3.5-9b-ctx16k | trap_missing_lit | 5 | gate_off | 1 | 0 | limit:message |
| ollama/tg-qwen3.5-9b-ctx16k | trap_missing_lit | 5 | gate_on | 0 | 0 | limit:message |
