#!/usr/bin/env python3
"""Детектор взаимоблокировок по журналу событий acquire/wait/release.

Ресурсы единичные. Строится граф ожидания: поток -> поток, который
держит нужный ему ресурс. Цикл в этом графе и есть взаимоблокировка."""
import sys

from waitgraph import find_cycle


class LogError(Exception):
    pass


def build_graph(waiting, owner):
    """Граф ожидания: ждущий поток -> владелец ресурса, которого он ждёт."""
    graph = {}
    for thread, resource in waiting.items():
        # если ресурс уже освободили, поток больше не заблокирован
        if resource in owner:
            graph[thread] = {owner[resource]}
    return graph


def analyze(lines):
    """Разбирает журнал. Возвращает (найденные циклы, конечный граф, ждут, владельцы)."""
    owner = {}      # ресурс -> поток, который его держит
    waiting = {}    # поток -> ресурс, которого он ждёт
    reported = []   # (номер строки, цикл)
    seen = set()

    for number, line in enumerate(lines, 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) != 3 or parts[0] not in ("acquire", "wait", "release"):
            raise LogError(f"строка {number}: не понял «{line}»")
        action, thread, resource = parts

        if action == "acquire":
            if resource in owner:
                raise LogError(f"строка {number}: {resource} уже занят потоком {owner[resource]}")
            if waiting.get(thread, resource) != resource:
                raise LogError(f"строка {number}: {thread} ждал другой ресурс")
            waiting.pop(thread, None)
            owner[resource] = thread
        elif action == "wait":
            if resource not in owner:
                raise LogError(f"строка {number}: {thread} ждёт свободный ресурс {resource}")
            if thread in waiting:
                raise LogError(f"строка {number}: {thread} уже ждёт {waiting[thread]}")
            waiting[thread] = resource
        else:
            if owner.get(resource) != thread:
                raise LogError(f"строка {number}: {thread} не держит {resource}")
            del owner[resource]

        cycle = find_cycle(build_graph(waiting, owner))
        if cycle and frozenset(cycle) not in seen:
            seen.add(frozenset(cycle))
            reported.append((number, cycle))

    return reported, build_graph(waiting, owner), waiting, owner


def main():
    if len(sys.argv) != 2:
        print("Использование: deadlock_detector.py журнал.log")
        return 2
    try:
        with open(sys.argv[1], encoding="utf-8") as f:
            lines = f.readlines()
        found, graph, waiting, owner = analyze(lines)
    except (OSError, LogError) as error:
        print(f"Ошибка: {error}")
        return 2

    print(f"Журнал: {sys.argv[1]}")
    for number, cycle in found:
        print(f"Строка {number}: найден цикл ожидания {' -> '.join(cycle + [cycle[0]])}")

    print("Граф ожидания в конце (кто кого ждёт):")
    if not graph:
        print("  нет ждущих потоков")
    for thread in sorted(graph):
        (target,) = graph[thread]
        print(f"  {thread} ждёт {waiting[thread]}, его держит {target}")

    if found:
        members = sorted({t for _, cycle in found for t in cycle})
        print("Итог: ВЗАИМОБЛОКИРОВКА, участники: " + ", ".join(members))
        others = sorted(t for t in waiting if t not in members)
        if others:
            print("Ждут, но в цикл не входят: " + ", ".join(others))
        return 1
    print("Итог: взаимоблокировки нет")
    return 0


if __name__ == "__main__":
    sys.exit(main())
