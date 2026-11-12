#!/usr/bin/env python3
"""ПР-10: график «размер TLB -> доля попаданий» на refs_long.txt -> tlb_hit.svg.

Рисует SVG без сторонних библиотек, рядом печатает таблицу с EAT.
"""
import sys

from tlb import eat, simulate
from translate import HERE, load_refs, load_table

SIZES = range(1, 13)


def svg(points, path):
    w, h, left, right, top, bottom = 640, 360, 60, 20, 30, 50
    pw, ph = w - left - right, h - top - bottom
    xmax = max(k for k, _ in points)

    def x(k):
        return left + (k - 1) / (xmax - 1) * pw

    def y(v):
        return top + (1 - v) * ph

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
             f'font-family="sans-serif" font-size="12">',
             f'<rect width="{w}" height="{h}" fill="white"/>',
             f'<text x="{w / 2}" y="18" text-anchor="middle" font-size="14">'
             f'Размер TLB и доля попаданий (refs_long.txt, LRU)</text>']
    for i in range(0, 11):
        v = i / 10
        parts.append(f'<line x1="{left}" y1="{y(v):.1f}" x2="{w - right}" y2="{y(v):.1f}" '
                     f'stroke="#ddd"/>')
        parts.append(f'<text x="{left - 6}" y="{y(v) + 4:.1f}" text-anchor="end">{v:.1f}</text>')
    for k, _ in points:
        parts.append(f'<text x="{x(k):.1f}" y="{h - bottom + 18}" text-anchor="middle">{k}</text>')
    parts.append(f'<text x="{w / 2}" y="{h - 8}" text-anchor="middle">число записей TLB</text>')
    parts.append(f'<text x="14" y="{h / 2}" text-anchor="middle" '
                 f'transform="rotate(-90 14 {h / 2})">доля попаданий</text>')
    line = " ".join(f"{x(k):.1f},{y(v):.1f}" for k, v in points)
    parts.append(f'<polyline points="{line}" fill="none" stroke="#1f77b4" stroke-width="2"/>')
    for k, v in points:
        parts.append(f'<circle cx="{x(k):.1f}" cy="{y(v):.1f}" r="3.5" fill="#1f77b4"/>')
    parts.append("</svg>")
    path.write_text("\n".join(parts) + "\n", encoding="utf-8")


def main():
    table = load_table()
    addrs = load_refs(HERE / "refs_long.txt")
    points = []
    print(f"{'K':>3}  {'hit':>6}  {'miss':>5}  {'h':>6}  {'EAT, нс':>8}")
    for k in SIZES:
        tlb, faults, bad = simulate(addrs, table, k)
        assert faults == 0 and bad == 0
        points.append((k, tlb.hit_ratio))
        print(f"{k:>3}  {tlb.hits:>6}  {tlb.misses:>5}  {tlb.hit_ratio:>6.3f}  {eat(tlb.hit_ratio):>8.1f}")
    svg(points, HERE / "tlb_hit.svg")
    print("график: tlb_hit.svg")
    return 0


if __name__ == "__main__":
    sys.exit(main())
