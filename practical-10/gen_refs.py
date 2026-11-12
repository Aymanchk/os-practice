#!/usr/bin/env python3
"""ПР-10: генерация длинной строки обращений с локальностью -> refs_long.txt.

Модель: программа работает в «окне» из WINDOW соседних загруженных страниц
(цикл, массив, стек) и с вероятностью JUMP перескакивает в случайное место.
Используются только страницы, которые есть в таблице, чтобы TLB мерить без
страничных отказов. seed зафиксирован, файл получается одинаковым всегда.
"""
import random
import sys

from translate import HERE, PAGE_SIZE, load_table

SEED = 42
COUNT = 10_000
WINDOW = 3
JUMP = 0.02


def generate(count=COUNT, seed=SEED, window=WINDOW, jump=JUMP):
    rng = random.Random(seed)
    present = sorted(p for p, f in load_table().items() if f is not None)
    start = 0
    out = []
    for _ in range(count):
        if rng.random() < jump:
            start = rng.randrange(len(present) - window + 1)
        page = present[start + rng.randrange(window)]
        out.append(page * PAGE_SIZE + rng.randrange(PAGE_SIZE))
    return out


def main():
    addrs = generate()
    lines = [" ".join(map(str, addrs[i:i + 20])) for i in range(0, len(addrs), 20)]
    header = (f"# {COUNT} обращений, окно {WINDOW} страницы, перескок {JUMP}, seed {SEED} "
              f"(gen_refs.py)\n")
    (HERE / "refs_long.txt").write_text(header + "\n".join(lines) + "\n", encoding="utf-8")
    pages = {a // PAGE_SIZE for a in addrs}
    print(f"refs_long.txt: {len(addrs)} обращений, разных страниц {len(pages)}: {sorted(pages)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
