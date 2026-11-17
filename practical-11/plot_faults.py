#!/usr/bin/env python3
"""ПР-11, уровень B: график «число кадров (1…8) → число отказов» -> faults.png."""
import sys
from pathlib import Path

from replace import ALGORITHMS, REFERENCE

HERE = Path(__file__).resolve().parent
FRAMES = range(1, 9)


def table():
    return {name: [fn(REFERENCE, n).faults for n in FRAMES] for name, fn in ALGORITHMS.items()}


def main():
    data = table()
    print(f"{'Кадры':>5}  " + "  ".join(f"{n:>7}" for n in data))
    for i, n in enumerate(FRAMES):
        print(f"{n:>5}  " + "  ".join(f"{data[name][i]:>7}" for name in data))
    print(f"разных страниц в строке: {len(set(REFERENCE))}")

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib не установлен: pip install -r requirements.txt; таблица выше, графика нет")
        return 0
    fig, ax = plt.subplots(figsize=(7, 4.2))
    styles = {"FIFO": "o-", "LRU": "s-", "Optimal": "^-", "Clock": "d--"}
    for name, ys in data.items():
        ax.plot(list(FRAMES), ys, styles[name], label=name)
    ax.set_xlabel("число кадров")
    ax.set_ylabel("число страничных отказов")
    ax.set_title("Контрольная строка Silberschatz (20 обращений, 6 разных страниц)")
    ax.set_xticks(list(FRAMES))
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(HERE / "faults.png", dpi=120)
    print("график: faults.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
