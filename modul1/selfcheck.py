#!/usr/bin/env python3
"""Самопроверка (блок A, задача 3): set1.txt против эталона ПР-5.

Автор: Эркинбеков Айман

Запуск:  python3 selfcheck.py
Код возврата: 0, если всё совпало, 1, если есть расхождения.
"""
import os
import sys

import scheduler as s

HERE = os.path.dirname(os.path.abspath(__file__))

# Эталон из методички ПР-5 для set1.txt: среднее ожидание и средний оборот.
ETALON = {
    "FCFS":     {"wait": 8.75,  "turn": 15.25, "gantt": "P1[0-8] P2[8-12] P3[12-21] P4[21-26]"},
    "SJF":      {"wait": 7.75,  "turn": 14.25, "gantt": "P1[0-8] P2[8-12] P4[12-17] P3[17-26]"},
    "RR q=3":   {"wait": 13.5,  "turn": 20.0,  "gantt": None},
    "SRTF":     {"wait": 6.5,   "turn": 13.0,  "gantt": "P1[0-1] P2[1-5] P4[5-10] P1[10-17] P3[17-26]"},
    "Priority": {"wait": 10.75, "turn": 17.25, "gantt": "P1[0-2] P3[2-11] P1[11-17] P2[17-21] P4[21-26]"},
}


def run_checks():
    """Возвращает список строк (алгоритм, ожидание, эталон, оборот, эталон, ок)."""
    procs = s.load(os.path.join(HERE, "data", "set1.txt"))
    results = [s.fcfs(procs), s.sjf(procs), s.rr(procs, 3), s.srtf(procs), s.priority(procs)]
    rows = []
    for r in results:
        e = ETALON[r.name]
        ok = abs(r.avg_waiting() - e["wait"]) < 1e-9 and abs(r.avg_turnaround() - e["turn"]) < 1e-9
        if e["gantt"] is not None:
            ok = ok and s.gantt_compact(r) == e["gantt"]
        rows.append((r.name, r.avg_waiting(), e["wait"], r.avg_turnaround(), e["turn"], ok))
    return rows


def sanity_errors():
    """Проверяет все алгоритмы на всех файлах: диаграмма Ганта должна быть корректной."""
    errors = []
    for name in ("set1.txt", "jobs.txt", "mixed.txt", "starve.txt"):
        procs = s.load(os.path.join(HERE, "data", name))
        algos = [s.fcfs(procs), s.sjf(procs), s.srtf(procs), s.priority(procs), s.mlfq(procs),
                 s.mlfq(procs, boost=0), s.priority_aging(procs, 5)]
        algos += [s.rr(procs, q) for q in range(1, 11)]
        for r in algos:
            ran = {p.pid: 0 for p in procs}
            prev_end = 0
            for pid, a, b in r.gantt:
                if a != prev_end:
                    errors.append(f"{name} {r.name}: разрыв во времени на {prev_end}")
                prev_end = b
                if pid is not None:
                    ran[pid] += b - a
            for p in procs:
                if ran[p.pid] != p.burst:
                    errors.append(f"{name} {r.name}: {p.pid} отработал {ran[p.pid]} вместо {p.burst}")
                if r.first_start[p.pid] < p.arrival:
                    errors.append(f"{name} {r.name}: {p.pid} стартовал раньше прихода")
                if r.finish[p.pid] != max(b for pid, a, b in r.gantt if pid == p.pid):
                    errors.append(f"{name} {r.name}: неверное время завершения {p.pid}")
    return errors


def main() -> int:
    errors = sanity_errors()
    print("Проверка корректности: 4 файла x 17 вариантов алгоритмов ->",
          "OK" if not errors else f"ошибок: {len(errors)}")
    for e in errors[:20]:
        print("  ", e)
    print()
    rows = run_checks()
    print("Самопроверка set1.txt против эталона ПР-5")
    print(f"{'Алгоритм':<10} {'Ожидание':>9} {'Эталон':>7} {'Оборот':>7} {'Эталон':>7}  Итог")
    for name, w, ew, t, et, ok in rows:
        print(f"{name:<10} {s.fmt(w):>9} {s.fmt(ew):>7} {s.fmt(t):>7} {s.fmt(et):>7}  {'OK' if ok else 'ОШИБКА'}")
    bad = [r for r in rows if not r[-1]]
    print("\nВсе алгоритмы совпали с эталоном." if not bad else f"\nРасхождений: {len(bad)}")
    return 1 if bad or errors else 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    sys.exit(main())
