#!/usr/bin/env python3
"""Обедающие философы: наивный вариант с deadlock и два исправления.

  naive   - каждый берёт сначала левую вилку, потом правую (бывает deadlock)
  ordered - вилки пронумерованы, всегда берём сначала вилку с меньшим номером
  limit   - за столом одновременно не больше N-1 философов (семафор)

Запуск: ./philosophers.py naive|ordered|limit|all [секунд]
"""
import random
import sys
import threading
import time

N = 5
EAT = 0.005         # сколько философ ест
THINK_MAX = 0.02    # думает случайное время до этого значения
GRAB_PAUSE = 0.01   # пауза между первой и второй вилкой
MODES = ("naive", "ordered", "limit")
DESCRIPTION = {
    "naive": "левая вилка, потом правая",
    "ordered": "сначала вилка с меньшим номером",
    "limit": "за столом не больше N-1 философов",
}


def run(mode, seconds):
    """Один прогон. Возвращает словарь с результатами."""
    forks = [threading.Lock() for _ in range(N)]
    seat = threading.Semaphore(N - 1) if mode == "limit" else None
    meals = [0] * N      # каждый поток пишет только в свою ячейку
    holding = [0] * N    # сколько вилок сейчас в руках у философа
    stop = threading.Event()

    def philosopher(i):
        rng = random.Random(i)
        left, right = i, (i + 1) % N
        if mode == "ordered":
            first, second = min(left, right), max(left, right)
        else:
            first, second = left, right
        while not stop.is_set():
            time.sleep(rng.random() * THINK_MAX)
            if seat:
                seat.acquire()
            forks[first].acquire()
            holding[i] = 1
            time.sleep(GRAB_PAUSE)
            forks[second].acquire()
            holding[i] = 2
            time.sleep(EAT)
            meals[i] += 1
            forks[second].release()
            forks[first].release()
            holding[i] = 0
            if seat:
                seat.release()

    threads = [threading.Thread(target=philosopher, args=(i,), daemon=True)
               for i in range(N)]
    start = time.time()
    for t in threads:
        t.start()

    # Следим за прогрессом. Взаимоблокировка: у всех в руках ровно по одной
    # вилке и никто не ест, и так несколько проверок подряд.
    deadlock = False
    stuck = 0
    last_total = -1
    while time.time() - start < seconds:
        time.sleep(0.1)
        total = sum(meals)
        if all(h == 1 for h in holding) and total == last_total:
            stuck += 1
        else:
            stuck = 0
        last_total = total
        if stuck >= 5:
            deadlock = True
            break

    elapsed = time.time() - start
    stop.set()
    if not deadlock:
        for t in threads:
            t.join(timeout=2)
    return {"mode": mode, "deadlock": deadlock, "time": elapsed, "meals": list(meals)}


def report(result):
    meals = result["meals"]
    print(f"Режим: {result['mode']} ({DESCRIPTION[result['mode']]})")
    if result["deadlock"]:
        print(f"ВЗАИМОБЛОКИРОВКА через {result['time']:.1f} с: "
              "у каждого философа по одной вилке, все ждут вторую")
    else:
        print(f"Работали {result['time']:.1f} с, зависания не было")
    print("Сколько раз поел каждый:", meals)
    print(f"Всего: {sum(meals)}, меньше всего: {min(meals)}, больше всего: {max(meals)}")


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    seconds = float(sys.argv[2]) if len(sys.argv) > 2 else 3.0
    if mode != "all" and mode not in MODES:
        print("Использование: philosophers.py naive|ordered|limit|all [секунд]")
        return 2

    if mode != "all":
        report(run(mode, seconds))
        return 0

    results = [run(m, seconds) for m in MODES]
    for result in results:
        report(result)
        print()
    print("Сводка (сколько раз поел каждый философ):")
    print(f"{'режим':<9}{'P0':>5}{'P1':>5}{'P2':>5}{'P3':>5}{'P4':>5}{'всего':>8}  итог")
    for r in results:
        row = "".join(f"{x:>5}" for x in r["meals"])
        verdict = "deadlock" if r["deadlock"] else "ок"
        print(f"{r['mode']:<9}{row}{sum(r['meals']):>8}  {verdict}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
