#!/usr/bin/env python3
"""Таблица для README: на каких операциях ops1 отказ у каждого варианта (печатает Markdown)."""
import sys

from buddy import Buddy
from memsim import MEMORY, MemoryManager, load


def refusals(manager, ops, free_name):
    """Номера операций alloc, которые получили отказ."""
    failed = []
    for n, (cmd, pid, *rest) in enumerate(ops, 1):
        if cmd == "alloc":
            if not manager.alloc(pid, rest[0]):
                failed.append(n)
        else:
            getattr(manager, free_name)(pid)
    return failed


def main():
    ops = load(sys.argv[1] if len(sys.argv) > 1 else "ops1.txt")
    variants = []
    for strategy in ("first", "best", "worst"):
        variants.append((f"{strategy} fit", MemoryManager(strategy), "free"))
    for strategy in ("first", "best", "worst"):
        variants.append((f"{strategy} fit + слияние", MemoryManager(strategy, coalesce=True), "free"))
    variants.append(("buddy", Buddy(), "release"))

    print("| Вариант | Отказ на операциях | Отказов | Свободно | Макс. дыра | Дыр |")
    print("|---|---|---:|---:|---:|---:|")
    for name, manager, free_name in variants:
        failed = refusals(manager, ops, free_name)
        if isinstance(manager, Buddy):
            total, largest, _ = manager.stats()
            holes = sum(len(lst) for lst in manager.free.values())
        else:
            total, largest, holes = manager.stats()
        print(f"| {name} | {', '.join(map(str, failed))} | {len(failed)} | {total} | {largest} | {holes} |")

    buddy = Buddy()
    for cmd, pid, *rest in ops[:3]:            # первые три выделения: 200, 300, 150
        buddy.alloc(pid, rest[0])
    internal = buddy.stats()[2]
    print(f"\nBuddy после трёх выделений (200, 300, 150 -> блоки 256, 512, 256): внутренняя "
          f"фрагментация {internal} из {MEMORY} ({100 * internal / MEMORY:.1f}% памяти).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
