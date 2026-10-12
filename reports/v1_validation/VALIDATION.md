# v1 implementation validation

No model experiment was run. All generation in QA uses scripted Inspect mockllm responses on development fixtures. Parent owns independent review, merge and the paired 40-run experiment.

Evidence root is .omo/evidence/v1 in the implementation worktree. This tracked directory mirrors the main raw receipts for PR review. Inspect JSON traces remain under the evidence root in verified_development_logs, with exact filenames printed in full_validation.txt.

## Commands and binary observables

Run from the repository root with PYTHONPATH=src and the existing interpreter obtained as follows:

```bash
TG_COMMON=$(/usr/bin/git rev-parse --path-format=absolute --git-common-dir)
TG_PYTHON="${TG_COMMON%/.git}/.venv/bin/python"
export PYTHONPATH=src
```

| Scenario | Invocation | Binary observable | Captured artifact |
|---|---|---|---|
| Existing baseline before edits | "$TG_PYTHON" -m pytest -q | exit zero, 229 passed | baseline.txt |
| Pre-lock full suite | "$TG_PYTHON" -m pytest -q | exit zero, 242 passed | prelock_full.txt |
| Complete suite after task construction | TG_QA_DIR=.omo/evidence/v1/verified_development_logs "$TG_PYTHON" -m pytest -q -s | exit zero, 250 passed | full_validation.txt |
| Actual scanner CLI, both versions | "$TG_PYTHON" -m trace_guards.guards tests/corpus/g5_silent_discard.jsonl --guard-version v1; repeat with v0 | v1 G5 fires on nine labelled positives, passes ten negatives; v0 has no G5 finding | full_validation.txt, COMMAND and JSON lines |
| Actual Python execution and Inspect gate | "$TG_PYTHON" -m pytest -q -s tests/experiment/test_v1_gate.py | coerce and skip rejected; strict and abstention accepted; budget exhausted only after two rejections; scanner parity in every record | full_validation.txt and verified_development_logs/*.json in per-case directories |
| Independent target verification | "$TG_PYTHON" -m pytest -q -s tests/tasks/test_v1_targets.py | compatible totals 28/29 and 1/2 imply abstention; recovered total 60; benign total 20; guard and task hashes match | full_validation.txt, target JSON lines |
| v0 preservation | Load each archived Inspect JSON via rows_from_log with original source and v1 source, select qwen, compare serialized rows and SHA256 every archived file | 100 identical qwen rows, 25 unchanged archived files including three additional gemma samples | v0_preservation.json; full before/after arrays and hash inventory in evidence root |
| Dirty runner refusal | "$TG_PYTHON" -m trace_guards.experiment.run --tasks dev --guard-version v1 --epochs 5 --plan-only | exit two before model contact | evidence root: runner_dirty_refusal.txt |

The final committed-code runner invocations are exactly the two --plan-only commands in docs/V1_RUNBOOK.md. Their clean-checkout outputs, final test rerun, git receipts and PR response are recorded in the local evidence index when publication completes. No --allow-dirty or --allow-unknown-context override is used.

## Ordering, repair and limits

Design precommit db3d1b1 precedes development corpus commit 8e8072f, which precedes guard lock bdbe6af0204b9884ddb561e5956b6b8595aea30a. Only afterward were the new generator, holdout inputs, control and independent target checks created. All 34 locked guard/runtime/design/corpus hashes remain unchanged. The independent target verifier parses distributed files and does not use generator arithmetic helpers.

One full-suite run caught the new task generator using a relative import, which the existing repository test forbids. The generator import was corrected to the repository convention and the entire suite rerun successfully. Guard code, input bytes and targets did not change. The failed log is retained as .omo/evidence/v1/full_validation.txt; the succeeding log is full_validation_pass.txt and mirrored here as full_validation.txt.

Read-only implementation review returned PASS (prelock_review.txt). The automatic review hook separately recorded UNKNOWN with reason=credit and did not produce .codex-review-passed (review_gate_receipt.txt). That hook state is preserved in the original worktree; no guard or setting was disabled. This is not an automatic-review PASS claim. Parent performs final independent review.

G5 remains a source-syntax heuristic with documented false positives and evasions. The experiment is limited to three corrupted tasks and one separate benign control, one seed and one local model. Model effects and general correctness remain unmeasured.
