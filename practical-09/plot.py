#!/usr/bin/env python3
"""График для уровня B: внешняя фрагментация по ходу ops2 и число отказов у четырёх подходов.

Рисует SVG без сторонних библиотек (matplotlib не нужен), GitHub показывает его прямо в README.
Запуск: python3 plot.py  ->  fragmentation.svg
"""
import sys

from compare import approaches, trace
from memsim import load

COLORS = {"first +merge": "#2a6fdb", "best +merge": "#1a9e5c",
          "worst +merge": "#d9822b", "buddy": "#b0399b"}
W, H = 900, 430
WINDOW = 10                                    # сглаживание: среднее по 10 соседним шагам
LEFT, RIGHT, TOP, BOTTOM = 60, 250, 50, 60     # поля основного графика (справа место под отказы)


def smooth(values):
    """Скользящее среднее: значение на шаге i - среднее последних WINDOW шагов."""
    result = []
    for i in range(len(values)):
        part = values[max(0, i - WINDOW + 1):i + 1]
        result.append(sum(part) / len(part))
    return result


def line_chart(series, steps):
    plot_w, plot_h = W - LEFT - RIGHT, H - TOP - BOTTOM
    parts = [f'<rect x="{LEFT}" y="{TOP}" width="{plot_w}" height="{plot_h}" fill="#fafafa" stroke="#ccc"/>']
    for k in range(0, 11, 2):                   # горизонтальные линии 0, 0.2 ... 1.0
        y = TOP + plot_h - plot_h * k / 10
        parts.append(f'<line x1="{LEFT}" y1="{y:.1f}" x2="{LEFT + plot_w}" y2="{y:.1f}" stroke="#e3e3e3"/>')
        parts.append(f'<text x="{LEFT - 8}" y="{y + 4:.1f}" font-size="12" text-anchor="end">{k / 10:.1f}</text>')
    for step in range(0, steps + 1, 50):        # подписи по оси шагов
        x = LEFT + plot_w * step / steps
        parts.append(f'<text x="{x:.1f}" y="{TOP + plot_h + 18}" font-size="12" text-anchor="middle">{step}</text>')
    parts.append(f'<text x="{LEFT + plot_w / 2}" y="{H - 18}" font-size="13" text-anchor="middle">'
                 f'номер операции в ops2.txt (линии сглажены: среднее по {WINDOW} шагам)</text>')
    parts.append(f'<text x="18" y="{TOP + plot_h / 2}" font-size="13" text-anchor="middle" '
                 f'transform="rotate(-90 18 {TOP + plot_h / 2})">внешняя фрагментация</text>')
    for name, (_, ext, _) in series.items():
        points = " ".join(f"{LEFT + plot_w * (i + 1) / steps:.1f},{TOP + plot_h - plot_h * v:.1f}"
                          for i, v in enumerate(smooth(ext)))
        parts.append(f'<polyline fill="none" stroke="{COLORS[name]}" stroke-width="1.8" points="{points}"/>')
    return parts


def bars(series):
    x0, width = W - RIGHT + 40, RIGHT - 70
    top = TOP + 30
    biggest = max(r for r, _, _ in series.values())
    parts = [f'<text x="{x0}" y="{TOP + 12}" font-size="13" font-weight="bold">отказов и средняя фр.</text>']
    for i, (name, (refused, ext, _)) in enumerate(series.items()):
        y = top + i * 62
        bar = width * refused / biggest
        avg = sum(ext) / len(ext)
        parts.append(f'<text x="{x0}" y="{y}" font-size="12">{name}</text>')
        parts.append(f'<rect x="{x0}" y="{y + 6}" width="{bar:.1f}" height="16" fill="{COLORS[name]}"/>')
        parts.append(f'<text x="{x0 + bar + 6:.1f}" y="{y + 19}" font-size="12">{refused}</text>')
        parts.append(f'<text x="{x0}" y="{y + 38}" font-size="11" fill="#555">средняя внешняя {avg:.2f}</text>')
    return parts


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "ops2.txt"
    out = sys.argv[2] if len(sys.argv) > 2 else "fragmentation.svg"
    ops = load(path)
    series = {name: trace(ops, make, alloc, free, stats)
              for name, make, alloc, free, stats in approaches()}
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
             f'viewBox="0 0 {W} {H}" font-family="sans-serif">',
             f'<rect width="{W}" height="{H}" fill="white"/>',
             f'<text x="{LEFT}" y="28" font-size="16" font-weight="bold">'
             f'Четыре подхода на {path}: внешняя фрагментация после каждой операции</text>']
    parts += line_chart(series, len(ops))
    parts += bars(series)
    parts.append("</svg>")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(parts) + "\n")
    print(f"записан {out}: {len(series)} линии по {len(ops)} шагов")
    for name, (refused, ext, internal) in series.items():
        print(f"  {name:<13} отказов {refused:>3}, средняя внешняя {sum(ext) / len(ext):.2f}, "
              f"средняя внутренняя {sum(internal) / len(internal):.0f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
