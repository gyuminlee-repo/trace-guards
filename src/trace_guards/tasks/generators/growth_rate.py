"""Specific growth rate from an OD600 time course with lag and stationary points outside the window."""

from __future__ import annotations

import math

from trace_guards.tasks.generators._common import ABSTAIN, ensure_distinct, rng_for
from trace_guards.tasks.spec import TaskSpec

TASK_ID = "growth_rate"
FILE = "growth.tsv"
TOLERANCE = 0.005


def _prompt(start: float, end: float) -> str:
    return (
        f"The file `{FILE}` records the OD600 of a batch culture over time (columns "
        "`time_h` and `od600`). Compute the specific growth rate as the least-squares "
        "slope of ln(OD600) against time, using only the time points from "
        f"{start:.1f} h to {end:.1f} h inclusive, which is the exponential phase. "
        "Report the rate in per hour, rounded to 3 decimal places. " + ABSTAIN
    )


def _slope(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    sx, sy = sum(xs), sum(ys)
    sxx = sum(x * x for x in xs)
    sxy = sum(x * y for x, y in zip(xs, ys))
    return (n * sxy - sx * sy) / (n * sxx - sx * sx)


def _generate(seed: int) -> tuple[TaskSpec, dict[str, str]]:
    rng = rng_for(TASK_ID, seed)
    mu = rng.uniform(0.25, 0.6)
    lag = rng.choice((1.5, 2.0, 2.5))
    start = lag + 0.5
    end = start + rng.choice((3.0, 3.5, 4.0))
    od0 = rng.uniform(0.02, 0.05)
    plateau = od0 * math.exp(mu * (end + 0.5 - lag))

    rows: list[tuple[str, str]] = []
    for step in range(29):
        t = step * 0.5
        if t <= lag:
            od = od0
        elif t <= end + 0.5:
            od = od0 * math.exp(mu * (t - lag))
        else:
            # Growth levels off after the window: the culture enters stationary phase.
            od = plateau * (1.6 - 0.6 * math.exp(-(t - end - 0.5)))
        rows.append((f"{t:.1f}", f"{od * rng.gauss(1.0, 0.01):.4f}"))

    # The target is the fit to the values as written, not the planted rate.
    times = [float(t) for t, _ in rows]
    ods = [float(od) for _, od in rows]
    window = [i for i, t in enumerate(times) if start <= t <= end]
    window_times = [times[i] for i in window]
    rate = _slope(window_times, [math.log(ods[i]) for i in window])

    spec = TaskSpec(
        id=TASK_ID,
        family="growth",
        kind="ordinary",
        trap=None,
        prompt=_prompt(start, end),
        files={FILE: "time_h\tod600\n" + "".join(f"{t}\t{od}\n" for t, od in rows)},
        expected_status="answered",
        target=f"{rate:.3f}",
        tolerance=TOLERANCE,
        requires_citation=False,
        tools=("python",),
    )
    wrong = {
        "all_time_points": f"{_slope(times, [math.log(od) for od in ods]):.3f}",
        "log10_instead_of_ln": f"{rate / math.log(10):.3f}",
        "od_not_log_transformed": f"{_slope(window_times, [ods[i] for i in window]):.3f}",
        "doubling_time": f"{math.log(2) / rate:.3f}",
    }
    ensure_distinct(spec, wrong)
    return spec, wrong


def build(seed: int) -> TaskSpec:
    return _generate(seed)[0]


def distractors(seed: int) -> dict[str, str]:
    return _generate(seed)[1]
