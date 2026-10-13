#!/usr/bin/env python3
"""Создаёт входные файлы set1, set2, set3 и starve.

set1, set2 и set3 переписаны из методички без изменений (таблица
«Выдаваемые файлы» в ПР-5). starve.txt - собственный набор для
демонстрации голодания и старения.
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent
HEADER = "# PID arrival burst priority"

# Контрольный набор: четвёртое число - приоритет, меньше = важнее.
SET1 = [
    "P1 0 8 2",
    "P2 1 4 3",
    "P3 2 9 1",
    "P4 3 5 4",
]

# 20 процессов, CPU-bound.
SET2 = [
    "P1 0 17 6", "P2 4 17 3", "P3 5 22 1", "P4 6 12 2",
    "P5 7 17 14", "P6 13 8 5", "P7 16 19 12", "P8 18 19 8",
    "P9 20 22 19", "P10 21 21 7", "P11 22 10 9", "P12 22 20 13",
    "P13 24 25 10", "P14 25 23 16", "P15 28 11 15", "P16 31 21 20",
    "P17 32 24 18", "P18 34 23 17", "P19 35 20 11", "P20 40 24 4",
]

# 20 процессов: один длинный P1 и 19 коротких.
SET3 = [
    "P1 0 60 12", "P2 9 4 5", "P3 10 2 11", "P4 13 3 6",
    "P5 13 3 8", "P6 16 1 15", "P7 16 1 19", "P8 17 2 7",
    "P9 18 4 2", "P10 18 4 20", "P11 18 3 18", "P12 21 2 3",
    "P13 22 3 13", "P14 22 4 4", "P15 23 4 10", "P16 23 4 1",
    "P17 26 4 17", "P18 26 1 16", "P19 29 3 14", "P20 30 3 9",
]


def make_starve():
    """Один процесс с плохим приоритетом и непрерывный поток важных."""
    lines = ["LOW 0 5 9"]

    for number in range(1, 31):
        lines.append(f"H{number:02d} {number * 2} 3 1")

    return lines


def write(name, lines):
    text = HEADER + "\n" + "\n".join(lines) + "\n"
    (HERE / name).write_text(text, encoding="utf-8")
    print(f"Создан {name}, процессов: {len(lines)}")


def main():
    write("set1.txt", SET1)
    write("set2.txt", SET2)
    write("set3.txt", SET3)
    write("starve.txt", make_starve())


if __name__ == "__main__":
    main()
