#!/usr/bin/env python3
"""Проверка ПР-8: банкир, детектор циклов, TrackedLock, философы."""
import itertools
import random
import subprocess
import sys
import threading
import time

import banker
import deadlock_detector
import philosophers
import tracked_lock
from waitgraph import find_cycle

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


def make(path):
    return banker.Banker(*banker.read_state(path))


def brute_force_safe(avail, alloc, maxim):
    """Независимая проверка: есть ли хоть один порядок завершения процессов."""
    n, m = len(alloc), len(avail)
    for perm in itertools.permutations(range(n)):
        work = list(avail)
        good = True
        for i in perm:
            if any(maxim[i][j] - alloc[i][j] > work[j] for j in range(m)):
                good = False
                break
            work = [work[j] + alloc[i][j] for j in range(m)]
        if good:
            return True
    return False


def has_cycle_by_reduction(graph):
    """Независимый способ: убираем вершины без исходящих рёбер, пока можно."""
    nodes = set(graph) | {w for targets in graph.values() for w in targets}
    edges = {v: set(graph.get(v, ())) for v in nodes}
    changed = True
    while changed:
        changed = False
        for v in list(edges):
            if not edges[v]:
                del edges[v]
                for other in edges.values():
                    other.discard(v)
                changed = True
    return bool(edges)


print("== Банкир ==")
b1 = make("bank1.txt")
check("Need для bank1 совпадает с примером Silberschatz",
      b1.need_matrix() == [[7, 4, 3], [1, 2, 2], [6, 0, 0], [0, 1, 1], [4, 3, 1]])
check("bank1: безопасно, последовательность P1 P3 P4 P0 P2", b1.safe_sequence() == [1, 3, 4, 0, 2])
check("bank1: последовательность из методички P1 P3 P4 P2 P0 тоже допустима",
      b1.is_valid_sequence([1, 3, 4, 2, 0]))
check("bank1: порядок P0 P1 P2 P3 P4 недопустим", not b1.is_valid_sequence([0, 1, 2, 3, 4]))
all_seq = b1.all_safe_sequences()
brute = [p for p in itertools.permutations(range(5)) if b1.is_valid_sequence(list(p))]
check("bank1: перебор с возвратом и перестановки дают одинаковый набор (16)",
      len(all_seq) == 16 and sorted(map(tuple, all_seq)) == sorted(brute))
b2 = make("bank2.txt")
check("bank2: UNSAFE", b2.safe_sequence() is None and b2.all_safe_sequences() == [])

status, info = b1.request(1, [1, 0, 2])
check("P1 (1, 0, 2): выдано", status == "GRANTED" and b1.is_valid_sequence(info))
check("после выдачи Available = (2, 3, 0)", b1.available == [2, 3, 0])
status, _ = b1.request(4, [3, 3, 0])
check("P4 (3, 3, 0): отказ, ресурсов нет", status == "WAIT")
before = (list(b1.available), [list(r) for r in b1.allocation])
status, _ = b1.request(0, [0, 2, 0])
after = (list(b1.available), [list(r) for r in b1.allocation])
check("P0 (0, 2, 0): отказ, небезопасно, состояние откатилось", status == "UNSAFE" and before == after)
status, _ = b1.request(2, [7, 0, 0])
check("P2 (7, 0, 0): ошибка, больше Need", status == "ERROR")

rng = random.Random(8)
bad = 0
for _ in range(400):
    n, m = rng.randint(2, 5), rng.randint(1, 3)
    maxim = [[rng.randint(0, 6) for _ in range(m)] for _ in range(n)]
    alloc = [[rng.randint(0, maxim[i][j]) for j in range(m)] for i in range(n)]
    avail = [rng.randint(0, 4) for _ in range(m)]
    bk = banker.Banker(avail, alloc, maxim)
    seq = bk.safe_sequence()
    if (seq is not None) != brute_force_safe(avail, alloc, maxim):
        bad += 1
    if seq is not None and not bk.is_valid_sequence(seq):
        bad += 1
check("400 случайных состояний: банкир совпал с полным перебором", bad == 0)

bad = 0
granted = 0
for _ in range(400):
    n, m = rng.randint(2, 4), rng.randint(1, 3)
    maxim = [[rng.randint(0, 5) for _ in range(m)] for _ in range(n)]
    alloc = [[rng.randint(0, maxim[i][j]) for j in range(m)] for i in range(n)]
    avail = [rng.randint(0, 4) for _ in range(m)]
    bk = banker.Banker(avail, alloc, maxim)
    pid = rng.randrange(n)
    req = [rng.randint(0, 3) for _ in range(m)]
    old_avail, old_alloc = list(bk.available), [list(r) for r in bk.allocation]
    status, _ = bk.request(pid, req)
    if status == "GRANTED":
        granted += 1
        want_avail = [old_avail[j] - req[j] for j in range(m)]
        want_alloc = [list(r) for r in old_alloc]
        want_alloc[pid] = [old_alloc[pid][j] + req[j] for j in range(m)]
        if bk.available != want_avail or bk.allocation != want_alloc:
            bad += 1
        if not brute_force_safe(bk.available, bk.allocation, maxim):
            bad += 1
    else:
        if bk.available != old_avail or bk.allocation != old_alloc:
            bad += 1
        if status == "UNSAFE":
            test_avail = [old_avail[j] - req[j] for j in range(m)]
            test_alloc = [list(r) for r in old_alloc]
            test_alloc[pid] = [old_alloc[pid][j] + req[j] for j in range(m)]
            if brute_force_safe(test_avail, test_alloc, maxim):
                bad += 1
check(f"400 случайных запросов (выдано {granted}): решения верны, откат точный", bad == 0)

print("== Детектор по журналу ==")
with open("events_deadlock.log", encoding="utf-8") as f:
    found, graph, waiting, owner = deadlock_detector.analyze(f.readlines())
members = {t for _, cycle in found for t in cycle}
check("events_deadlock.log: цикл T1, T2, T3 найден на строке 11",
      members == {"T1", "T2", "T3"} and found[0][0] == 11)
check("events_deadlock.log: T4 ждёт, но в цикле его нет", "T4" in waiting and "T4" not in members)
with open("events_ok.log", encoding="utf-8") as f:
    found, graph, waiting, owner = deadlock_detector.analyze(f.readlines())
check("events_ok.log: взаимоблокировки нет", not found and not waiting)

bad = 0
for _ in range(500):
    size = rng.randint(1, 7)
    g = {v: {rng.randrange(size) for _ in range(rng.randint(0, 2))} for v in range(size)}
    cycle = find_cycle(g)
    if (cycle is not None) != has_cycle_by_reduction(g):
        bad += 1
    if cycle:
        ring = cycle + [cycle[0]]
        if not all(ring[k + 1] in g[ring[k]] for k in range(len(cycle))):
            bad += 1
check("500 случайных графов: DFS совпал с независимым способом, цикл настоящий", bad == 0)


def random_log(rnd):
    """Случайный, но правильный журнал событий."""
    threads = [f"T{i}" for i in range(rnd.randint(2, 5))]
    resources = [chr(ord("A") + i) for i in range(rnd.randint(2, 5))]
    own, wait, lines = {}, {}, []
    for _ in range(rnd.randint(5, 40)):
        t = rnd.choice(threads)
        if t in wait:
            r = wait[t]
            if r not in own:           # ресурс освободили: поток его берёт
                lines.append(f"acquire {t} {r}")
                own[r] = t
                del wait[t]
            continue
        r = rnd.choice(resources)
        held = [x for x, who in own.items() if who == t]
        action = rnd.choice(["acquire", "wait", "release"])
        if action == "acquire" and r not in own:
            lines.append(f"acquire {t} {r}")
            own[r] = t
        elif action == "wait" and r in own:
            lines.append(f"wait {t} {r}")
            wait[t] = r
        elif action == "release" and held:
            r = rnd.choice(held)
            lines.append(f"release {t} {r}")
            del own[r]
    return lines


bad = 0
rnd = random.Random(88)
deadlocks = 0
for _ in range(500):
    lines = random_log(rnd)
    found, graph, waiting, owner = deadlock_detector.analyze(lines)
    expected = has_cycle_by_reduction(graph)
    deadlocks += bool(found)
    if bool(found) != expected:
        bad += 1
check(f"500 случайных журналов (с deadlock: {deadlocks}): детектор совпал с проверкой", bad == 0)

print("== TrackedLock ==")
lock = tracked_lock.TrackedLock("one")
lock.acquire()
try:
    lock.acquire()
    self_ok = False
except tracked_lock.DeadlockError:
    self_ok = True
lock.release()
check("повторный захват своей блокировки даёт DeadlockError, а не зависание", self_ok)

try:
    lock.release()
    release_ok = False
except RuntimeError:
    release_ok = True
check("release чужой или свободной блокировки даёт RuntimeError", release_ok)

errors_total = 0
all_finished = True
for _ in range(20):
    locks = [tracked_lock.TrackedLock(f"L{i}") for i in range(3)]
    errors = []

    def worker(i):
        try:
            with locks[i]:
                time.sleep(0.05)
                with locks[(i + 1) % 3]:
                    pass
        except tracked_lock.DeadlockError as error:
            errors.append(str(error))

    threads = [threading.Thread(target=worker, args=(i,), name=f"W{i}", daemon=True) for i in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5)
    if any(t.is_alive() for t in threads):
        all_finished = False
    errors_total += len(errors) >= 1
check("цикл из трёх потоков: 20 раз из 20 ошибка вместо зависания", all_finished and errors_total == 20)

good = 0
for _ in range(20):
    res = subprocess.run([sys.executable, "deadlock.py", "--tracked"], capture_output=True, text=True, timeout=30)
    if res.returncode == 0 and res.stdout.count("DeadlockError") == 1 and "зависания нет" in res.stdout:
        good += 1
check("deadlock.py --tracked: 20 запусков из 20 без зависания и с одной ошибкой", good == 20)

try:
    subprocess.run([sys.executable, "deadlock.py"], capture_output=True, timeout=3)
    hangs = False
except subprocess.TimeoutExpired:
    hangs = True
check("deadlock.py без параметров действительно зависает (убит по таймауту)", hangs)

res = subprocess.run([sys.executable, "deadlock.py", "--dump", "1"], capture_output=True, text=True, timeout=30)
check("deadlock.py --dump показывает оба потока в worker",
      res.returncode == 1 and res.stderr.count("in worker") == 2)

print("== Философы ==")
runs = [philosophers.run("naive", 5) for _ in range(5)]
check("naive: 5 запусков из 5 закончились взаимоблокировкой", all(r["deadlock"] for r in runs))
for mode in ("ordered", "limit"):
    r = philosophers.run(mode, 3)
    check(f"{mode}: без взаимоблокировки, поел каждый (минимум {min(r['meals'])})",
          not r["deadlock"] and min(r["meals"]) > 0)

print()
print(f"Проверок: {total}, провалено: {failed}")
sys.exit(1 if failed else 0)
