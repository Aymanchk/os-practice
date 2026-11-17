#!/usr/bin/env python3
"""Проверка ПР-11: эталоны УМК, аномалия Белади, независимые реализации алгоритмов."""
import random
import subprocess
import sys
from collections import deque
from pathlib import Path

from compare import generate
from replace import BELADY, REFERENCE, clock, fifo, lru, optimal

HERE = Path(__file__).resolve().parent
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


# ---------- независимые эталоны ----------

def ref_lru(refs, n):
    """LRU как стек: недавняя страница в конце списка."""
    stack, faults = [], 0
    for p in refs:
        if p in stack:
            stack.remove(p)
        else:
            faults += 1
            if len(stack) == n:
                stack.pop(0)
        stack.append(p)
    return faults


def ref_second_chance(refs, n):
    """Второй шанс через очередь: голова с битом 1 уходит в хвост с битом 0."""
    q, bit, faults = deque(), {}, 0
    for p in refs:
        if p in bit:
            bit[p] = 1
            continue
        faults += 1
        if len(q) == n:
            while bit[q[0]]:
                bit[q[0]] = 0
                q.rotate(-1)
            del bit[q.popleft()]
        q.append(p)
        bit[p] = 1
    return faults


def min_faults(refs, n):
    """Минимально возможное число отказов полным перебором всех решений о вытеснении."""
    states = {frozenset(): 0}
    for p in refs:
        nxt = {}
        for s, f in states.items():
            if p in s:
                cands = [(s, f)]
            elif len(s) < n:
                cands = [(s | {p}, f + 1)]
            else:
                cands = [((s - {v}) | {p}, f + 1) for v in s]
            for s2, f2 in cands:
                if f2 < nxt.get(s2, 10 ** 9):
                    nxt[s2] = f2
        states = nxt
    return min(states.values())


# ---------- эталоны из УМК ----------
check("контрольная строка, 3 кадра: FIFO 15", fifo(REFERENCE, 3).faults == 15)
check("контрольная строка, 3 кадра: LRU 12", lru(REFERENCE, 3).faults == 12)
check("контрольная строка, 3 кадра: Optimal 9", optimal(REFERENCE, 3).faults == 9)
check("контрольная строка, 3 кадра: Clock 14", clock(REFERENCE, 3).faults == 14)
check("4 кадра: FIFO 10, LRU 8, Optimal 8, Clock 9",
      [f(REFERENCE, 4).faults for f in (fifo, lru, optimal, clock)] == [10, 8, 8, 9])
check("при 6 и более кадрах у всех 6 отказов (6 разных страниц)",
      all(f(REFERENCE, n).faults == 6 for f in (fifo, lru, optimal, clock) for n in (6, 7, 8)))

# ---------- аномалия Белади ----------
check("Белади: FIFO 3 кадра 9 отказов, 4 кадра 10", (fifo(BELADY, 3).faults, fifo(BELADY, 4).faults) == (9, 10))
check("LRU и Optimal на строке Белади не растут с числом кадров",
      all(f(BELADY, n).faults >= f(BELADY, n + 1).faults for f in (lru, optimal) for n in range(1, 7)))

# ---------- независимые реализации на случайных строках ----------
rng = random.Random(7)
ok_lru = ok_clock = ok_opt = ok_order = ok_fifo1 = True
for _ in range(300):
    refs = [rng.randrange(6) for _ in range(rng.randrange(5, 40))]
    for n in (1, 2, 3, 4, 5):
        ok_lru &= lru(refs, n).faults == ref_lru(refs, n)
        ok_clock &= clock(refs, n).faults == ref_second_chance(refs, n)
        o = optimal(refs, n).faults
        ok_order &= o <= min(fifo(refs, n).faults, lru(refs, n).faults, clock(refs, n).faults)
    ok_fifo1 &= fifo(refs, 1).faults == clock(refs, 1).faults == lru(refs, 1).faults
for _ in range(150):
    refs = [rng.randrange(5) for _ in range(rng.randrange(4, 14))]
    for n in (2, 3):
        ok_opt &= optimal(refs, n).faults == min_faults(refs, n)
check("LRU совпадает с эталонным стеком на 300 случайных строках", ok_lru)
check("Clock совпадает с «вторым шансом» через очередь на 300 строках", ok_clock)
check("Optimal равен минимуму полного перебора на 150 коротких строках", ok_opt)
check("Optimal никогда не хуже FIFO, LRU и Clock", ok_order)
check("при 1 кадре все алгоритмы дают одинаково", ok_fifo1)

# ---------- типичные ошибки ----------
check("LRU обновляет время при попадании: 1 2 1 3 при 2 кадрах вытесняет 2",
      lru([1, 2, 1, 3], 2, trace=True).steps[-1][2] == [1, 3])
check("Optimal смотрит вперёд: 1 2 3 1 при 2 кадрах вытесняет 2",
      optimal([1, 2, 3, 1], 2, trace=True).steps[2][3] == 2)
check("повторное обращение к загруженной странице не отказ", fifo([5, 5, 5, 5], 1).faults == 1)
check("Clock: стрелка сдвигается после замены (1 2 3 4 при 2 кадрах: 4 отказа, 4 на месте 2)",
      clock([1, 2, 3, 4], 2, trace=True).steps[-1][2] == [3, 4])

# ---------- строки по 1000 обращений ----------
s1, s2 = generate(), generate()
check("строки random и locality воспроизводятся (seed)", s1 == s2 and all(len(v) == 1000 for v in s1.values()))
check("на строке с локальностью отказов меньше у всех алгоритмов",
      all(f(s1["locality"], 5).faults < f(s1["random"], 5).faults for f in (fifo, lru, optimal, clock)))
check("Clock делает меньше работы на обращение, чем LRU",
      all(clock(r, 5).work < lru(r, 5).work for r in s1.values()))

# ---------- командная строка ----------
res = subprocess.run([sys.executable, str(HERE / "replace.py")], capture_output=True, text=True, timeout=30)
row3 = [line.split() for line in res.stdout.splitlines() if line.split()[:1] == ["3"]]
check("python3 replace.py: код 0 и строка «3 15 12 9 14»", res.returncode == 0 and row3 == [["3", "15", "12", "9", "14"]])
res = subprocess.run([sys.executable, str(HERE / "replace.py"), "-f", "0"], capture_output=True, text=True, timeout=30)
check("replace.py -f 0: понятная ошибка", res.returncode == 2 and "не меньше 1" in res.stderr)

print()
print(f"Проверок: {total}, провалено: {failed}")
sys.exit(1 if failed else 0)
