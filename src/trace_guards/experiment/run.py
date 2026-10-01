"""Run the gate_off and gate_on conditions over a set of tasks.

    PYTHONPATH=src python -m trace_guards.experiment.run --tasks dev --epochs 2

Writes `run_meta.json` and Inspect json logs under the output folder. Samples
run one at a time so that wall time per run is not inflated by queueing on a
single local model server.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

import inspect_ai
from inspect_ai import eval

from ..tasks.registry import all_specs
from ..tasks.spec import TaskSpec
from . import build

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_MODEL = "ollama/qwen3.5:9b"
# DESIGN.md section 10: only these may be run while guards are still open.
DEV_TASKS = ("seq_gc", "lit_lookup", "trap_alias")
META_FILE = "run_meta.json"
LOG_DIR = "logs"


def holdout_tasks(seed: int = 0) -> tuple[str, ...]:
    return tuple(s.id for s in all_specs(seed) if s.id not in DEV_TASKS)


def select_specs(tasks: str, seed: int) -> list[TaskSpec]:
    specs = {s.id: s for s in all_specs(seed)}
    if tasks == "all":
        ids = list(specs)
    elif tasks == "dev":
        ids = list(DEV_TASKS)
    elif tasks == "holdout":
        ids = list(holdout_tasks(seed))
    else:
        ids = [t.strip() for t in tasks.split(",") if t.strip()]
    if not ids:
        raise ValueError("no task selected")
    unknown = [t for t in ids if t not in specs]
    if unknown:
        raise ValueError(f"unknown task ids: {unknown}")
    if len(set(ids)) != len(ids):
        raise ValueError(f"duplicate task ids: {ids}")
    return [specs[t] for t in ids]


def _git(*args: str) -> str:
    done = subprocess.run(
        ["git", "-C", str(REPO_ROOT), *args], capture_output=True, text=True, check=True
    )
    return done.stdout


def git_state() -> tuple[str, bool]:
    """(commit SHA, working tree is clean)."""
    return _git("rev-parse", "HEAD").strip(), _git("status", "--porcelain").strip() == ""


def _split(value: str) -> list[str]:
    return [v.strip() for v in value.split(",") if v.strip()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--models", default=DEFAULT_MODEL, help="comma separated")
    parser.add_argument("--tasks", required=True, help="comma separated ids, or all, dev, holdout")
    parser.add_argument("--epochs", type=int, required=True)
    parser.add_argument("--conditions", default=",".join(build.CONDITIONS))
    parser.add_argument("--seed", type=int, default=0, help="task generation seed")
    parser.add_argument("--out", default=None, help="default runs/<UTC time>")
    parser.add_argument("--allow-dirty", action="store_true")
    args = parser.parse_args(argv)

    models = _split(args.models)
    conditions = _split(args.conditions)
    bad = [c for c in conditions if c not in build.CONDITIONS]
    if bad or not conditions or not models or args.epochs < 1:
        parser.error("need at least one model, one known condition and epochs >= 1")
    specs = select_specs(args.tasks, args.seed)

    commit, clean = git_state()
    if not clean and not args.allow_dirty:
        print(
            "working tree is not clean; commit first or pass --allow-dirty "
            "(the recorded commit would not describe the code that ran)",
            file=sys.stderr,
        )
        return 2

    started = datetime.now(timezone.utc)
    out = Path(args.out or f"runs/{started.strftime('%Y%m%dT%H%M%SZ')}")
    out.mkdir(parents=True, exist_ok=False)
    meta = {
        "commit": commit,
        "worktree_clean": clean,
        "models": models,
        "conditions": conditions,
        "temperature": build.TEMPERATURE,
        "message_limit": build.MESSAGE_LIMIT,
        "max_rejections": build.MAX_REJECTIONS,
        "epochs": args.epochs,
        "seed": args.seed,
        "task_ids": [s.id for s in specs],
        "inspect_ai_version": inspect_ai.__version__,
        "started_utc": started.isoformat(timespec="seconds"),
    }
    (out / META_FILE).write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")

    failures: list[str] = []
    for model in models:
        for condition in conditions:
            label = f"{model} {condition}"
            print(f"running {label}: {len(specs)} tasks x {args.epochs} epochs", flush=True)
            try:
                logs = eval(
                    [build.build_task(spec, condition) for spec in specs],
                    model=model,
                    epochs=args.epochs,
                    log_dir=str(out / LOG_DIR),
                    log_format="json",
                    max_tasks=1,
                    max_samples=1,
                    fail_on_error=False,
                    display="none",
                )
            except Exception:  # reported below; the remaining runs still go ahead
                traceback.print_exc()
                failures.append(f"{label}: eval raised (traceback above)")
                continue
            for log in logs:
                if log.status != "success":
                    failures.append(f"{label} {log.eval.task}: log status {log.status}")
                for sample in log.samples or []:
                    if sample.error is not None:
                        failures.append(
                            f"{label} {log.eval.task} epoch {sample.epoch}: sample error"
                        )

    print(f"logs written under {out.as_posix()}")
    if failures:
        print(f"{len(failures)} failures:", file=sys.stderr)
        for line in failures:
            print(f"  {line}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
