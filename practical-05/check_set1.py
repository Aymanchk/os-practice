#!/usr/bin/env python3
"""Сверка результатов на set1 с эталоном из методички."""
from sched import calculate_metrics, read_processes, simulate

# Для FCFS ожидание и оборот посчитаны вручную: P1 0-8, P2 8-12,
# P3 12-21, P4 21-26. Эталон из методички для FCFS (9.25 и 15.75)
# с этим расчётом не совпадает, поэтому здесь стоят числа ручного расчёта.
CHECKS = [
    ("FCFS", "fcfs", {}, 8.75, 15.25),
    ("SRTF", "srtf", {}, 6.5, 13.0),
    ("RR, q=3", "rr", {"quantum": 3}, 13.5, 20.0),
]


def main():
    processes = read_processes("set1.txt")
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
            f"{title:<8} ожидание {result['avg_waiting']:.2f} "
            f"(ждали {wait:.2f}), оборот {result['avg_turnaround']:.2f} "
            f"(ждали {turnaround:.2f}) {status}"
        )

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
