#!/usr/bin/env python3
"""Сравнение четырёх подходов на большом наборе операций (по умолчанию ops2.txt).

Подходы: first fit, best fit, worst fit (дыры склеиваются) и buddy system.
Внешняя фрагментация считается после каждой операции и усредняется по всем шагам.
"""
import sys

from buddy import Buddy
from memsim import MEMORY, MemoryManager, STRATEGIES, external_fragmentation, load

HEADER = f"{'подход':<16}{'отказов':>8}{'внешняя фр.':>13}{'внутренняя':>12}"


def trace(ops, make, alloc, free, stats):
    """Прогоняет операции. Возвращает (отказов, внешняя после каждого шага, внутренняя после каждого шага)."""
    m, ext, internal = make(), [], []
    for cmd, pid, *rest in ops:
        alloc(m, pid, rest[0]) if cmd == "alloc" else free(m, pid)
        tot, mx, extra = stats(m)
        ext.append(external_fragmentation(tot, mx))   # доля свободной памяти вне самой большой дыры
        internal.append(extra)
    return m.refused, ext, internal


def simulate(ops, make, alloc, free, stats):
    """Возвращает (отказов, средняя внешняя, средняя внутренняя) по всем шагам."""
    refused, ext, internal = trace(ops, make, alloc, free, stats)
    return refused, sum(ext) / len(ext), sum(internal) / len(internal)


def first_two(m):
    """Для first/best/worst: внутренней фрагментации нет, третье значение 0."""
    return (*m.stats()[:2], 0)


def approaches():
    """Четыре подхода из задания: (название, make, alloc, free, stats)."""
    result = []
    for strategy in STRATEGIES:
        result.append((f"{strategy} +merge", lambda s=strategy: MemoryManager(s, coalesce=True),
                       MemoryManager.alloc, MemoryManager.free, first_two))
    result.append(("buddy", Buddy, Buddy.alloc, Buddy.release, Buddy.stats))
    return result


def row(name, result):
    r, e, i = result
    return f"{name:<16}{r:>8}{e:>13.2f}{i:>12.0f}"


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "ops2.txt"
    try:
        ops = load(path)
    except (OSError, ValueError) as error:
        print(f"Ошибка: {error}")
        return 2

    results = {}
    for name, make, alloc, free, stats in approaches():
        results[name] = simulate(ops, make, alloc, free, stats)

    print(HEADER)
    for name, result in results.items():
        print(row(name, result))

    plain = {}
    for strategy in STRATEGIES:
        plain[strategy] = simulate(
            ops, lambda s=strategy: MemoryManager(s, coalesce=False),
            MemoryManager.alloc, MemoryManager.free, first_two)

    allocs = sum(1 for op in ops if op[0] == "alloc")
    print(f"\nДополнительно. Те же три стратегии без склейки дыр ({len(ops)} операций из {path}, "
          f"{allocs} alloc, {len(ops) - allocs} free):")
    print(HEADER)
    for strategy in STRATEGIES:
        print(row(f"{strategy} -merge", plain[strategy]))

    print("\nВыводы по этому файлу:")
    best_refused = min(r[0] for r in results.values())
    names = [n for n, r in results.items() if r[0] == best_refused]
    print(f"- меньше всего отказов: {', '.join(names)} ({best_refused})")
    best_ext = min(r[1] for r in results.values())
    names = [n for n, r in results.items() if abs(r[1] - best_ext) < 0.005]
    print(f"- меньше всего внешней фрагментации: {', '.join(names)} ({best_ext:.2f})")
    worst_name = max(results, key=lambda n: results[n][1])
    print(f"- больше всего внешней фрагментации: {worst_name} ({results[worst_name][1]:.2f})")
    for strategy in STRATEGIES:
        with_merge, without = results[f"{strategy} +merge"], plain[strategy]
        print(f"- склейка у {strategy} fit: отказов было {without[0]}, стало {with_merge[0]}; "
              f"внешняя фрагментация была {without[1]:.2f}, стала {with_merge[1]:.2f}")
    internal = results["buddy"][2]
    print(f"- buddy: потери внутри блоков в среднем {internal:.0f} единиц "
          f"({100 * internal / MEMORY:.0f}% памяти) из-за округления до степени двойки")
    return 0


if __name__ == "__main__":
    sys.exit(main())
