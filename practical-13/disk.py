#!/usr/bin/env python3
"""ПР-13: алгоритмы планирования обращений к диску.

Единый интерфейс: алгоритм(очередь, головка, направление, цилиндров) -> Schedule
(порядок обслуживания и путь головки). Направление +1 = к бо́льшим номерам.

Соглашения (как в Silberschatz и в эталоне УМК):
  SCAN    доезжает до края диска (199), потом разворачивается;
  LOOK    разворачивается на последнем запросе, до края не едет;
  C-SCAN  доезжает до края, возвращается в цилиндр 0 и едет снова вверх;
          возврат 199 -> 0 ЗАСЧИТЫВАЕТСЯ в перемещение;
  C-LOOK  после последнего запроса прыгает к самому младшему запросу;
          прыжок тоже засчитывается.

Запуск:
    ./disk.py                     # контрольный набор и сверка с эталоном
    ./disk.py -v                  # плюс путь головки
    ./disk.py -q "10 20 150" -H 100 -d down
"""
import argparse
import sys

CYLINDERS = 200
HEAD = 53
QUEUE = [98, 183, 37, 122, 14, 124, 65, 67]
REFERENCE = {"FCFS": 640, "SSTF": 236, "SCAN": 331, "C-SCAN": 382, "LOOK": 299, "C-LOOK": 322}


class Schedule:
    def __init__(self, head):
        self.order = []          # порядок обслуживания запросов
        self.path = [head]       # все точки, где головка была (включая края и прыжки)

    def go(self, cyl, serve=True):
        self.path.append(cyl)
        if serve:
            self.order.append(cyl)

    @property
    def movement(self):
        return sum(abs(b - a) for a, b in zip(self.path, self.path[1:]))


def fcfs(queue, head, direction=1, cylinders=CYLINDERS):
    s = Schedule(head)
    for c in queue:
        s.go(c)
    return s


def sstf(queue, head, direction=1, cylinders=CYLINDERS):
    """Каждый раз ближайший запрос. При равном расстоянии - в текущем направлении."""
    s, pos, left = Schedule(head), head, list(queue)
    while left:
        c = min(left, key=lambda x: (abs(x - pos), (x - pos) * direction < 0))
        left.remove(c)
        s.go(c)
        pos = c
    return s


def _split(queue, head, direction):
    """Запросы по ходу движения (в порядке обслуживания) и позади головки."""
    ahead = sorted(c for c in queue if (c - head) * direction >= 0)
    behind = sorted(c for c in queue if (c - head) * direction < 0)
    if direction < 0:
        ahead.reverse()
        behind.reverse()
    return ahead, behind


def scan(queue, head, direction=1, cylinders=CYLINDERS):
    s = Schedule(head)
    ahead, behind = _split(queue, head, direction)
    for c in ahead:
        s.go(c)
    if behind:
        edge = cylinders - 1 if direction > 0 else 0
        if not s.path or s.path[-1] != edge:
            s.go(edge, serve=False)          # доехать до края
        for c in reversed(behind):           # обратный ход: от ближнего к дальнему
            s.go(c)
    return s


def look(queue, head, direction=1, cylinders=CYLINDERS):
    s = Schedule(head)
    ahead, behind = _split(queue, head, direction)
    for c in ahead:
        s.go(c)
    for c in reversed(behind):
        s.go(c)
    return s


def cscan(queue, head, direction=1, cylinders=CYLINDERS):
    s = Schedule(head)
    ahead, behind = _split(queue, head, direction)
    for c in ahead:
        s.go(c)
    if behind:
        edge, start = (cylinders - 1, 0) if direction > 0 else (0, cylinders - 1)
        if s.path[-1] != edge:
            s.go(edge, serve=False)          # до края
        s.go(start, serve=False)             # возврат через весь диск (засчитывается)
        for c in behind:                     # снова в том же направлении
            s.go(c)
    return s


def clook(queue, head, direction=1, cylinders=CYLINDERS):
    s = Schedule(head)
    ahead, behind = _split(queue, head, direction)
    for c in ahead:
        s.go(c)
    for c in behind:                         # прыжок к самому дальнему позади, дальше по ходу
        s.go(c)
    return s


ALGORITHMS = {"FCFS": fcfs, "SSTF": sstf, "SCAN": scan, "C-SCAN": cscan, "LOOK": look, "C-LOOK": clook}


def main(argv):
    p = argparse.ArgumentParser(description="Планирование диска")
    p.add_argument("-q", "--queue", help="очередь цилиндров через пробел")
    p.add_argument("-H", "--head", type=int, default=HEAD)
    p.add_argument("-d", "--direction", choices=["up", "down"], default="up")
    p.add_argument("-c", "--cylinders", type=int, default=CYLINDERS)
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args(argv)
    queue = [int(x) for x in args.queue.split()] if args.queue else QUEUE
    if not all(0 <= c < args.cylinders for c in queue + [args.head]):
        p.error(f"цилиндры должны быть в диапазоне 0..{args.cylinders - 1}")
    direction = 1 if args.direction == "up" else -1
    control = not args.queue and args.head == HEAD and direction == 1 and args.cylinders == CYLINDERS

    print(f"Цилиндров {args.cylinders}, головка {args.head}, направление {args.direction}, "
          f"очередь: {' '.join(map(str, queue))}")
    print(f"{'алгоритм':>8}  {'путь':>5}  {'эталон':>6}  порядок обслуживания")
    for name, fn in ALGORITHMS.items():
        s = fn(queue, args.head, direction, args.cylinders)
        ref = REFERENCE[name] if control else ""
        mark = "" if not control else ("  ok" if s.movement == ref else "  ОТЛИЧАЕТСЯ")
        print(f"{name:>8}  {s.movement:>5}  {ref:>6}  {' '.join(map(str, s.order))}{mark}")
        if args.verbose:
            print(f"{'':>8}  путь головки: {' -> '.join(map(str, s.path))}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
