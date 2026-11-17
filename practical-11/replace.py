#!/usr/bin/env python3
"""ПР-11: алгоритмы замещения страниц FIFO, LRU, Optimal и Clock.

Запуск:
    python3 replace.py              # контрольная строка, 3 и 4 кадра, таблица
    python3 replace.py -f 3 -v      # пошагово для 3 кадров
    python3 replace.py -f 4 -s "1 2 3 4 1 2 5 1 2 3 4 5"
"""
import argparse
import sys
from collections import deque

# Контрольная строка из учебника Silberschatz
REFERENCE = [7, 0, 1, 2, 0, 3, 0, 4, 2, 3, 0, 3, 2, 1, 2, 0, 1, 7, 0, 1]
# Строка для аномалии Белади
BELADY = [1, 2, 3, 4, 1, 2, 5, 1, 2, 3, 4, 5]


class Result:
    """Число отказов и, при желании, история состояний кадров."""

    def __init__(self):
        self.faults = 0
        self.work = 0            # элементарные действия алгоритма (для сравнения LRU и Clock)
        self.steps = []          # (страница, отказ?, кадры после шага, вытесненная)

    def record(self, page, fault, frames, victim, trace):
        if fault:
            self.faults += 1
        if trace:
            self.steps.append((page, fault, list(frames), victim))


def fifo(refs, nframes, trace=False):
    """Вытесняется страница, загруженная раньше всех. Попадание очередь не меняет."""
    res, frames, queue = Result(), [], deque()
    for page in refs:
        victim = None
        fault = page not in frames
        if fault:
            if len(frames) < nframes:
                frames.append(page)
            else:
                victim = queue.popleft()
                frames[frames.index(victim)] = page
            queue.append(page)
        res.record(page, fault, frames, victim, trace)
    return res


def lru(refs, nframes, trace=False):
    """Вытесняется страница, к которой дольше всего не обращались.
    Время последнего обращения обновляется при КАЖДОМ обращении, а не только при отказе."""
    res, frames, last_used = Result(), [], {}
    for time, page in enumerate(refs):
        victim = None
        fault = page not in frames
        if fault:
            if len(frames) < nframes:
                frames.append(page)
            else:
                victim = min(frames, key=lambda p: last_used[p])
                res.work += len(frames)          # просмотр времени всех кадров
                frames[frames.index(victim)] = page
        last_used[page] = time
        res.work += 1                            # запись времени при каждом обращении
        res.record(page, fault, frames, victim, trace)
    return res


def optimal(refs, nframes, trace=False):
    """Вытесняется страница, которая понадобится позже всех (смотрим ВПЕРЁД по строке).
    Страница, которая больше не встретится, нужна «никогда» и уходит первой."""
    res, frames = Result(), []
    for i, page in enumerate(refs):
        victim = None
        fault = page not in frames
        if fault:
            if len(frames) < nframes:
                frames.append(page)
            else:
                def next_use(p):
                    for j in range(i + 1, len(refs)):
                        if refs[j] == p:
                            return j
                    return float("inf")
                # при равенстве (несколько «никогда») берётся кадр с меньшим номером
                victim = max(frames, key=next_use)
                frames[frames.index(victim)] = page
        res.record(page, fault, frames, victim, trace)
    return res


def clock(refs, nframes, trace=False):
    """Второй шанс: у каждого кадра бит обращения, стрелка идёт по кругу.
    Попадание: бит = 1. Отказ: пока под стрелкой бит 1, сбросить в 0 и сдвинуть
    стрелку; в кадр с битом 0 положить новую страницу (бит 1), стрелку сдвинуть дальше."""
    res = Result()
    frames = [None] * nframes
    bits = [0] * nframes
    hand = 0
    for page in refs:
        victim = None
        if page in frames:
            bits[frames.index(page)] = 1
            res.work += 1                        # установка бита при попадании
            fault = False
        else:
            fault = True
            res.work += 1                        # кадр под стрелкой проверяется всегда
            while bits[hand] == 1:
                bits[hand] = 0
                hand = (hand + 1) % nframes
                res.work += 1                    # сброс бита и шаг стрелки
            victim = frames[hand]
            frames[hand] = page
            bits[hand] = 1
            hand = (hand + 1) % nframes
        res.record(page, fault, [f for f in frames if f is not None], victim, trace)
    return res


ALGORITHMS = {"FIFO": fifo, "LRU": lru, "Optimal": optimal, "Clock": clock}


def parse_refs(text):
    return [int(x) for x in text.replace(",", " ").split()]


def print_trace(name, res):
    print(f"--- {name}")
    for page, fault, frames, victim in res.steps:
        mark = "F" if fault else " "
        out = f"  вытеснена {victim}" if victim is not None else ""
        print(f"  {page:>2}  {mark}  {frames}{out}")
    print(f"  отказов: {res.faults}")


def main(argv):
    p = argparse.ArgumentParser(description="Алгоритмы замещения страниц")
    p.add_argument("-f", "--frames", type=int, nargs="+", default=[3, 4], help="число кадров")
    p.add_argument("-s", "--string", help="строка обращений (по умолчанию контрольная)")
    p.add_argument("-v", "--verbose", action="store_true", help="пошаговое состояние кадров")
    args = p.parse_args(argv)
    if any(f < 1 for f in args.frames):
        p.error("число кадров должно быть не меньше 1")
    refs = parse_refs(args.string) if args.string else REFERENCE

    print("Строка:", " ".join(map(str, refs)))
    print(f"{'Кадры':>5}  " + "  ".join(f"{n:>7}" for n in ALGORITHMS))
    for nf in args.frames:
        row = [fn(refs, nf).faults for fn in ALGORITHMS.values()]
        print(f"{nf:>5}  " + "  ".join(f"{v:>7}" for v in row))
    if args.verbose:
        for nf in args.frames:
            print(f"\n=== {nf} кадра(ов)")
            for name, fn in ALGORITHMS.items():
                print_trace(name, fn(refs, nf, trace=True))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
