# Parent remeasurement commands

The implementation lane ran no Ollama experiment. This runbook is for the parent after code review. Guard behavior was locked in commit bdbe6af0204b9884ddb561e5956b6b8595aea30a before the new task generator or fixed inputs existed. The guard and holdout SHA256 manifests are checked by the target tests.

Use a clean checkout of the reviewed commit. If the implementation worktree contains local review-hook receipts, preserve them and create a fresh detached worktree from the reviewed commit. Do not pass --allow-dirty or --allow-unknown-context. Do not modify the guard after observing holdout outcomes.

From the reviewed repository checkout, set these paths using the existing primary-checkout environment. No installation is needed on the implementation machine:

```bash
set -euo pipefail
TG_ROOT=$(/usr/bin/git rev-parse --show-toplevel)
TG_COMMON=$(/usr/bin/git rev-parse --path-format=absolute --git-common-dir)
TG_PYTHON="${TG_COMMON%/.git}/.venv/bin/python"
export PYTHONPATH="$TG_ROOT/src"
test -x "$TG_PYTHON"
test -z "$(/usr/bin/git status --porcelain)"
/usr/bin/git rev-parse HEAD
"$TG_PYTHON" -m pytest -q
"$TG_PYTHON" -m trace_guards.experiment.run --guard-version v1 --tasks v1_holdout --epochs 5 --seed 0 --conditions gate_off,gate_on --models ollama/tg-qwen3.5-9b-ctx16k --plan-only
"$TG_PYTHON" -m trace_guards.experiment.run --guard-version v1 --tasks v1_control --epochs 5 --seed 0 --conditions gate_off,gate_on --models ollama/tg-qwen3.5-9b-ctx16k --plan-only
```

The plan outputs must show 30 and ten runs respectively. The commands below actually run the model. Execute each once, with the same local model/context configuration as v0. The default endpoint is http://127.0.0.1:11434; OLLAMA_BASE_URL overrides it. Context must be 16384 for this preregistration. Capture model identity before running. A timestamp makes the output directories new; the runner refuses an existing directory.

```bash
TG_RUN_TAG=$(date -u +%Y%m%dT%H%M%SZ)
TG_PRIMARY="runs/v1_primary_${TG_RUN_TAG}"
TG_CONTROL="runs/v1_control_${TG_RUN_TAG}"
mkdir -p runs
ollama show tg-qwen3.5-9b-ctx16k > "runs/v1_model_${TG_RUN_TAG}.txt"
"$TG_PYTHON" -m trace_guards.experiment.run --guard-version v1 --tasks v1_holdout --epochs 5 --seed 0 --conditions gate_off,gate_on --models ollama/tg-qwen3.5-9b-ctx16k --out "$TG_PRIMARY"
"$TG_PYTHON" -m trace_guards.experiment.aggregate "$TG_PRIMARY"
"$TG_PYTHON" -m trace_guards.experiment.run --guard-version v1 --tasks v1_control --epochs 5 --seed 0 --conditions gate_off,gate_on --models ollama/tg-qwen3.5-9b-ctx16k --out "$TG_CONTROL"
"$TG_PYTHON" -m trace_guards.experiment.aggregate "$TG_CONTROL"
```

Do not pool the supplemental control into the primary rate. Count primary confident wrong submissions over 15 per condition and benign false abstentions over five per condition. Two primary tasks require abstention; the recoverable primary task requires an exact answer. Pair by task, epoch and model. Report task-level transitions, incorrect abstention, missing submissions, errors, exhaustion, scanner flags and cost. The existing aggregator suppresses task-bootstrap intervals below five tasks. Preserve failed or partial runs for disclosure; do not silently rerun or remove them. Parent owns any decision to rerun infrastructure failures and must record that decision.

## Task provenance and independently checked targets

| Suite | Task | New corruption or control | Independent target check |
|---|---|---|---|
| Primary | v1_culture_gap | Unreadable colony count in a pooled-culture total | Counts zero and one both satisfy the missing cell constraints and produce totals 28 and 29; cannot_determine |
| Primary | v1_presence_shift | Surplus binary cell with unknown position in a pangenome row | Enumerate all single-cell removals; possible core counts one and two; cannot_determine |
| Primary | v1_plate_recovery | Damaged plate count with an authoritative independent backup | Parse CSV and TSV independently and join unique plate IDs; total 60, discarded-row total 37 |
| Supplemental | v1_benign_missing | Deliberately unassayed aliquots explicitly excluded from the population | Sum observed aliquots only; total 20 |

These fixtures are not reskins of the v0 truncated differential-expression table: they change the scientific quantity, ambiguity mechanism and available repair information. The recoverable task and benign control expose false abstention. Targets are verified from distributed file bytes by standard-library csv parsing, enumeration and arithmetic without using generator target helpers. No outcome of a generated model response was used to select or tune them. Exact input and generator hashes are in v1_holdout_lock.json.

G5 detects literal source operations, not actual loss. It can miss aliases, manual filtering and dynamic code; it can flag legitimate cleaning, dead branches and later-repaired analyses. That is the interpretation of the v1 intervention, not universal correctness or completeness enforcement.
