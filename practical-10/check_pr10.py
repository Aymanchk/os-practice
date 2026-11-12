#!/usr/bin/env python3
"""Проверка ПР-10: трансляция адресов, TLB с LRU, EAT, двухуровневая таблица."""
import random
import subprocess
import sys

from gen_refs import generate
from tlb import TLB, eat, simulate
from translate import (ADDRESS_SPACE, PAGE_SIZE, BadAddress, PageFault, HERE,
                       load_refs, load_table, split, translate)
from twolevel import TwoLevel, table_sizes

total = 0
failed = 0


def check(name, condition):
    global total, failed
    total += 1
    if condition:
        print(f"[ok]     {name}")
    else:
        failed += 1
        print(f"[ОШИБКА] {name}")


def raises(exc, fn, *args):
    try:
        fn(*args)
    except exc:
        return True
    return False


table = load_table()
refs = load_refs()

# ---------- трансляция ----------
small = {0: 5, 1: 2, 2: 7, 3: 0}                      # таблица из условия варианта A
check("1200 -> стр 1, смещ 176 -> физ 2224", split(1200) == (1, 176) and translate(1200, small) == 2224)
check("3100 -> стр 3, смещ 28 -> физ 28", split(3100) == (3, 28) and translate(3100, small) == 28)
check("5000 -> стр 4: страничный отказ", raises(PageFault, translate, 5000, small))
check("первые три адреса refs.txt - контрольные 1200, 3100, 5000", refs[:3] == [1200, 3100, 5000])
check("адрес 16384 и -1 - неверные", raises(BadAddress, split, ADDRESS_SPACE) and raises(BadAddress, split, -1))
check("границы страницы: 1023 -> (0, 1023), 1024 -> (1, 0)", split(1023) == (0, 1023) and split(1024) == (1, 0))

rng = random.Random(1)
good = True
for _ in range(5000):
    a = rng.randrange(ADDRESS_SPACE)
    page, off = a >> 10, a & (PAGE_SIZE - 1)          # то же самое сдвигом и маской
    if table[page] is None:
        good &= raises(PageFault, translate, a, table)
    else:
        good &= translate(a, table) == (table[page] << 10) | off
check("5000 случайных адресов: деление/остаток совпадает со сдвигом/маской", good)

# ---------- TLB ----------
t = TLB(2)
t.insert(1, 10); t.insert(2, 20); t.lookup(1); t.insert(3, 30)
check("LRU: после обращения к 1 вытесняется 2, а не 1", list(t.entries) == [1, 3])


def brute_lru(pages, k):
    """Независимый эталон: стек LRU списком."""
    stack, hits = [], 0
    for p in pages:
        if p in stack:
            hits += 1
            stack.remove(p)
        elif len(stack) == k:
            stack.pop(0)
        stack.append(p)
    return hits


long_refs = load_refs(HERE / "refs_long.txt")
ok = True
for k in (1, 2, 3, 4, 8, 12):
    tlb, faults, bad = simulate(long_refs, table, k)
    ok &= tlb.hits == brute_lru([a // PAGE_SIZE for a in long_refs], k) and faults == 0
check("TLB на refs_long.txt совпадает с эталонным LRU-стеком при K = 1, 2, 3, 4, 8, 12", ok)

hits_by_k = [simulate(long_refs, table, k)[0].hits for k in range(1, 13)]
check("доля попаданий не убывает с ростом TLB (LRU - стековый алгоритм)",
      all(a <= b for a, b in zip(hits_by_k, hits_by_k[1:])))
tlb4, faults4, bad4 = simulate(refs, table, 4)
check("refs.txt, K = 4: 14 hit, 15 miss, 2 отказа, 1 неверный адрес",
      (tlb4.hits, tlb4.misses, faults4, bad4) == (14, 15, 2, 1))
check("refs_long.txt воспроизводится тем же seed", generate() == long_refs)

# ---------- EAT ----------
check("EAT(1) = 110, EAT(0) = 210, EAT(0.9) = 120", (eat(1), eat(0), round(eat(0.9), 6)) == (110, 210, 120))
check("EAT для двухуровневой таблицы при промахе = 310", eat(0, levels=2) == 310)

# ---------- двухуровневая таблица ----------
tl = TwoLevel(table)
ok = True
for a in range(0, ADDRESS_SPACE, 7):
    if table[a // PAGE_SIZE] is None:
        ok &= raises(PageFault, tl.translate, a)
    else:
        phys, n = tl.translate(a)
        ok &= phys == translate(a, table) and n == 3
check("двухуровневая даёт те же адреса, что и одноуровневая, за 3 обращения к памяти", ok)
flat, outer, inner, regions, used = table_sizes()
check("32 бита / 4 КБ: плоская таблица 4 МБ, двухуровневая 20 КБ", flat == 4 << 20 and outer + len(used) * inner == 20 << 10)

# ---------- командная строка ----------
res = subprocess.run([sys.executable, str(HERE / "translate.py"), "1200", "3100", "5000"],
                     capture_output=True, text=True, timeout=30)
check("translate.py 1200 3100 5000: код 0, 2224 и 28 в выводе, отказ для 5000",
      res.returncode == 0 and "= 2224" in res.stdout and "= 28" in res.stdout and "отсутствует" in res.stdout)
res = subprocess.run([sys.executable, str(HERE / "tlb.py"), "-k", "0"], capture_output=True, text=True, timeout=30)
check("tlb.py -k 0: понятная ошибка, а не зависание", res.returncode != 0 and "не меньше 1" in res.stderr)

print()
print(f"Проверок: {total}, провалено: {failed}")
sys.exit(1 if failed else 0)
