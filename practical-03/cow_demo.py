#!/usr/bin/env python3
import os
import sys
from pathlib import Path


LIST_SIZE = 8_000_000
POINTERS_PER_PAGE = 512


def memory_info():
    values = {}

    for line in Path("/proc/self/smaps_rollup").read_text().splitlines():
        if ":" not in line:
            continue

        key, value = line.split(":", 1)
        parts = value.split()

        if parts and parts[0].isdigit():
            values[key] = int(parts[0])

    rss = values.get("Rss", 0)
    shared = (
        values.get("Shared_Clean", 0)
        + values.get("Shared_Dirty", 0)
    )
    private = (
        values.get("Private_Clean", 0)
        + values.get("Private_Dirty", 0)
    )

    return rss, shared, private


def show_memory(label):
    rss, shared, private = memory_info()

    print(
        f"{label}: "
        f"RSS={rss} kB, "
        f"shared={shared} kB, "
        f"private={private} kB",
        flush=True,
    )


def main():
    big_list = [0] * LIST_SIZE

    print(
        f"Родитель PID={os.getpid()} создал список "
        f"из {LIST_SIZE} элементов",
        flush=True,
    )

    show_memory("Родитель до fork")
    sys.stdout.flush()

    child_pid = os.fork()

    if child_pid == 0:
        show_memory("Ребёнок до изменения")

        # Изменяем хотя бы один элемент на каждой странице списка.
        for index in range(0, len(big_list), POINTERS_PER_PAGE):
            big_list[index] = 1

        show_memory("Ребёнок после изменения")
        os._exit(0)

    waited_pid, status = os.waitpid(child_pid, 0)
    exit_code = os.waitstatus_to_exitcode(status)

    print(
        f"Родитель дождался PID={waited_pid}, код={exit_code}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
