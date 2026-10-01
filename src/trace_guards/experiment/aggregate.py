"""Aggregate one run folder into runs.csv, summary.csv and summary.md.

    PYTHONPATH=src python -m trace_guards.experiment.aggregate runs/<folder>

Definitions follow DESIGN.md sections 3 and 10. Every rate is written with
its count and denominator.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import statistics
import sys
from pathlib import Path
from typing import Any, Mapping

from inspect_ai.log import EvalLog, read_eval_log

from .. import inspect_adapter as ia
from ..guards import run_all
from .build import SCORER_NAME
from .run import LOG_DIR, META_FILE

RUN_COLUMNS = (
    "model", "task_id", "kind", "trap", "epoch", "condition", "final_status",
    "expected_status", "correct", "confident_wrong", "abstained", "wrong_abstention",
    "n_submit_calls", "n_rejections", "gate_exhausted", "first_findings",
    "final_findings", "first_unsupported", "n_tool_events", "input_tokens",
    "output_tokens", "total_tokens", "max_prompt_tokens", "context_risk", "wall_seconds",
    "accepted_submission_present", "error",
)  # fmt: skip
SUMMARY_COLUMNS = (
    "model", "condition", "metric", "count", "denominator", "rate",
    "ci_low", "ci_high", "median", "mean", "max", "note",
)  # fmt: skip
COST_FIELDS = (
    "n_rejections", "input_tokens", "output_tokens", "total_tokens",
    "max_prompt_tokens", "wall_seconds",
)  # fmt: skip
# A run is at risk when its largest prompt reaches this share of the context length.
CONTEXT_RISK_NUMERATOR, CONTEXT_RISK_DENOMINATOR = 9, 10
PAIRED_CONDITION = "gate_on_minus_gate_off"
PAIRED_METRIC = "confident_wrong_paired_difference"
MIN_TASKS_FOR_INTERVAL = 5
TOO_FEW_TASKS = "too few tasks, no interval given"
BOOTSTRAP_REPS = 10_000
BOOTSTRAP_SEED = 0
Z95 = statistics.NormalDist().inv_cdf(0.975)

TOKEN_NOTE = (
    "`total_tokens` is the Inspect `total_tokens` of the run, summed over every "
    "model call of the run. In the Ollama logs checked so far it equals input_tokens + "
    "output_tokens + input_tokens_cache_read; `input_tokens` counts only the "
    "prompt tokens that were not read from the prompt cache, so it is far "
    "smaller than the prompt that the model saw."
)


# --------------------------------------------------------------------------
# One row per run
# --------------------------------------------------------------------------


def _guards_at(store: Mapping[str, Any], task_id: str, index: int) -> str:
    trace, submission = ia.trace_from_store(store, task_id, index)
    findings = run_all(
        trace, submission, requires_citation=store[ia.REQUIRES_CITATION_KEY]
    )
    return ";".join(dict.fromkeys(f.guard for f in findings))


def run_row(
    *,
    model: str,
    task_id: str,
    kind: str,
    trap: str | None,
    epoch: int,
    condition: str,
    expected_status: str,
    store: Mapping[str, Any],
    correct: bool,
    input_tokens: int = 0,
    output_tokens: int = 0,
    total_tokens: int = 0,
    max_prompt_tokens: int | None = None,
    context_length: int,
    wall_seconds: float = 0.0,
    error: str = "",
) -> dict[str, Any]:
    """Measures of one run, from its sample store and its grade."""
    records = ia.submissions_in(store)
    accepted = [i for i, r in enumerate(records) if r["accepted"]]
    final = records[accepted[-1]] if accepted else None
    if final is None and correct:
        raise ValueError(f"{task_id}: graded correct without an accepted submission")
    status = final["submission"]["status"] if final else ""
    abstained = status == "cannot_determine"
    first = _guards_at(store, task_id, 0) if records else ""
    return {
        "model": model,
        "task_id": task_id,
        "kind": kind,
        "trap": trap or "",
        "epoch": epoch,
        "condition": condition,
        "final_status": status,
        "expected_status": expected_status,
        "correct": int(correct),
        "confident_wrong": int(status in ("answered", "absent") and not correct),
        "abstained": int(abstained),
        "wrong_abstention": int(abstained and expected_status != "cannot_determine"),
        "n_submit_calls": len(records),
        "n_rejections": sum(1 for r in records if not r["accepted"]),
        "gate_exhausted": int(bool(final and final["gate_exhausted"])),
        "first_findings": first,
        "final_findings": _guards_at(store, task_id, accepted[-1]) if final else "",
        # Blank when the run made no submit call: there is nothing to scan.
        "first_unsupported": int(bool(first)) if records else "",
        "n_tool_events": len(store.get(ia.EVENTS_KEY, [])),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        # Blank when no model call of the run reported usage.
        "max_prompt_tokens": "" if max_prompt_tokens is None else max_prompt_tokens,
        "context_risk": ""
        if max_prompt_tokens is None
        else int(
            max_prompt_tokens * CONTEXT_RISK_DENOMINATOR
            >= context_length * CONTEXT_RISK_NUMERATOR
        ),
        "wall_seconds": round(wall_seconds, 3),
        "accepted_submission_present": int(final is not None),
        "error": error,
    }


def max_prompt_tokens(sample: Any) -> int | None:
    """Largest prompt of any model call: input tokens plus tokens read from the cache."""
    sizes = [
        event.output.usage.input_tokens + (event.output.usage.input_tokens_cache_read or 0)
        for event in sample.events
        if event.event == "model" and event.output.usage is not None
    ]
    return max(sizes) if sizes else None


def rows_from_log(log: EvalLog, context_length: int) -> list[dict[str, Any]]:
    rows = []
    for sample in log.samples or []:
        error = ""
        if sample.error is not None:
            error = sample.error.message.splitlines()[0][:200]
        elif sample.limit is not None:
            error = f"limit:{sample.limit.type}"
        if sample.scores is None or SCORER_NAME not in sample.scores:
            if sample.error is None:
                raise ValueError(f"{log.eval.task} epoch {sample.epoch}: no score and no error")
            correct = False
        else:
            correct = sample.scores[SCORER_NAME].value == "C"
        usage = list(sample.model_usage.values())
        rows.append(
            run_row(
                model=log.eval.model,
                task_id=str(sample.id),
                kind=sample.metadata["kind"],
                trap=sample.metadata["trap"],
                epoch=sample.epoch,
                condition=log.eval.metadata["condition"],
                expected_status=sample.metadata["expected_status"],
                store=sample.store,
                correct=correct,
                input_tokens=sum(u.input_tokens for u in usage),
                output_tokens=sum(u.output_tokens for u in usage),
                total_tokens=sum(u.total_tokens for u in usage),
                max_prompt_tokens=max_prompt_tokens(sample),
                context_length=context_length,
                wall_seconds=sample.total_time or 0.0,
                error=error,
            )
        )
    return rows


# --------------------------------------------------------------------------
# Summaries
# --------------------------------------------------------------------------


def wilson(count: int, n: int) -> tuple[float, float]:
    """Wilson score interval, 95%. Raises for n == 0."""
    if n <= 0 or not 0 <= count <= n:
        raise ValueError(f"wilson needs 0 <= count <= n and n > 0, got {count}/{n}")
    p = count / n
    z2 = Z95 * Z95
    centre = (p + z2 / (2 * n)) / (1 + z2 / n)
    half = Z95 * ((p * (1 - p) / n + z2 / (4 * n * n)) ** 0.5) / (1 + z2 / n)
    # At the edges the bound is exactly 0 or 1; rounding must not push it past p.
    low = 0.0 if count == 0 else centre - half
    high = 1.0 if count == n else centre + half
    return low, high


def _is(field: str):
    return lambda r: r[field] == 1


# metric -> (numerator test, denominator test, what the denominator is)
RATE_METRICS = {
    "correct": (_is("correct"), lambda r: True, "all runs"),
    "confident_wrong": (_is("confident_wrong"), lambda r: True, "all runs"),
    "no_accepted_submission": (
        lambda r: r["accepted_submission_present"] == 0, lambda r: True, "all runs",
    ),
    "abstained": (_is("abstained"), lambda r: True, "all runs"),
    "abstained_where_expected": (
        _is("abstained"),
        lambda r: r["expected_status"] == "cannot_determine",
        "runs of tasks whose expected status is cannot_determine",
    ),
    "wrong_abstention": (
        _is("wrong_abstention"),
        lambda r: r["expected_status"] != "cannot_determine",
        "runs of tasks whose expected status is not cannot_determine",
    ),
    "first_unsupported": (
        _is("first_unsupported"),
        lambda r: r["n_submit_calls"] > 0,
        "runs with at least one submit call",
    ),
    "final_unsupported": (
        lambda r: r["final_findings"] != "",
        lambda r: r["accepted_submission_present"] == 1,
        "runs with an accepted submission",
    ),
    "gate_exhausted": (_is("gate_exhausted"), lambda r: True, "all runs"),
    "context_risk": (
        _is("context_risk"),
        lambda r: r["max_prompt_tokens"] != "",
        "runs with a model call that reported usage",
    ),
    "rejected_at_least_once": (lambda r: r["n_rejections"] > 0, lambda r: True, "all runs"),
}  # fmt: skip


def _groups(rows: list[dict]) -> dict[tuple[str, str], list[dict]]:
    groups: dict[tuple[str, str], list[dict]] = {}
    for row in rows:
        groups.setdefault((row["model"], row["condition"]), []).append(row)
    return dict(sorted(groups.items()))


def condition_summary(rows: list[dict]) -> list[dict[str, Any]]:
    """Per (model, condition): rate metrics with Wilson intervals, then cost."""
    out = []
    for (model, condition), group in _groups(rows).items():
        base = {"model": model, "condition": condition}
        out.append({**base, "metric": "runs", "count": len(group), "note": "all runs"})
        for metric, (hit, member, note) in RATE_METRICS.items():
            members = [r for r in group if member(r)]
            count = sum(1 for r in members if hit(r))
            line = {**base, "metric": metric, "count": count, "denominator": len(members), "note": note}
            if members:
                low, high = wilson(count, len(members))
                line.update(rate=count / len(members), ci_low=low, ci_high=high)
            out.append(line)
        for field in COST_FIELDS:
            values = [r[field] for r in group if r[field] != ""]
            line = {**base, "metric": field, "denominator": len(values), "note": "per run"}
            if values:
                line.update(
                    median=statistics.median(values),
                    mean=statistics.fmean(values),
                    max=max(values),
                )
            out.append(line)
    return out


def paired_differences(rows: list[dict]) -> dict[str, dict[str, list[int]]]:
    """model -> task -> confident_wrong differences (gate_on minus gate_off) per epoch.

    A run without an accepted submission has confident_wrong 0 and stays in its pair.
    """
    cells: dict[tuple, dict[str, int]] = {}
    for r in rows:
        key = (r["model"], r["task_id"], r["epoch"])
        if r["condition"] in cells.setdefault(key, {}):
            raise ValueError(f"duplicate run for {key} {r['condition']}")
        cells[key][r["condition"]] = r["confident_wrong"]
    out: dict[str, dict[str, list[int]]] = {}
    for (model, task, _), by_condition in sorted(cells.items()):
        if "gate_on" in by_condition and "gate_off" in by_condition:
            diff = by_condition["gate_on"] - by_condition["gate_off"]
            out.setdefault(model, {}).setdefault(task, []).append(diff)
    return out


def bootstrap_interval(by_task: dict[str, list[int]]) -> tuple[float, float] | None:
    """95% percentile interval of the mean paired difference, resampling tasks."""
    tasks = sorted(by_task)
    if len(tasks) < MIN_TASKS_FOR_INTERVAL:
        return None
    rng = random.Random(BOOTSTRAP_SEED)
    means = []
    for _ in range(BOOTSTRAP_REPS):
        diffs = [d for task in rng.choices(tasks, k=len(tasks)) for d in by_task[task]]
        means.append(sum(diffs) / len(diffs))
    means.sort()
    last = BOOTSTRAP_REPS - 1
    return means[round(0.025 * last)], means[round(0.975 * last)]


def paired_summary(rows: list[dict]) -> list[dict[str, Any]]:
    out = []
    for model, by_task in paired_differences(rows).items():
        diffs = [d for task in by_task for d in by_task[task]]
        interval = bootstrap_interval(by_task)
        line = {
            "model": model, "condition": PAIRED_CONDITION, "metric": PAIRED_METRIC,
            "count": sum(diffs), "denominator": len(diffs), "rate": sum(diffs) / len(diffs),
            "note": f"pairs over {len(by_task)} tasks; "
            + (f"task bootstrap, {BOOTSTRAP_REPS} resamples" if interval else TOO_FEW_TASKS),
        }  # fmt: skip
        if interval:
            line.update(ci_low=interval[0], ci_high=interval[1])
        out.append(line)
    return out


def per_task(rows: list[dict]) -> list[dict[str, Any]]:
    cells: dict[tuple, list[dict]] = {}
    for r in rows:
        cells.setdefault((r["model"], r["task_id"], r["condition"]), []).append(r)
    return [
        {
            "model": model, "task_id": task, "condition": condition, "runs": len(group),
            "correct": sum(r["correct"] for r in group),
            "confident_wrong": sum(r["confident_wrong"] for r in group),
            "no_accepted_submission": sum(1 - r["accepted_submission_present"] for r in group),
        }  # fmt: skip
        for (model, task, condition), group in sorted(cells.items())
    ]


# --------------------------------------------------------------------------
# Output
# --------------------------------------------------------------------------


def _num(value: Any) -> str:
    if value is None or value == "":
        return ""
    return f"{value:.4f}" if isinstance(value, float) else str(value)


def _write_csv(path: Path, columns: tuple[str, ...], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({c: _num(row.get(c)) for c in columns})


def _table(header: tuple[str, ...], lines: list[tuple]) -> list[str]:
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    out.extend("| " + " | ".join(str(c) for c in line) + " |" for line in lines)
    return out + [""]


def summary_markdown(meta: dict, rows: list[dict], summary: list[dict], n_logs: int) -> str:
    md = [
        "# Run summary (preliminary)",
        "",
        "**Preliminary.** Few tasks and few epochs; the intervals are wide and the "
        "task-level bootstrap is coarse. Every rate is shown as count / denominator.",
        "",
        f"- commit: `{meta['commit']}` (working tree clean: {meta['worktree_clean']})",
        f"- models: {', '.join(meta['models'])}",
        "- context length (tokens): "
        + ", ".join(f"{m} {n}" for m, n in meta["context_length"].items()),
        f"- epochs: {meta['epochs']}; temperature: {meta['temperature']}; "
        f"task seed: {meta['seed']}; message limit: {meta['message_limit']}",
        f"- tasks ({len(meta['task_ids'])}): {', '.join(meta['task_ids'])}",
        f"- conditions: {', '.join(meta['conditions'])}",
        f"- inspect_ai {meta['inspect_ai_version']}; started {meta['started_utc']}",
        f"- logs read: {n_logs}; runs: {len(rows)}",
        "",
        "## Definitions",
        "",
        "- confident_wrong: the accepted submission has status `answered` or `absent` "
        "and is graded incorrect.",
        "- abstained: the accepted submission has status `cannot_determine`. "
        "wrong_abstention: abstained on a task whose expected status is not "
        "`cannot_determine`.",
        "- A run without an accepted submission is graded incorrect and is counted "
        "under no_accepted_submission only, not under confident_wrong or abstained.",
        "- first_unsupported: the scanner (the same guards as the gate) has at least "
        "one finding on the first submit call. final_unsupported: the same on the "
        "accepted submission.",
        f"- {TOKEN_NOTE}",
        "- max_prompt_tokens: the largest prompt of any model call of the run "
        "(input_tokens + input_tokens_cache_read of that call). context_risk: that "
        f"value is at least {CONTEXT_RISK_NUMERATOR}/{CONTEXT_RISK_DENOMINATOR} of the "
        "context length of the model, so an early message may have been cut.",
        "- wall_seconds is the Inspect `total_time` of the sample; samples ran one at a time.",
        "",
    ]
    for (model, condition), _ in _groups(rows).items():
        own = [s for s in summary if (s["model"], s["condition"]) == (model, condition)]
        md += [f"## {model}, {condition}", ""]
        md += _table(
            ("metric", "count / denominator", "rate", "Wilson 95%", "denominator is"),
            [
                (
                    s["metric"], f"{s['count']} / {s['denominator']}",
                    _num(s.get("rate")) or "n/a",
                    f"{s['ci_low']:.4f} to {s['ci_high']:.4f}" if "ci_low" in s else "n/a",
                    s["note"],
                )
                for s in own if s["metric"] in RATE_METRICS
            ],
        )  # fmt: skip
        md += _table(
            ("per run", "n runs", "median", "mean", "max"),
            [
                (
                    s["metric"], s["denominator"],
                    _num(float(s["median"])) if "median" in s else "n/a",
                    _num(s.get("mean")) or "n/a", _num(s.get("max")) or "n/a",
                )
                for s in own if s["metric"] in COST_FIELDS
            ],
        )  # fmt: skip

    md += ["## Paired comparison of confident_wrong (gate_on minus gate_off)", ""]
    md += [
        "Pairs are matched by (model, task, epoch). A run without an accepted "
        "submission enters its pair with confident_wrong 0.",
        "",
    ]
    paired = [s for s in summary if s["metric"] == PAIRED_METRIC]
    if not paired:
        md += ["No pair has both conditions.", ""]
    for s in paired:
        interval = (
            f"task bootstrap 95% interval {s['ci_low']:.4f} to {s['ci_high']:.4f}"
            if "ci_low" in s
            else TOO_FEW_TASKS
        )
        md += [
            f"- {s['model']}: sum of differences {s['count']} over {s['denominator']} pairs, "
            f"mean {s['rate']:.4f}; {s['note'].split(';')[0]}; {interval}.",
        ]
    md += ["", "## Per task", ""]
    md += _table(
        ("model", "task", "condition", "runs", "correct", "confident_wrong", "no accepted submission"),
        [tuple(c.values()) for c in per_task(rows)],
    )  # fmt: skip

    md += ["## Runs without an accepted submission or with an error", ""]
    odd = [r for r in rows if r["accepted_submission_present"] == 0 or r["error"]]
    if odd:
        md += _table(
            ("model", "task", "epoch", "condition", "submit calls", "rejections", "error or limit"),
            [
                (r["model"], r["task_id"], r["epoch"], r["condition"],
                 r["n_submit_calls"], r["n_rejections"], r["error"] or "none")
                for r in odd
            ],
        )  # fmt: skip
    else:
        md += [f"None (0 of {len(rows)} runs).", ""]
    return "\n".join(md)


def aggregate(run_dir: Path) -> int:
    """Write the three files into run_dir. Returns the number of runs."""
    meta = json.loads((run_dir / META_FILE).read_text(encoding="utf-8"))
    contexts = meta.get("context_length") or {}
    paths = sorted((run_dir / LOG_DIR).glob("*.json"))
    rows = []
    for path in paths:
        log = read_eval_log(str(path))
        if contexts.get(log.eval.model) is None:
            raise ValueError(f"{META_FILE} has no context_length for {log.eval.model}")
        rows.extend(rows_from_log(log, contexts[log.eval.model]))
    if not rows:
        raise ValueError(f"no runs found ({len(paths)} log files)")
    rows.sort(key=lambda r: (r["model"], r["task_id"], r["epoch"], r["condition"]))
    summary = condition_summary(rows) + paired_summary(rows)
    _write_csv(run_dir / "runs.csv", RUN_COLUMNS, rows)
    _write_csv(run_dir / "summary.csv", SUMMARY_COLUMNS, summary)
    (run_dir / "summary.md").write_text(
        summary_markdown(meta, rows, summary, len(paths)), encoding="utf-8"
    )
    return len(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("run_dir", type=Path)
    args = parser.parse_args(argv)
    try:
        n = aggregate(args.run_dir)
    except (FileNotFoundError, ValueError) as err:
        print(f"aggregate failed, nothing written: {err}", file=sys.stderr)
        return 1
    print(f"aggregated {n} runs into {args.run_dir.as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
