#!/usr/bin/env python3
"""Проверка ПР-13: эталоны Silberschatz, свойства алгоритмов, голодание SSTF."""
import itertools
import random
import subprocess
import sys
from pathlib import Path

import dynamic
from compare import random_runs
from disk import ALGORITHMS, CYLINDERS, HEAD, QUEUE, REFERENCE

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


for name, fn in ALGORITHMS.items():
    s = fn(QUEUE, HEAD, 1, CYLINDERS)
    check(f"{name}: суммарное перемещение {REFERENCE[name]} (эталон)", s.movement == REFERENCE[name])

check("SCAN доезжает до 199, LOOK нет",
      199 in ALGORITHMS["SCAN"](QUEUE, HEAD).path and 199 not in ALGORITHMS["LOOK"](QUEUE, HEAD).path)
check("C-SCAN возвращается через 0 и засчитывает 199 цилиндров возврата",
      ALGORITHMS["C-SCAN"](QUEUE, HEAD).path[-4:] == [199, 0, 14, 37])

rng = random.Random(3)
served_all = order_ok = sstf_greedy = look_le_scan = clook_le_cscan = True
for _ in range(500):
    head = rng.randrange(CYLINDERS)
    q = [rng.randrange(CYLINDERS) for _ in range(rng.randrange(1, 30))]
    for d in (1, -1):
        res = {n: f(q, head, d, CYLINDERS) for n, f in ALGORITHMS.items()}
        served_all &= all(sorted(s.order) == sorted(q) for s in res.values())
        look_le_scan &= res["LOOK"].movement <= res["SCAN"].movement
        clook_le_cscan &= res["C-LOOK"].movement <= res["C-SCAN"].movement
        # путь головки = сумма |разностей| и проходит через все обслуженные цилиндры
        order_ok &= all(set(s.order) <= set(s.path) for s in res.values())
        s = res["SSTF"]
        pos, left = head, list(q)
        for c in s.order:
            sstf_greedy &= abs(c - pos) == min(abs(x - pos) for x in left)
            left.remove(c)
            pos = c
check("на 1000 случайных очередях каждый алгоритм обслуживает все запросы ровно по разу", served_all)
check("SSTF каждый раз берёт ближайший запрос", sstf_greedy)
check("LOOK никогда не хуже SCAN, C-LOOK никогда не хуже C-SCAN", look_le_scan and clook_le_cscan)
check("путь головки проходит через все обслуженные цилиндры", order_ok)


def brute_min(q, head):
    return min(sum(abs(b - a) for a, b in zip((head,) + p, p)) for p in itertools.permutations(q))


ok = True
for _ in range(100):
    head = rng.randrange(CYLINDERS)
    q = [rng.randrange(CYLINDERS) for _ in range(6)]
    best = brute_min(tuple(q), head)
    ok &= all(f(q, head, 1).movement >= best for f in ALGORITHMS.values())
check("ни один алгоритм не лучше оптимума полного перебора (100 очередей по 6)", ok)

r1, r2 = random_runs(), random_runs()
check("случайные наборы воспроизводятся (seed), 20 прогонов", r1 == r2 and all(len(v) == 20 for v in r1.values()))
mean = {n: sum(v) / len(v) for n, v in r1.items()}
check("на 50 случайных запросах FCFS в разы хуже остальных", all(mean["FCFS"] > 5 * mean[n] for n in mean if n != "FCFS"))

arr = [(0, 190)] + [(0, c) for c in (45, 48, 52, 55, 58)]
rng2 = random.Random(5)
arr += [(k * 4, rng2.randint(40, 60)) for k in range(1, 400)]
done_s, _, _ = dynamic.simulate(dynamic.pick_sstf, arr, head=50)
done_c, _, _ = dynamic.simulate(dynamic.pick_clook, arr, head=50)
t_s = next(d[2] for d in done_s if d[1] == 190)
t_c = next(d[2] for d in done_c if d[1] == 190)
check("голодание: SSTF обслуживает 190 только после конца потока, C-LOOK за 140 единиц",
      t_s > arr[-1][0] and t_c == 140)
check("в динамике все запросы обслужены ровно по разу", len(done_s) == len(done_c) == len(arr))

res = subprocess.run([sys.executable, str(HERE / "disk.py")], capture_output=True, text=True, timeout=30)
check("./disk.py: код 0, у всех шести «ok»", res.returncode == 0 and res.stdout.count("  ok") == 6)
res = subprocess.run([sys.executable, str(HERE / "disk.py"), "-q", "250"], capture_output=True, text=True, timeout=30)
check("цилиндр вне диска: понятная ошибка", res.returncode == 2 and "диапазоне" in res.stderr)

print()
print(f"Проверок: {total}, провалено: {failed}")
sys.exit(1 if failed else 0)
