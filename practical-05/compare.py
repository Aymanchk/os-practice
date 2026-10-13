#!/usr/bin/env python3
"""Сравнение всех алгоритмов на наборах set1, set2, set3."""
from pathlib import Path

from sched import calculate_metrics, read_processes, simulate

HERE = Path(__file__).resolve().parent

SETS = ["set1.txt", "set2.txt", "set3.txt"]

ALGORITHMS = [
    ("FCFS", "fcfs", {}),
    ("SJF", "sjf", {}),
    ("SRTF", "srtf", {}),
    ("Priority", "priority", {}),
    ("RR, q=3", "rr", {"quantum": 3}),
]


def main():
    for number, name in enumerate(SETS):
        processes = read_processes(HERE / name)

        if number > 0:
            print()

        print(f"### {name} (процессов: {len(processes)})")
        print()
        print(
            "| Алгоритм | Среднее ожидание | Средний оборот "
            "| Среднее время отклика | Загрузка CPU, % "
            "| Переключения |"
        )
        print("| --- | ---: | ---: | ---: | ---: | ---: |")

        for title, algorithm, params in ALGORITHMS:
            intervals = simulate(processes, algorithm, **params)
            result = calculate_metrics(processes, intervals)
            print(
                f"| {title} "
                f"| {result['avg_waiting']:.2f} "
                f"| {result['avg_turnaround']:.2f} "
                f"| {result['avg_response']:.2f} "
                f"| {result['utilization']:.1f} "
                f"| {result['switches']} |"
            )


if __name__ == "__main__":
    main()
