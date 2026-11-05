#!/usr/bin/env python3
"""Симулятор динамического распределения памяти: first fit, best fit, worst fit."""

MEMORY = 1024
STRATEGIES = ("first", "best", "worst")


class Block:
    """Участок памяти: начало, размер и владелец. pid = None значит "свободен"."""

    def __init__(self, start, size, pid=None):
        self.start, self.size, self.pid = start, size, pid

    @property
    def free(self):
        return self.pid is None


class MemoryManager:
    def __init__(self, strategy="first", coalesce=False):
        if strategy not in STRATEGIES:
            raise ValueError(f"неизвестная стратегия {strategy!r}, нужна одна из {STRATEGIES}")
        self.blocks = [Block(0, MEMORY)]
        self.strategy = strategy
        self.coalesce = coalesce
        self.refused = 0          # сколько запросов отклонено

    def candidates(self, size):
        """Все свободные дыры, куда запрос помещается (в порядке адресов)."""
        return [b for b in self.blocks if b.free and b.size >= size]

    def choose(self, size):
        """Выбирает одну дыру по стратегии или None, если подходящей нет."""
        c = self.candidates(size)
        if not c:
            return None
        if self.strategy == "first":
            return c[0]                                   # первая по адресу
        if self.strategy == "best":
            return min(c, key=lambda b: b.size)           # самая маленькая из подходящих
        return max(c, key=lambda b: b.size)               # worst: самая большая

    def alloc(self, pid, size):
        hole = self.choose(size)
        if hole is None:
            self.refused += 1
            return False
        i = self.blocks.index(hole)
        self.blocks[i] = Block(hole.start, size, pid)
        if hole.size > size:
            rest = Block(hole.start + size, hole.size - size)
            self.blocks.insert(i + 1, rest)
        return True

    def free(self, pid):
        """Освобождает блоки процесса. Возвращает True, если что-то освободилось."""
        found = False
        for b in self.blocks:
            if b.pid == pid:
                b.pid = None
                found = True
        if self.coalesce:
            self.merge()
        return found

    def merge(self):
        """Склеивает соседние свободные дыры в одну (один проход по списку)."""
        merged = [self.blocks[0]]
        for b in self.blocks[1:]:
            last = merged[-1]
            if last.free and b.free:
                last.size += b.size
            else:
                merged.append(b)
        self.blocks = merged

    def stats(self):
        """(сколько свободно, самая большая дыра, сколько дыр)."""
        holes = [b.size for b in self.blocks if b.free]
        return sum(holes), max(holes, default=0), len(holes)

    def show(self):
        parts = [f"[{b.pid or '-'}:{b.size}]" for b in self.blocks]
        return " ".join(parts)


def external_fragmentation(total, largest):
    """Доля свободной памяти вне самой большой дыры: 0 - одна дыра, ближе к 1 - пыль."""
    return 1 - largest / total if total else 0


def step_line(n, op, shown, failed):
    """Строка вывода после одной операции: номер, операция, размер и карта памяти."""
    cmd, pid, *rest = op
    size = rest[0] if rest else ""
    note = "  ← ОТКАЗ" if failed else ""
    return f"{n:>2} {cmd:<5} {pid:<3} {size:>4}  {shown}{note}"


def run(ops, strategy, coalesce=False, verbose=False):
    """Выполняет все операции. С verbose=True печатает карту после каждой."""
    mm = MemoryManager(strategy, coalesce)
    for n, op in enumerate(ops, 1):
        cmd, pid, *rest = op
        failed = False
        if cmd == "alloc":
            failed = not mm.alloc(pid, rest[0])
        else:
            mm.free(pid)
        if verbose:
            print(step_line(n, op, mm.show(), failed))
    return mm


def load(path):
    """Читает файл операций. Строки: alloc PID размер, free PID. Пустые строки и # пропускаются.
    Возвращает список кортежей ("alloc", pid, размер) и ("free", pid)."""
    ops = []
    with open(path, encoding="utf-8") as f:
        for number, line in enumerate(f, 1):
            text = line.split("#", 1)[0].strip()
            if not text:
                continue
            p = text.split()
            try:
                if p[0] == "alloc" and len(p) == 3:
                    size = int(p[2])
                    if size <= 0:
                        raise ValueError("размер должен быть больше нуля")
                    ops.append(("alloc", p[1], size))
                elif p[0] == "free" and len(p) == 2:
                    ops.append(("free", p[1]))
                else:
                    raise ValueError("ожидалось alloc PID размер или free PID")
            except ValueError as error:
                raise ValueError(f"{path}:{number}: {error}") from None
    return ops
