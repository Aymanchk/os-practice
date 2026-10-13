#!/usr/bin/env python3
"""Зависимость RR от кванта 1...10 на наборе set2."""
import os
import sys
from pathlib import Path

from sched import calculate_metrics, read_processes, simulate

HERE = Path(__file__).resolve().parent
QUANTUMS = range(1, 11)


def collect(path):
    processes = read_processes(path)
    rows = []

    for quantum in QUANTUMS:
        intervals = simulate(processes, "rr", quantum=quantum)
        result = calculate_metrics(processes, intervals)
        rows.append((
            quantum,
            result["avg_waiting"],
            result["switches"],
            result["avg_response"],
        ))

    return rows


def print_table(rows):
    print(
        "| Квант | Среднее ожидание | Переключений "
        "| Среднее время отклика |"
    )
    print("| ---: | ---: | ---: | ---: |")

    for quantum, waiting, switches, response in rows:
        print(
            f"| {quantum} | {waiting:.2f} | {switches} "
            f"| {response:.2f} |"
        )


def print_text_chart(rows):
    print()
    print("Среднее ожидание (один символ # равен 10 единицам времени):")

    for quantum, waiting, _, _ in rows:
        print(f"q={quantum:<2} {'#' * round(waiting / 10)} {waiting:.2f}")

    print()
    print("Переключения контекста (один символ # равен 25 переключениям):")

    for quantum, _, switches, _ in rows:
        print(f"q={quantum:<2} {'#' * round(switches / 25)} {switches}")


def save_png(rows, path):
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib не установлен, PNG не создан")
        return False

    quantums = [row[0] for row in rows]
    waiting = [row[1] for row in rows]
    switches = [row[2] for row in rows]

    figure, left = plt.subplots(figsize=(7, 4))
    left.plot(quantums, waiting, marker="o", color="tab:blue")
    left.set_xlabel("Квант RR")
    left.set_ylabel("Среднее ожидание", color="tab:blue")
    left.set_xticks(list(quantums))

    right = left.twinx()
    right.plot(quantums, switches, marker="s", color="tab:red")
    right.set_ylabel("Число переключений", color="tab:red")

    left.set_title("RR на set2: квант, ожидание и переключения")
    figure.tight_layout()
    figure.savefig(path, dpi=120)
    print(f"График сохранён: {os.path.relpath(path)}")
    return True


def main():
    # Запуск: ./rr_quantum.py [набор] [куда сохранить PNG]
    path = sys.argv[1] if len(sys.argv) > 1 else HERE / "set2.txt"
    png = sys.argv[2] if len(sys.argv) > 2 else HERE / "rr_quantum.png"
    rows = collect(path)
    print_table(rows)
    print_text_chart(rows)
    save_png(rows, png)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
