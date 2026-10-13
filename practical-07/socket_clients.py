#!/usr/bin/env python3
"""Запускает несколько клиентов сокета одновременно, каждый в своём процессе."""
import subprocess
import sys
import time

CLIENTS = [
    ["1+1", "2*(3+4)", "10/4"],
    ["2**10", "7//2", "7%3"],
    ["100-1", "(5+5)*(5-5)", "1/0"],
    ["3.5*2", "-4+10", "abc"],
    ["12*12", "50/5", "2**64"],
]


def main():
    started = time.perf_counter()
    processes = []

    for expressions in CLIENTS:
        process = subprocess.Popen(
            [sys.executable, "socket_client.py", *expressions],
            stdout=subprocess.PIPE,
            text=True,
        )
        processes.append(process)

    failed = False
    lines = []

    for process in processes:
        output, _ = process.communicate()
        lines.extend(output.splitlines())
        failed = failed or process.returncode != 0

    elapsed = time.perf_counter() - started
    requests = sum(len(expressions) for expressions in CLIENTS)

    for line in lines:
        print(line)

    print()
    print(f"Клиентов одновременно: {len(CLIENTS)}")
    print(f"Запросов всего: {requests}")
    print(f"Время: {elapsed:.2f} с")
    print(f"Одним клиентом по очереди заняло бы не меньше {requests * 0.3:.1f} с")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
