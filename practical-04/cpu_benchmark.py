#!/usr/bin/env python3
import gc
import multiprocessing as mp
import os
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


WORKERS = 4
REPEATS = 3
EXPECTED_COUNT = 10_000_000
EXPECTED_SUM = 4_995_000_000
NUMBERS = []
HERE = Path(__file__).resolve().parent


def make_ranges(length, parts):
    ranges = []
    base_size = length // parts
    remainder = length % parts
    start = 0

    for part in range(parts):
        size = base_size + (1 if part < remainder else 0)
        end = start + size
        ranges.append((start, end))
        start = end

    return ranges


def sum_range(bounds):
    start, end = bounds
    total = 0

    for index in range(start, end):
        total += NUMBERS[index]

    return total


def single_thread(ranges):
    return sum_range((0, len(NUMBERS)))


def four_threads(ranges):
    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
        partial_sums = list(executor.map(sum_range, ranges))

    return sum(partial_sums)


def four_processes(ranges):
    # На Linux явно используем fork, чтобы большой список наследовался
    # процессами и не передавался им через pickle.
    context = mp.get_context("fork")

    with context.Pool(processes=WORKERS) as pool:
        partial_sums = pool.map(sum_range, ranges)

    return sum(partial_sums)


def measure(name, function, ranges):
    times = []

    for repeat in range(1, REPEATS + 1):
        gc.collect()
        started = time.perf_counter()
        result = function(ranges)
        elapsed = time.perf_counter() - started

        if result != EXPECTED_SUM:
            raise RuntimeError(
                f"{name}: неправильная сумма {result}, "
                f"ожидалось {EXPECTED_SUM}"
            )

        times.append(elapsed)

        print(
            f"{name}, повтор {repeat}: "
            f"сумма={result}, время={elapsed:.6f} с"
        )

    median = statistics.median(times)
    print(f"{name}, медиана: {median:.6f} с\n")
    return median


def main():
    global NUMBERS

    path = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "numbers.txt"

    if not path.is_file():
        print(
            f"Ошибка: файл не найден: {path}",
            file=sys.stderr,
        )
        return 1

    print(f"Загрузка данных из {path.name}...")
    NUMBERS = [int(line) for line in path.read_text().splitlines()]

    if len(NUMBERS) != EXPECTED_COUNT:
        print(
            f"Ошибка: получено {len(NUMBERS)} чисел, "
            f"ожидалось {EXPECTED_COUNT}",
            file=sys.stderr,
        )
        return 1

    try:
        available_cpus = len(os.sched_getaffinity(0))
    except AttributeError:
        available_cpus = os.cpu_count() or 1

    print(f"Загружено чисел: {len(NUMBERS)}")
    print(f"Доступных логических ядер: {available_cpus}")
    print(f"Рабочих потоков/процессов: {WORKERS}")
    print(f"Повторов: {REPEATS}")
    print("Загрузка файла не входит во время вычисления.\n")

    ranges = make_ranges(len(NUMBERS), WORKERS)

    single_median = measure(
        "Один поток",
        single_thread,
        ranges,
    )
    thread_median = measure(
        "4 потока threading",
        four_threads,
        ranges,
    )
    process_median = measure(
        "4 процесса multiprocessing",
        four_processes,
        ranges,
    )

    print("Итоговая таблица CPU:")
    print("Метод | Медиана, с | Относительно одного потока")
    print(
        f"Один поток | {single_median:.6f} | "
        f"{single_median / single_median:.2f}x"
    )
    print(
        f"4 потока | {thread_median:.6f} | "
        f"{single_median / thread_median:.2f}x"
    )
    print(
        f"4 процесса | {process_median:.6f} | "
        f"{single_median / process_median:.2f}x"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
