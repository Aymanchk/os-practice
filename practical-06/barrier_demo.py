#!/usr/bin/env python3
"""Барьер на условной переменной: 4 потока, 3 фазы."""
import random
import threading
import time

THREADS = 4
PHASES = 3


class Barrier:
    """Повторно используемый барьер. generation нужен, чтобы быстрый
    поток следующей фазы не перепутал её с предыдущей."""

    def __init__(self, parties):
        self.parties = parties
        self.waiting = 0
        self.generation = 0
        self.condition = threading.Condition()

    def wait(self):
        with self.condition:
            generation = self.generation
            self.waiting += 1

            if self.waiting == self.parties:
                self.waiting = 0
                self.generation += 1
                self.condition.notify_all()
                return

            while generation == self.generation:
                self.condition.wait()


events = []
events_lock = threading.Lock()


def log(kind, phase, number):
    with events_lock:
        events.append((len(events), kind, phase, number))
        print(f"{kind:<6} фаза {phase}, поток {number}", flush=True)


def worker(number, barrier):
    rng = random.Random(number)

    for phase in range(1, PHASES + 1):
        log("начал", phase, number)
        time.sleep(rng.uniform(0.01, 0.08))  # работа разной длины
        log("конец", phase, number)
        barrier.wait()


def check():
    """Ни один поток не должен начать фазу k + 1, пока не закончились все
    потоки фазы k."""
    for phase in range(1, PHASES):
        last_end = max(
            e[0] for e in events if e[1] == "конец" and e[2] == phase
        )
        first_next = min(
            e[0] for e in events if e[1] == "начал" and e[2] == phase + 1
        )

        if first_next < last_end:
            return False

    ends = sum(1 for e in events if e[1] == "конец")
    return ends == THREADS * PHASES


def main():
    barrier = Barrier(THREADS)
    threads = [
        threading.Thread(target=worker, args=(number, barrier))
        for number in range(1, THREADS + 1)
    ]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    ok = check()
    print(f"Барьер работает правильно: {ok}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
