#!/usr/bin/env python3
"""Создаёт наборы процессов set1, set2, set3 и starve.

Числа берутся из собственного генератора, поэтому результат
одинаков на любой версии Python.
"""
from pathlib import Path

SET1 = """# PID arrival burst priority
P1 0 8 2
P2 1 4 1
P3 2 9 3
P4 3 5 2
"""


class Lcg:
    def __init__(self, seed):
        self.state = seed

    def next(self, low, high):
        self.state = (self.state * 1103515245 + 12345) % 2**31
        return low + self.state % (high - low + 1)


def write(name, lines):
    text = "# PID arrival burst priority\n" + "\n".join(lines) + "\n"
    Path(name).write_text(text, encoding="utf-8")
    print(f"Создан {name}: {len(lines)} процессов")


def make_set2():
    """20 процессов, длинные CPU-bound burst."""
    rng = Lcg(2)
    lines = []

    for number in range(1, 21):
        arrival = (number - 1) * 2 + rng.next(0, 1)
        burst = rng.next(15, 40)
        priority = rng.next(1, 5)
        lines.append(f"P{number} {arrival} {burst} {priority}")

    return lines


def make_set3():
    """19 коротких процессов и один длинный, который приходит первым."""
    rng = Lcg(3)
    lines = ["P1 0 60 3"]

    for number in range(2, 21):
        arrival = rng.next(1, 30)
        burst = rng.next(1, 4)
        priority = rng.next(1, 5)
        lines.append(f"P{number} {arrival} {burst} {priority}")

    return lines


def make_starve():
    """Один процесс с плохим приоритетом и непрерывный поток важных."""
    lines = ["LOW 0 5 9"]

    for number in range(1, 31):
        lines.append(f"H{number:02d} {number * 2} 3 1")

    return lines


def main():
    Path("set1.txt").write_text(SET1, encoding="utf-8")
    print("Создан set1.txt: 4 процесса")
    write("set2.txt", make_set2())
    write("set3.txt", make_set3())
    write("starve.txt", make_starve())


if __name__ == "__main__":
    main()
