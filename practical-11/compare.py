#!/usr/bin/env python3
"""ПР-11, уровень B: две строки по 1000 обращений к 20 страницам, 5 кадров.

random.txt   - каждое обращение к случайной странице 0..19;
locality.txt - обращения в окне из 4 соседних страниц, с вероятностью 5%
               окно перескакивает в случайное место.
seed фиксирован, поэтому строки одинаковые при каждом запуске. Здесь же
сравниваются LRU и Clock по числу элементарных действий на одно обращение.
"""
import random
import sys
import time
from pathlib import Path

from replace import ALGORITHMS

HERE = Path(__file__).resolve().parent
SEED = 2026
COUNT = 1000
PAGES = 20
FRAMES = 5
WINDOW = 4
JUMP = 0.05


def random_string(rng):
    return [rng.randrange(PAGES) for _ in range(COUNT)]


def locality_string(rng):
    out, start = [], 0
    for _ in range(COUNT):
        if rng.random() < JUMP:
            start = rng.randrange(PAGES - WINDOW + 1)
        out.append(start + rng.randrange(WINDOW))
    return out


def generate():
    rng = random.Random(SEED)
    return {"random": random_string(rng), "locality": locality_string(rng)}


def save(strings):
    for name, refs in strings.items():
        lines = [" ".join(map(str, refs[i:i + 25])) for i in range(0, len(refs), 25)]
        (HERE / f"{name}.txt").write_text(
            f"# {COUNT} обращений к {PAGES} страницам, seed {SEED} (compare.py)\n"
            + "\n".join(lines) + "\n", encoding="utf-8")


def main():
    strings = generate()
    save(strings)
    print(f"Строки по {COUNT} обращений к {PAGES} страницам, seed {SEED}, кадров {FRAMES}")
    print(f"{'строка':>9}  " + "  ".join(f"{n:>7}" for n in ALGORITHMS) + "   доля отказов LRU")
    for name, refs in strings.items():
        row = [ALGORITHMS[a](refs, FRAMES).faults for a in ALGORITHMS]
        print(f"{name:>9}  " + "  ".join(f"{v:>7}" for v in row) + f"   {row[1] / COUNT:.1%}")
    print()
    print("Работа на одно обращение (элементарные действия), 5 кадров:")
    print(f"{'строка':>9}  {'LRU':>6}  {'Clock':>6}")
    for name, refs in strings.items():
        lw = ALGORITHMS["LRU"](refs, FRAMES).work / COUNT
        cw = ALGORITHMS["Clock"](refs, FRAMES).work / COUNT
        print(f"{name:>9}  {lw:>6.2f}  {cw:>6.2f}")
    print()
    print("Время на 1000 обращений, мс (медиана 7 прогонов, Python):")
    for name, refs in strings.items():
        cells = []
        for algo in ALGORITHMS:
            runs = []
            for _ in range(7):
                t = time.perf_counter()
                ALGORITHMS[algo](refs, FRAMES)
                runs.append((time.perf_counter() - t) * 1000)
            cells.append(f"{algo} {sorted(runs)[3]:.2f}")
        print(f"{name:>9}  " + ", ".join(cells))
    return 0


if __name__ == "__main__":
    sys.exit(main())
