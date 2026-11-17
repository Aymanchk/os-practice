#!/usr/bin/env python3
"""ПР-11, уровень B: аномалия Белади на строке 1 2 3 4 1 2 5 1 2 3 4 5.

Печатает число отказов при 1…7 кадрах для всех алгоритмов, отмечает, где
добавление кадра увеличило число отказов, и показывает пошагово FIFO при 3 и 4
кадрах. Для LRU и Optimal дополнительно проверяется свойство включения
(стековость): содержимое памяти из n кадров всегда входит в содержимое из n+1.
"""
import sys

from replace import ALGORITHMS, BELADY, fifo, print_trace

FRAMES = range(1, 8)


def anomalies(counts):
    return [(n, counts[i], counts[i + 1]) for i, n in enumerate(FRAMES)
            if i + 1 < len(counts) and counts[i + 1] > counts[i]]


def inclusion(fn, refs, n):
    """True, если после каждого шага множество страниц при n кадрах ⊆ множества при n+1."""
    a, b = fn(refs, n, trace=True).steps, fn(refs, n + 1, trace=True).steps
    return all(set(x[2]) <= set(y[2]) for x, y in zip(a, b))


def main():
    print("Строка:", " ".join(map(str, BELADY)))
    print(f"{'Кадры':>5}  " + "  ".join(f"{n:>7}" for n in ALGORITHMS))
    counts = {name: [fn(BELADY, n).faults for n in FRAMES] for name, fn in ALGORITHMS.items()}
    for i, n in enumerate(FRAMES):
        print(f"{n:>5}  " + "  ".join(f"{counts[name][i]:>7}" for name in ALGORITHMS))
    print()
    for name, c in counts.items():
        found = anomalies(c)
        if found:
            text = ", ".join(f"{n} кадра: {a} -> {n + 1} кадра: {b}" for n, a, b in found)
            print(f"{name:>7}: АНОМАЛИЯ ({text})")
        else:
            print(f"{name:>7}: аномалии нет, отказы не растут с числом кадров")
    print()
    for name in ALGORITHMS:
        ok = all(inclusion(ALGORITHMS[name], BELADY, n) for n in range(1, 7))
        print(f"{name:>7}: свойство включения M(n) ⊆ M(n+1) {'выполняется' if ok else 'НАРУШЕНО'}")
    print()
    for n in (3, 4):
        print(f"=== FIFO, {n} кадра")
        print_trace("FIFO", fifo(BELADY, n, trace=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
