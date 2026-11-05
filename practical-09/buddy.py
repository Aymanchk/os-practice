#!/usr/bin/env python3
"""Buddy system: память делится пополам, размеры блоков только степени двойки."""
from memsim import MEMORY, step_line


class Buddy:
    def __init__(self, log=False):
        self.free = {MEMORY: [0]}     # размер → адреса свободных блоков
        self.owned = {}               # pid → (адрес, блок, запрошено)
        self.refused, self.log = 0, log

    def alloc(self, pid, size):
        need = 1                      # 1. округляем запрос вверх до степени двойки
        while need < size:
            need *= 2
        s = need                      # 2. ищем свободный блок размера need или больше
        while s <= MEMORY and not self.free.get(s):
            s *= 2
        if s > MEMORY:
            self.refused += 1
            return False
        addr = min(self.free[s])      # из одинаковых берём тот, что левее
        self.free[s].remove(addr)
        while s > need:               # 3. делим пополам до нужного; правые половины свободны
            s //= 2
            self.free.setdefault(s, []).append(addr + s)
            if self.log:
                print(f"   делим → {s}+{s}")
        self.owned[pid] = (addr, need, size)
        return True

    def release(self, pid):
        """Освобождает блок и склеивает его с "другом". True, если процесс был в памяти."""
        if pid not in self.owned:     # alloc мог быть отклонён
            return False
        addr, s, _ = self.owned.pop(pid)
        while s < MEMORY:
            friend = addr ^ s         # адрес "друга" отличается от адреса блока одним битом
            if friend in self.free.get(s, []):
                self.free[s].remove(friend)
                addr, s = min(addr, friend), s * 2
                if self.log:
                    print(f"   слияние → {s}")
            else:
                break
        self.free.setdefault(s, []).append(addr)
        self.free[s].sort()
        return True

    def blocks(self):
        """Все блоки по порядку адресов: (адрес, размер, pid или None)."""
        result = [(addr, size, pid) for pid, (addr, size, _) in self.owned.items()]
        for size, addrs in self.free.items():
            result.extend((addr, size, None) for addr in addrs)
        return sorted(result)

    def show(self):
        return " ".join(f"[{pid or '-'}:{size}]" for _, size, pid in self.blocks())

    def stats(self):
        """(сколько свободно, самый большой свободный блок, потери внутри блоков)."""
        holes = [s for s, lst in self.free.items() for _ in lst]
        internal = sum(b - r for _, b, r in self.owned.values())
        return sum(holes), max(holes, default=0), internal


def run_buddy(ops, verbose=False, log=False):
    """Выполняет операции на buddy system. С verbose печатает карту после каждой."""
    buddy = Buddy(log=log)
    for n, op in enumerate(ops, 1):
        cmd, pid, *rest = op
        failed = False
        if cmd == "alloc":
            failed = not buddy.alloc(pid, rest[0])
        else:
            buddy.release(pid)
        if verbose:
            print(step_line(n, op, buddy.show(), failed))
    return buddy
