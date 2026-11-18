#!/usr/bin/env python3
"""ПР-13, уровень B: голодание в SSTF и справедливость SSTF против C-LOOK.

Здесь запросы приходят во время работы. Время меряется в цилиндрах: головка
проходит один цилиндр за единицу времени. После каждого обслуженного запроса
алгоритм выбирает следующий среди тех, что уже пришли. Ожидание запроса =
момент обслуживания - момент прихода.
"""
import random
import statistics
import sys

CYLINDERS = 200


def pick_sstf(pending, head, state):
    return min(pending, key=lambda r: (abs(r[1] - head), r[0]))


def pick_clook(pending, head, state):
    """Едем вверх; если впереди ничего нет - прыжок к самому младшему запросу."""
    ahead = [r for r in pending if r[1] >= head]
    if ahead:
        return min(ahead, key=lambda r: (r[1], r[0]))
    return min(pending, key=lambda r: (r[1], r[0]))


POLICIES = {"SSTF": pick_sstf, "C-LOOK": pick_clook}


def simulate(policy, arrivals, head=50, horizon=None):
    """arrivals: список (время прихода, цилиндр), по возрастанию времени.
    Возвращает список (время прихода, цилиндр, время обслуживания) и пройденный путь."""
    arrivals = list(arrivals)
    t, i, pending, done, moved = 0, 0, [], [], 0
    while i < len(arrivals) or pending:
        while i < len(arrivals) and arrivals[i][0] <= t:
            pending.append(arrivals[i])
            i += 1
        if not pending:
            t = arrivals[i][0]          # простой: ждём следующий запрос
            continue
        req = policy(pending, head, None)
        pending.remove(req)
        dist = abs(req[1] - head)
        t += dist
        moved += dist
        head = req[1]
        done.append((req[0], req[1], t))
        if horizon is not None and t > horizon:
            break
    return done, moved, pending


def starvation():
    """Далёкий запрос 190 в момент 0 и непрерывный поток запросов рядом с головкой."""
    rng = random.Random(5)
    arrivals = [(0, 190)] + [(0, c) for c in (45, 48, 52, 55, 58)]
    for k in range(1, 400):
        arrivals.append((k * 4, rng.randint(40, 60)))     # каждые 4 единицы времени
    print("Сценарий: головка на 50, в момент 0 запрос к цилиндру 190 и 5 запросов в 45..58;")
    print("затем каждые 4 единицы времени новый запрос в 40..60 (всего 399), поток длится 1600.")
    for name, pol in POLICIES.items():
        done, moved, pending = simulate(pol, arrivals, head=50, horizon=1600)
        far = [d for d in done if d[1] == 190]
        if far:
            note = ", то есть только когда поток закончился" if far[0][2] > arrivals[-1][0] else ""
            print(f"  {name:>6}: запрос 190 обслужен в момент {far[0][2]}, "
                  f"до него обслужено {done.index(far[0])} других запросов{note}")
        else:
            print(f"  {name:>6}: запрос 190 НЕ обслужен за {done[-1][2]} единиц времени, "
                  f"обслужено {len(done)} ближних запросов, в очереди осталось {len(pending)}")


def fairness(runs=20, n=400, rate=0.08):
    """Случайный поток по всему диску: интервалы между приходами ~ экспоненциальные."""
    rows = {name: {"move": [], "mean": [], "p95": [], "max": []} for name in POLICIES}
    for seed in range(runs):
        rng = random.Random(1000 + seed)
        t, arrivals = 0.0, []
        for _ in range(n):
            t += rng.expovariate(rate)
            arrivals.append((int(t), rng.randrange(CYLINDERS)))
        for name, pol in POLICIES.items():
            done, moved, _ = simulate(pol, arrivals, head=rng.randrange(CYLINDERS))
            waits = sorted(d[2] - d[0] for d in done)
            rows[name]["move"].append(moved / len(done))
            rows[name]["mean"].append(statistics.mean(waits))
            rows[name]["p95"].append(waits[int(0.95 * len(waits)) - 1])
            rows[name]["max"].append(waits[-1])
    print(f"Случайный поток: {runs} прогонов по {n} запросов, в среднем 1 запрос на "
          f"{1 / rate:.1f} единицы времени, цилиндры 0..{CYLINDERS - 1}")
    print(f"{'':>6}  {'путь на запрос':>14}  {'ожидание ср.':>12}  {'95-й процентиль':>15}  {'максимум':>8}")
    for name, r in rows.items():
        print(f"{name:>6}  {statistics.mean(r['move']):>14.1f}  {statistics.mean(r['mean']):>12.1f}  "
              f"{statistics.mean(r['p95']):>15.1f}  {statistics.mean(r['max']):>8.1f}")
    return rows


def main():
    starvation()
    print()
    fairness()
    return 0


if __name__ == "__main__":
    sys.exit(main())
