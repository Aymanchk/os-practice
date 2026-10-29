#!/usr/bin/env python3
"""Планировщик процессов: FCFS, SJF, RR, SRTF, Priority (+ старение), MLFQ.

Автор: Эркинбеков Айман

Только стандартная библиотека Python 3.8+, никаких внешних пакетов.

Соглашения (как в ПР-5):
  * время целое, процессор простаивает, если готовых процессов нет;
  * при равенстве выбирается процесс, пришедший раньше, затем с меньшим номером PID;
  * в RR процессы, пришедшие во время кванта или ровно в момент его окончания,
    встают в очередь РАНЬШЕ процесса, у которого закончился квант;
  * меньшее число priority = более высокий приоритет.

Метрики:
  оборот (turnaround) = завершение - прибытие
  ожидание (waiting)  = оборот - burst
  отклик (response)   = первый запуск - прибытие
  переключения        = сколько раз процессор перешёл с одного процесса на другой
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple


# ---------------------------------------------------------------- данные

@dataclass(frozen=True)
class Process:
    pid: str
    arrival: int
    burst: int
    priority: int

    @property
    def num(self) -> int:
        digits = "".join(ch for ch in self.pid if ch.isdigit())
        return int(digits) if digits else 0


def load(path: str) -> List[Process]:
    """Читает файл "PID arrival burst priority", строки с # и пустые пропускает."""
    procs = []
    with open(path, encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) < 4:
                raise ValueError(f"{path}:{line_no}: нужно 4 поля, а получено {len(parts)}: {line!r}")
            pid, arrival, burst, priority = parts[0], int(parts[1]), int(parts[2]), int(parts[3])
            if arrival < 0 or burst <= 0:
                raise ValueError(f"{path}:{line_no}: arrival >= 0 и burst > 0")
            procs.append(Process(pid, arrival, burst, priority))
    if not procs:
        raise ValueError(f"{path}: нет ни одного процесса")
    return procs


Segment = Tuple[Optional[str], int, int]  # (pid или None = простой, начало, конец)


@dataclass
class Result:
    name: str
    procs: List[Process]
    gantt: List[Segment]
    finish: Dict[str, int]
    first_start: Dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for pid, start, _ in self.gantt:
            if pid is not None and pid not in self.first_start:
                self.first_start[pid] = start

    # --- по процессам
    def turnaround(self, p: Process) -> int:
        return self.finish[p.pid] - p.arrival

    def waiting(self, p: Process) -> int:
        return self.turnaround(p) - p.burst

    def response(self, p: Process) -> int:
        return self.first_start[p.pid] - p.arrival

    # --- средние
    def _avg(self, fn: Callable[[Process], int], procs: Optional[List[Process]] = None) -> float:
        procs = self.procs if procs is None else procs
        return sum(fn(p) for p in procs) / len(procs)

    def avg_waiting(self, procs: Optional[List[Process]] = None) -> float:
        return self._avg(self.waiting, procs)

    def avg_turnaround(self, procs: Optional[List[Process]] = None) -> float:
        return self._avg(self.turnaround, procs)

    def avg_response(self, procs: Optional[List[Process]] = None) -> float:
        return self._avg(self.response, procs)

    @property
    def switches(self) -> int:
        run = [pid for pid, _, _ in self.gantt if pid is not None]
        return sum(1 for a, b in zip(run, run[1:]) if a != b)

    @property
    def makespan(self) -> int:
        return self.gantt[-1][2]


def _add(gantt: List[Segment], pid: Optional[str], start: int, end: int) -> None:
    """Добавляет отрезок в диаграмму Ганта, склеивая соседние отрезки одного процесса."""
    if end <= start:
        return
    if gantt and gantt[-1][0] == pid and gantt[-1][2] == start:
        gantt[-1] = (pid, gantt[-1][1], end)
    else:
        gantt.append((pid, start, end))


def _tie(p: Process) -> Tuple[int, int]:
    return (p.arrival, p.num)


# ------------------------------------------------- невытесняющие алгоритмы

def fcfs(procs: List[Process]) -> Result:
    gantt: List[Segment] = []
    finish: Dict[str, int] = {}
    t = 0
    for p in sorted(procs, key=_tie):
        if t < p.arrival:
            _add(gantt, None, t, p.arrival)
            t = p.arrival
        _add(gantt, p.pid, t, t + p.burst)
        t += p.burst
        finish[p.pid] = t
    return Result("FCFS", list(procs), gantt, finish)


def sjf(procs: List[Process]) -> Result:
    """Невытесняющий SJF: из пришедших берём самый короткий burst."""
    gantt: List[Segment] = []
    finish: Dict[str, int] = {}
    left = list(procs)
    t = 0
    while left:
        ready = [p for p in left if p.arrival <= t]
        if not ready:
            nxt = min(p.arrival for p in left)
            _add(gantt, None, t, nxt)
            t = nxt
            continue
        p = min(ready, key=lambda x: (x.burst,) + _tie(x))
        _add(gantt, p.pid, t, t + p.burst)
        t += p.burst
        finish[p.pid] = t
        left.remove(p)
    return Result("SJF", list(procs), gantt, finish)


# ------------------------------------------------------------ Round Robin

def rr(procs: List[Process], q: int = 2) -> Result:
    if q <= 0:
        raise ValueError("квант должен быть > 0")
    pending = sorted(procs, key=_tie)
    rem = {p.pid: p.burst for p in procs}
    queue: deque = deque()
    gantt: List[Segment] = []
    finish: Dict[str, int] = {}
    i, t = 0, 0

    def admit(upto: int) -> None:
        nonlocal i
        while i < len(pending) and pending[i].arrival <= upto:
            queue.append(pending[i])
            i += 1

    admit(0)
    while queue or i < len(pending):
        if not queue:
            _add(gantt, None, t, pending[i].arrival)
            t = pending[i].arrival
            admit(t)
            continue
        p = queue.popleft()
        run = min(q, rem[p.pid])
        _add(gantt, p.pid, t, t + run)
        t += run
        rem[p.pid] -= run
        admit(t)  # новые процессы встают в очередь раньше вытесненного
        if rem[p.pid] > 0:
            queue.append(p)
        else:
            finish[p.pid] = t
    return Result(f"RR q={q}", list(procs), gantt, finish)


# ------------------------------------------- вытесняющие (шаг = 1 единица)

def _preemptive(procs: List[Process], name: str, mode: str, aging: int = 0) -> Result:
    """SRTF и Priority с вытеснением, решение на каждом такте (как в ПР-5).

    При равенстве главного критерия работающий процесс не вытесняется.
    Старение (только Priority): каждые aging тактов подряд в очереди
    приоритет улучшается на 1; когда процесс получил процессор, счётчик
    сбрасывается, а улучшенный приоритет сохраняется.
    Автор: Эркинбеков Айман
    """
    rem = {p.pid: p.burst for p in procs}
    prio = {p.pid: p.priority for p in procs}
    waited = {p.pid: 0 for p in procs}
    gantt: List[Segment] = []
    finish: Dict[str, int] = {}
    current: Optional[str] = None
    t = 0
    while len(finish) < len(procs):
        ready = [p for p in procs if p.arrival <= t and rem[p.pid] > 0]
        if not ready:
            nxt = min(p.arrival for p in procs if rem[p.pid] > 0)
            _add(gantt, None, t, nxt)
            t = nxt
            current = None
            continue

        def key(x: Process) -> tuple:
            main = rem[x.pid] if mode == "srtf" else prio[x.pid]
            keep = 0 if x.pid == current else 1
            return (main, keep) + _tie(x)

        p = min(ready, key=key)
        current = p.pid
        _add(gantt, p.pid, t, t + 1)
        rem[p.pid] -= 1
        waited[p.pid] = 0
        t += 1
        if rem[p.pid] == 0:
            finish[p.pid] = t
            current = None
        if aging > 0:
            for other in ready:
                if other is p:
                    continue
                waited[other.pid] += 1
                if waited[other.pid] >= aging:
                    prio[other.pid] -= 1
                    waited[other.pid] = 0
    return Result(name, list(procs), gantt, finish)


def srtf(procs: List[Process]) -> Result:
    """Автор: Эркинбеков Айман"""
    return _preemptive(procs, "SRTF", "srtf")


def priority(procs: List[Process]) -> Result:
    """Вытесняющий приоритетный: меньшее число = выше приоритет.
    Автор: Эркинбеков Айман"""
    return _preemptive(procs, "Priority", "priority")


def priority_aging(procs: List[Process], step: int = 5) -> Result:
    """Priority со старением: каждые step тактов ожидания приоритет улучшается на 1.
    Автор: Эркинбеков Айман"""
    if step <= 0:
        raise ValueError("шаг старения должен быть > 0")
    return _preemptive(procs, f"Priority+aging({step})", "priority", aging=step)


# ------------------------------------------------------------------- MLFQ

def mlfq(procs: List[Process], quanta: Tuple[int, ...] = (2, 4, 8), boost: int = 50) -> Result:
    """Многоуровневая очередь с обратной связью.

    * новый процесс попадает на верхний уровень 0;
    * израсходовал весь квант уровня -> понижается на уровень ниже
      (на последнем уровне остаётся и работает как RR);
    * процесс с более высокого уровня сразу вытесняет процесс с нижнего уровня,
      вытесненный встаёт в конец своей очереди и сохраняет уже потраченную часть кванта;
    * каждые boost единиц времени все процессы поднимаются на уровень 0 (boost).
    """
    n_levels = len(quanta)
    levels: List[deque] = [deque() for _ in range(n_levels)]
    level: Dict[str, int] = {}
    used: Dict[str, int] = {}
    rem = {p.pid: p.burst for p in procs}
    pending = sorted(procs, key=_tie)
    gantt: List[Segment] = []
    finish: Dict[str, int] = {}
    current: Optional[Process] = None
    i, t = 0, 0

    def admit(upto: int) -> None:
        nonlocal i
        while i < len(pending) and pending[i].arrival <= upto:
            p = pending[i]
            level[p.pid], used[p.pid] = 0, 0
            levels[0].append(p)
            i += 1

    while len(finish) < len(procs):
        admit(t)

        if boost and t > 0 and t % boost == 0:
            everyone = [p for lv in levels for p in lv]
            for lv in levels:
                lv.clear()
            if current is not None:
                everyone.insert(0, current)
            for p in everyone:
                level[p.pid], used[p.pid] = 0, 0
            levels[0].extend(p for p in everyone if p is not current)

        if current is not None and any(levels[k] for k in range(level[current.pid])):
            levels[level[current.pid]].append(current)  # вытеснение более высоким уровнем
            current = None

        if current is None:
            for lv in levels:
                if lv:
                    current = lv.popleft()
                    break
        if current is None:  # никто не готов -> простой до следующего прибытия
            nxt = pending[i].arrival
            _add(gantt, None, t, nxt)
            t = nxt
            continue

        p = current
        _add(gantt, p.pid, t, t + 1)
        t += 1
        rem[p.pid] -= 1
        used[p.pid] += 1
        admit(t)  # пришедшие встают раньше процесса, у которого кончился квант
        if rem[p.pid] == 0:
            finish[p.pid] = t
            current = None
        elif used[p.pid] >= quanta[level[p.pid]]:
            level[p.pid] = min(level[p.pid] + 1, n_levels - 1)
            used[p.pid] = 0
            levels[level[p.pid]].append(p)
            current = None
    name = "MLFQ q=" + "/".join(map(str, quanta)) + (f" boost={boost}" if boost else " без boost")
    return Result(name, list(procs), gantt, finish)


ALGORITHMS = {
    "fcfs": fcfs,
    "sjf": sjf,
    "rr": rr,
    "srtf": srtf,
    "priority": priority,
    "aging": priority_aging,
    "mlfq": mlfq,
}


# ----------------------------------------------------------------- вывод

def fmt(x: float) -> str:
    """2.50 -> '2.5', 3.00 -> '3'."""
    s = f"{x:.2f}".rstrip("0").rstrip(".")
    return s if s != "-0" else "0"


def gantt_text(res: Result, scale: int = 1) -> str:
    """Текстовая диаграмма Ганта (ASCII), например:
    | P1      | P2  |
    0         7     11
    """
    top, bottom = "|", "0"
    for pid, start, end in res.gantt:
        label = pid if pid is not None else "--"
        width = max(len(label) + 1, (end - start) * scale)
        top += label.center(width) + "|"
        bottom += " " * (width + 1 - len(str(end))) + str(end)
    return top + "\n" + bottom


def gantt_compact(res: Result) -> str:
    """Короткая запись Ганта: P1[0-7] P2[7-11] ..."""
    return " ".join(f"{pid or 'idle'}[{s}-{e}]" for pid, s, e in res.gantt)


def process_table(res: Result) -> str:
    rows = ["| PID | Прибытие | Burst | Приоритет | Старт | Завершение | Ожидание | Оборот | Отклик |",
            "| --- | --: | --: | --: | --: | --: | --: | --: | --: |"]
    for p in sorted(res.procs, key=lambda x: x.num):
        rows.append(f"| {p.pid} | {p.arrival} | {p.burst} | {p.priority} | {res.first_start[p.pid]} | "
                    f"{res.finish[p.pid]} | {res.waiting(p)} | {res.turnaround(p)} | {res.response(p)} |")
    rows.append(f"| **Среднее** | | | | | | **{fmt(res.avg_waiting())}** | "
                f"**{fmt(res.avg_turnaround())}** | **{fmt(res.avg_response())}** |")
    return "\n".join(rows)
