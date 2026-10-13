#!/usr/bin/env python3
"""Симулятор планирования CPU: FCFS, SJF, SRTF, Priority, RR."""
import argparse
import sys
from collections import deque


class Process:
    def __init__(self, pid, arrival, burst, priority=1, order=0):
        self.pid = pid
        self.arrival = arrival
        self.burst = burst
        self.priority = priority
        self.order = order


def read_processes(path):
    processes = []

    with open(path, encoding="utf-8") as source:
        for line in source:
            line = line.strip()

            if not line or line.startswith("#"):
                continue

            parts = line.split()

            if len(parts) not in (3, 4):
                raise ValueError(f"Неверная строка: {line!r}")

            pid = parts[0]
            arrival = int(parts[1])
            burst = int(parts[2])
            priority = int(parts[3]) if len(parts) == 4 else 1

            if burst <= 0 or arrival < 0:
                raise ValueError(f"Неверные числа: {line!r}")

            processes.append(
                Process(pid, arrival, burst, priority, len(processes))
            )

    if not processes:
        raise ValueError("Во входном файле нет процессов")

    return processes


def add_interval(intervals, pid, start, end):
    """Добавляет отрезок и склеивает его с предыдущим, если процесс тот же."""
    if intervals and intervals[-1][0] == pid and intervals[-1][2] == start:
        intervals[-1] = (pid, intervals[-1][1], end)
    else:
        intervals.append((pid, start, end))


def by_arrival(processes):
    return sorted(processes, key=lambda p: (p.arrival, p.order))


def run_nonpreemptive(processes, key):
    """FCFS и SJF: выбранный процесс работает до конца."""
    waiting = by_arrival(processes)
    intervals = []
    time = 0

    while waiting:
        ready = [p for p in waiting if p.arrival <= time]

        if not ready:
            time = min(p.arrival for p in waiting)
            continue

        chosen = min(ready, key=key)
        waiting.remove(chosen)
        add_interval(intervals, chosen.pid, time, time + chosen.burst)
        time += chosen.burst

    return intervals


def run_round_robin(processes, quantum):
    """RR. Процесс, пришедший в момент t, встаёт в очередь раньше
    процесса, вытесненного в тот же момент t."""
    if quantum < 1:
        raise ValueError("Квант должен быть не меньше 1")

    incoming = by_arrival(processes)
    remaining = {p.pid: p.burst for p in processes}
    queue = deque()
    intervals = []
    time = 0
    index = 0

    def admit(now):
        nonlocal index
        while index < len(incoming) and incoming[index].arrival <= now:
            queue.append(incoming[index])
            index += 1

    while index < len(incoming) or queue:
        admit(time)

        if not queue:
            time = incoming[index].arrival
            continue

        process = queue.popleft()
        run = min(quantum, remaining[process.pid])
        add_interval(intervals, process.pid, time, time + run)
        time += run
        remaining[process.pid] -= run

        admit(time)

        if remaining[process.pid] > 0:
            queue.append(process)

    return intervals


def run_preemptive(processes, mode, aging=0):
    """SRTF и Priority с вытеснением. Решение принимается на каждом такте.

    Priority: меньшее число означает более высокий приоритет.
    Старение: каждые aging тактов ожидания приоритет улучшается на 1.
    Пока процесс работает, накопленное улучшение сохраняется.
    """
    remaining = {p.pid: p.burst for p in processes}
    priority = {p.pid: p.priority for p in processes}
    waited = {p.pid: 0 for p in processes}
    intervals = []
    time = 0
    current = None
    done = 0

    while done < len(processes):
        ready = [
            p for p in processes
            if p.arrival <= time and remaining[p.pid] > 0
        ]

        if not ready:
            time = min(
                p.arrival for p in processes if remaining[p.pid] > 0
            )
            current = None
            continue

        def key(p):
            if mode == "srtf":
                main = remaining[p.pid]
            else:
                main = priority[p.pid]

            keep = 0 if p.pid == current else 1
            return (main, keep, p.arrival, p.order)

        chosen = min(ready, key=key)
        current = chosen.pid
        add_interval(intervals, chosen.pid, time, time + 1)
        remaining[chosen.pid] -= 1
        waited[chosen.pid] = 0
        time += 1

        if remaining[chosen.pid] == 0:
            done += 1
            current = None

        if mode == "priority" and aging > 0:
            for p in ready:
                if p.pid == chosen.pid:
                    continue

                waited[p.pid] += 1

                if waited[p.pid] >= aging:
                    priority[p.pid] -= 1
                    waited[p.pid] = 0

    return intervals


def simulate(processes, algorithm, **params):
    """Единая точка входа. Возвращает список (pid, начало, конец)."""
    if algorithm == "fcfs":
        return run_nonpreemptive(
            processes, key=lambda p: (p.arrival, p.order)
        )

    if algorithm == "sjf":
        return run_nonpreemptive(
            processes, key=lambda p: (p.burst, p.arrival, p.order)
        )

    if algorithm == "srtf":
        return run_preemptive(processes, "srtf")

    if algorithm == "priority":
        return run_preemptive(
            processes, "priority", aging=params.get("aging", 0)
        )

    if algorithm == "rr":
        return run_round_robin(processes, params.get("quantum", 3))

    raise ValueError(f"Неизвестный алгоритм: {algorithm}")


def calculate_metrics(processes, intervals):
    first_start = {}
    finish = {}

    for pid, start, end in intervals:
        first_start.setdefault(pid, start)
        finish[pid] = end

    rows = []

    for p in processes:
        turnaround = finish[p.pid] - p.arrival
        waiting = turnaround - p.burst
        response = first_start[p.pid] - p.arrival
        rows.append({
            "pid": p.pid,
            "arrival": p.arrival,
            "burst": p.burst,
            "priority": p.priority,
            "finish": finish[p.pid],
            "waiting": waiting,
            "turnaround": turnaround,
            "response": response,
        })

    count = len(rows)
    busy = sum(p.burst for p in processes)
    span = max(finish.values()) - min(p.arrival for p in processes)

    # Переключение: смена процесса на процессоре между соседними отрезками.
    switches = sum(
        1 for a, b in zip(intervals, intervals[1:]) if a[0] != b[0]
    )

    return {
        "rows": rows,
        "avg_waiting": sum(r["waiting"] for r in rows) / count,
        "avg_turnaround": sum(r["turnaround"] for r in rows) / count,
        "avg_response": sum(r["response"] for r in rows) / count,
        "utilization": 100.0 * busy / span,
        "switches": switches,
    }


def format_gantt(intervals, per_line=12):
    cells = []
    previous_end = None

    for pid, start, end in intervals:
        if previous_end is not None and start > previous_end:
            cells.append(("idle", previous_end, start))

        cells.append((pid, start, end))
        previous_end = end

    lines = []

    for offset in range(0, len(cells), per_line):
        chunk = cells[offset:offset + per_line]
        top = "|"
        bottom = ""

        for pid, start, end in chunk:
            width = max(len(pid), len(str(start)), len(str(end))) + 2
            top += pid.center(width) + "|"
            bottom += str(start).ljust(width + 1)

        bottom += str(chunk[-1][2])
        lines.append(top)
        lines.append(bottom)

    return "\n".join(lines)


def algorithm_title(algorithm, params):
    if algorithm == "rr":
        return f"RR (q={params.get('quantum', 3)})"

    if algorithm == "priority" and params.get("aging", 0) > 0:
        return f"Priority (старение каждые {params['aging']} тактов)"

    names = {
        "fcfs": "FCFS",
        "sjf": "SJF",
        "srtf": "SRTF",
        "priority": "Priority (вытесняющий)",
    }
    return names[algorithm]


def print_report(path, algorithm, params, show_gantt):
    processes = read_processes(path)
    intervals = simulate(processes, algorithm, **params)
    result = calculate_metrics(processes, intervals)

    print(f"Алгоритм: {algorithm_title(algorithm, params)}")
    print(f"Файл: {path}")

    if show_gantt:
        print()
        print("Диаграмма Ганта:")
        print(format_gantt(intervals))

    print()
    print("PID   приход  burst  prio  конец  ожидание  оборот  отклик")

    for r in result["rows"]:
        print(
            f"{r['pid']:<5} {r['arrival']:>6} {r['burst']:>6} "
            f"{r['priority']:>5} {r['finish']:>6} {r['waiting']:>9} "
            f"{r['turnaround']:>7} {r['response']:>7}"
        )

    print()
    print(f"Среднее ожидание: {result['avg_waiting']:.2f}")
    print(f"Средний оборот: {result['avg_turnaround']:.2f}")
    print(f"Среднее время отклика: {result['avg_response']:.2f}")
    print(f"Загрузка CPU: {result['utilization']:.1f}%")
    print(f"Переключений контекста: {result['switches']}")


def main():
    parser = argparse.ArgumentParser(description="Симулятор планирования CPU")
    parser.add_argument("input", help="файл с процессами")
    parser.add_argument(
        "--algo",
        required=True,
        choices=["fcfs", "sjf", "srtf", "priority", "rr"],
    )
    parser.add_argument("--quantum", type=int, default=3)
    parser.add_argument("--aging", type=int, default=0)
    parser.add_argument("--gantt", action="store_true")
    args = parser.parse_args()

    params = {}

    if args.algo == "rr":
        params["quantum"] = args.quantum

    if args.algo == "priority":
        params["aging"] = args.aging

    try:
        print_report(args.input, args.algo, params, args.gantt)
    except (OSError, ValueError) as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
