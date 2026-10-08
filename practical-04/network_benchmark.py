#!/usr/bin/env python3
import statistics
import sys
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from pathlib import Path
from urllib.request import Request, urlopen


WORKERS = 4
REPEATS = 3


def download(url):
    request = Request(
        url,
        headers={"User-Agent": "os-practice-04"},
    )

    with urlopen(request, timeout=15) as response:
        return len(response.read())


def sequential(urls):
    return sum(download(url) for url in urls)


def thread_pool(urls):
    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
        sizes = list(executor.map(download, urls))

    return sum(sizes)


def process_pool(urls):
    with ProcessPoolExecutor(max_workers=WORKERS) as executor:
        sizes = list(executor.map(download, urls))

    return sum(sizes)


def measure(name, action, urls, expected_size):
    times = []

    for repeat in range(1, REPEATS + 1):
        started = time.perf_counter()
        total_size = action(urls)
        elapsed = time.perf_counter() - started

        if total_size != expected_size:
            raise RuntimeError(
                f"{name}: получено {total_size} байт, "
                f"ожидалось {expected_size}"
            )

        times.append(elapsed)

        print(
            f"{name}: повтор {repeat}, "
            f"байт={total_size}, время={elapsed:.6f} с"
        )

    median = statistics.median(times)
    print(f"{name}: медиана={median:.6f} с")
    print()

    return median


def main():
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "urls.txt")

    if not path.is_file():
        print(f"Ошибка: файл не найден: {path}", file=sys.stderr)
        return 1

    urls = [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    if len(urls) != 20:
        print(
            f"Ошибка: получено URL: {len(urls)}, ожидалось 20",
            file=sys.stderr,
        )
        return 1

    expected_size = sum(
        path.stat().st_size
        for path in Path("web").glob("file*.txt")
    )

    print(f"URL: {len(urls)}")
    print(f"Рабочих потоков/процессов: {WORKERS}")
    print(f"Повторов: {REPEATS}")
    print(f"Ожидаемый объём: {expected_size} байт")
    print()

    results = {
        "Последовательно": measure(
            "Последовательно",
            sequential,
            urls,
            expected_size,
        ),
        "ThreadPoolExecutor": measure(
            "ThreadPoolExecutor",
            thread_pool,
            urls,
            expected_size,
        ),
        "ProcessPoolExecutor": measure(
            "ProcessPoolExecutor",
            process_pool,
            urls,
            expected_size,
        ),
    }

    print("Итоговая таблица:")
    print("Метод\tМедиана, с")

    for name, median in results.items():
        print(f"{name}\t{median:.6f}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
