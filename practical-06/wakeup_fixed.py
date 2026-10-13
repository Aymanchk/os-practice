#!/usr/bin/env python3
"""Исправление: после wait условие проверяется заново в цикле while."""
import threading
import time

from common import Ring, Violations

violations = Violations()
ring = Ring(5, violations)
condition = threading.Condition()
taken = []


def consumer(name):
    with condition:
        while ring.count == 0:  # после пробуждения проверяем условие снова
            condition.wait()

        item = ring.get()
        taken.append((name, item))


def main():
    first = threading.Thread(target=consumer, args=("потребитель 1",))
    second = threading.Thread(target=consumer, args=("потребитель 2",))
    first.start()
    second.start()
    time.sleep(0.3)  # оба потребителя уже ждут пустой буфер

    with condition:
        ring.put("элемент 1")
        condition.notify_all()  # будим обоих, а элемент только один

    time.sleep(0.3)

    with condition:
        ring.put("элемент 2")
        condition.notify_all()

    first.join(timeout=2)
    second.join(timeout=2)

    for name, item in taken:
        print(f"{name} получил: {item}")

    problems = violations.all()
    print(f"Нарушений: {len(problems)}")

    for line in problems:
        print(f"  {line}")

    print(f"Остаток в буфере: {ring.count}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
