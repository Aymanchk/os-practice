#!/usr/bin/env python3
"""Взаимоблокировка: два потока берут две блокировки в разном порядке.

Без параметров программа ЗАВИСАЕТ, так и задумано.
  ./deadlock.py --dump 3   через 3 секунды показать, где ждёт каждый поток
  ./deadlock.py --tracked  то же самое на TrackedLock: вместо зависания ошибка
"""
import argparse
import faulthandler
import sys
import threading
import time

from tracked_lock import DeadlockError, TrackedLock

PAUSE = 0.2  # пауза, чтобы оба потока успели взять первую блокировку
_print_lock = threading.Lock()


def say(text):
    """Печать одной строкой целиком, чтобы вывод потоков не перемешивался."""
    with _print_lock:
        sys.stdout.write(text + "\n")
        sys.stdout.flush()


def worker(name, first, second):
    """first и second: пары (имя, блокировка)."""
    try:
        with first[1]:
            say(f"{name}: взял {first[0]}")
            time.sleep(PAUSE)
            say(f"{name}: хочет {second[0]}")
            with second[1]:
                say(f"{name}: взял обе блокировки")
    except DeadlockError as error:
        say(f"{name}: поймал DeadlockError: {error}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dump", type=float, metavar="СЕК",
                        help="через СЕК секунд вывести стеки потоков и выйти")
    parser.add_argument("--tracked", action="store_true",
                        help="использовать TrackedLock")
    args = parser.parse_args()

    if args.dump:
        faulthandler.dump_traceback_later(args.dump, exit=True)

    if args.tracked:
        lock_a, lock_b = TrackedLock("lock_a"), TrackedLock("lock_b")
    else:
        lock_a, lock_b = threading.Lock(), threading.Lock()
    a = ("lock_a", lock_a)
    b = ("lock_b", lock_b)

    # первый берёт a потом b, второй берёт b потом a
    t1 = threading.Thread(target=worker, args=("T1", a, b), name="T1")
    t2 = threading.Thread(target=worker, args=("T2", b, a), name="T2")
    t1.start()
    t2.start()

    if args.tracked:
        t1.join(timeout=5)
        t2.join(timeout=5)
        if t1.is_alive() or t2.is_alive():
            print("Потоки зависли, TrackedLock не помог")
            return 1
        print("Оба потока завершились, зависания нет")
        return 0

    t1.join()
    t2.join()
    print("Эта строка не напечатается: потоки ждут друг друга вечно")
    return 0


if __name__ == "__main__":
    sys.exit(main())
