#!/usr/bin/env python3
"""ПР-13, уровень B: суммарное перемещение на контрольном наборе и на случайных
наборах из 50 запросов (среднее по 20 генерациям) -> movement.png."""
import random
import statistics
import sys
from pathlib import Path

from disk import ALGORITHMS, CYLINDERS, HEAD, QUEUE

HERE = Path(__file__).resolve().parent
SEED = 13
RUNS = 20
REQUESTS = 50


def random_runs():
    rng = random.Random(SEED)
    results = {name: [] for name in ALGORITHMS}
    for _ in range(RUNS):
        head = rng.randrange(CYLINDERS)
        queue = [rng.randrange(CYLINDERS) for _ in range(REQUESTS)]
        for name, fn in ALGORITHMS.items():
            results[name].append(fn(queue, head, 1, CYLINDERS).movement)
    return results


def main():
    control = {name: fn(QUEUE, HEAD, 1, CYLINDERS).movement for name, fn in ALGORITHMS.items()}
    rnd = random_runs()
    print(f"Случайные наборы: {RUNS} генераций по {REQUESTS} запросов, головка случайная, "
          f"направление вверх, seed {SEED}")
    print(f"{'алгоритм':>8}  {'контроль':>8}  {'среднее':>8}  {'ст.откл':>7}  {'мин':>5}  {'макс':>5}")
    for name in ALGORITHMS:
        v = rnd[name]
        print(f"{name:>8}  {control[name]:>8}  {statistics.mean(v):>8.1f}  "
              f"{statistics.stdev(v):>7.1f}  {min(v):>5}  {max(v):>5}")
    best = min(ALGORITHMS, key=lambda n: statistics.mean(rnd[n]))
    print(f"меньше всего в среднем: {best}")

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib не установлен, график не построен")
        return 0
    names = list(ALGORITHMS)
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    axes[0].bar(names, [control[n] for n in names], color="#4c78a8")
    axes[0].set_title("Контрольный набор (8 запросов, головка 53)")
    for i, n in enumerate(names):
        axes[0].text(i, control[n] + 8, str(control[n]), ha="center", fontsize=9)
    means = [statistics.mean(rnd[n]) for n in names]
    errs = [statistics.stdev(rnd[n]) for n in names]
    axes[1].bar(names, means, yerr=errs, capsize=4, color="#f58518")
    axes[1].set_title(f"Случайные наборы: {REQUESTS} запросов, среднее по {RUNS}")
    for ax in axes:
        ax.set_ylabel("суммарное перемещение, цилиндров")
        ax.tick_params(axis="x", labelrotation=20)
        ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(HERE / "movement.png", dpi=120)
    print("график: movement.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
