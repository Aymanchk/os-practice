#!/usr/bin/env python3
"""Сверка результатов на set1 со всеми эталонами из методички."""
from pathlib import Path

from sched import calculate_metrics, read_processes, simulate

HERE = Path(__file__).resolve().parent

# Эталоны из раздела «Исходные данные» ПР-5:
# (название, алгоритм, параметры, среднее ожидание, средний оборот)
CHECKS = [
    ("FCFS", "fcfs", {}, 8.75, 15.25),
    ("SJF", "sjf", {}, 7.75, 14.25),
    ("SRTF", "srtf", {}, 6.5, 13.0),
    ("Priority", "priority", {}, 10.75, 17.25),
    ("RR, q=3", "rr", {"quantum": 3}, 13.5, 20.0),
]


def main():
    processes = read_processes(HERE / "set1.txt")
    failed = False

    for title, algorithm, params, wait, turnaround in CHECKS:
        intervals = simulate(processes, algorithm, **params)
        result = calculate_metrics(processes, intervals)
        ok = (
            abs(result["avg_waiting"] - wait) < 1e-9
            and abs(result["avg_turnaround"] - turnaround) < 1e-9
        )
        status = "OK" if ok else "ОШИБКА"
        failed = failed or not ok
        print(
            f"{title:<9} ожидание {result['avg_waiting']:.2f} "
            f"(эталон {wait:.2f}), оборот {result['avg_turnaround']:.2f} "
            f"(эталон {turnaround:.2f}) {status}"
        )

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
