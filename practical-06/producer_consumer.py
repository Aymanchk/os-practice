#!/usr/bin/env python3
"""Производитель и потребитель: 3 производителя, 2 потребителя, 1000 элементов."""
import sys
import threading
import time
from collections import Counter

from buffers import ConditionBuffer, SemaphoreBuffer
from common import CAPACITY, CONSUMERS, ITEMS, PRODUCERS, STOP, Violations

MODES = {
    "sem": ("семафоры и мьютекс", SemaphoreBuffer),
    "cond": ("мьютекс и условная переменная", ConditionBuffer),
}


def producer(buffer, number):
    # Производитель number создаёт числа number, number + 3, number + 6 ...
    for item in range(number, ITEMS, PRODUCERS):
        buffer.put(item)


def consumer(buffer, result):
    while True:
        item = buffer.get()

        if item == STOP:
            return

        result.append(item)


def run(mode):
    title, buffer_class = MODES[mode]
    violations = Violations()
    buffer = buffer_class(CAPACITY, violations)
    results = [[] for _ in range(CONSUMERS)]

    producers = [
        threading.Thread(target=producer, args=(buffer, number))
        for number in range(PRODUCERS)
    ]
    consumers = [
        threading.Thread(target=consumer, args=(buffer, results[number]))
        for number in range(CONSUMERS)
    ]

    started = time.perf_counter()

    for thread in producers + consumers:
        thread.start()

    for thread in producers:
        thread.join()

    # Все производители закончили, каждому потребителю отправляем STOP.
    for _ in range(CONSUMERS):
        buffer.put(STOP)

    for thread in consumers:
        thread.join()

    elapsed = time.perf_counter() - started

    consumed = [item for part in results for item in part]
    counts = Counter(consumed)
    duplicates = sorted(item for item, n in counts.items() if n > 1)
    missing = sorted(set(range(ITEMS)) - set(counts))
    exactly_once = not duplicates and not missing and len(consumed) == ITEMS
    problems = violations.all()

    print(f"Вариант: {title}")
    print(f"Производителей: {PRODUCERS}, потребителей: {CONSUMERS}")
    print(f"Размер буфера: {CAPACITY}")
    print(f"Создано элементов: {ITEMS}")
    print(f"Потреблено элементов: {len(consumed)}")
    print(
        "Потребители получили: "
        + ", ".join(str(len(part)) for part in results)
    )
    print(f"Каждый элемент потреблён ровно один раз: {exactly_once}")
    print(f"Повторов: {len(duplicates)}, потеряно: {len(missing)}")
    print(f"Максимальное заполнение буфера: {buffer.ring.max_count}")
    print(f"Остаток в буфере после работы: {buffer.ring.count}")
    print(f"Нарушений буфера: {len(problems)}")

    for line in problems[:5]:
        print(f"  {line}")

    print(f"Время: {elapsed:.3f} с")

    ok = (
        exactly_once
        and not problems
        and buffer.ring.max_count <= CAPACITY
        and buffer.ring.count == 0
    )
    return ok


def main():
    sys.setswitchinterval(1e-6)  # чаще переключаем потоки, чтобы искать ошибки

    if len(sys.argv) != 2 or sys.argv[1] not in MODES:
        print("Использование: ./producer_consumer.py sem|cond")
        return 2

    return 0 if run(sys.argv[1]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
