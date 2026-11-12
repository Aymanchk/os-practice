#!/usr/bin/env python3
"""ПР-10, вариант B: TLB на K записей с замещением LRU и эффективное время доступа.

Запуск:
    ./tlb.py              # TLB на 4 записи, прогон refs.txt, таблица EAT
    ./tlb.py -k 2         # другой размер TLB
    ./tlb.py -v           # hit/miss по каждому обращению
"""
import argparse
import sys
from collections import OrderedDict

from translate import BadAddress, PAGE_SIZE, load_refs, load_table, split

MEM_NS = 100   # время одного обращения к памяти
TLB_NS = 10    # время поиска в TLB


class TLB:
    """Ассоциативный буфер трансляции: страница -> кадр, не больше K записей, LRU."""

    def __init__(self, size):
        if size < 1:
            raise ValueError("размер TLB должен быть не меньше 1")
        self.size = size
        self.entries = OrderedDict()   # порядок = от давно использованной к недавней
        self.hits = 0
        self.misses = 0

    def lookup(self, page):
        """Возвращает кадр при попадании (и делает запись самой свежей) или None."""
        if page in self.entries:
            self.entries.move_to_end(page)
            self.hits += 1
            return self.entries[page]
        self.misses += 1
        return None

    def insert(self, page, frame):
        """Кладёт трансляцию; при переполнении вытесняет самую давнюю (LRU)."""
        if page in self.entries:
            self.entries.move_to_end(page)
        elif len(self.entries) >= self.size:
            self.entries.popitem(last=False)
        self.entries[page] = frame

    @property
    def hit_ratio(self):
        total = self.hits + self.misses
        return self.hits / total if total else 0.0


def simulate(addrs, table, size, log=None):
    """Прогон обращений через TLB. Неверные адреса пропускаются, страничные отказы
    считаются отдельно: трансляции нет, в TLB ничего не кладётся."""
    tlb = TLB(size)
    faults = bad = 0
    for addr in addrs:
        try:
            page, offset = split(addr)
        except BadAddress:
            bad += 1
            if log is not None:
                log.append(f"{addr:>6}  неверный адрес, пропущен")
            continue
        frame = tlb.lookup(page)
        if frame is not None:
            status = "hit "
        else:
            frame = table.get(page)
            if frame is None:
                faults += 1
                if log is not None:
                    log.append(f"{addr:>6}  стр {page:>2}  miss  страничный отказ")
                continue
            tlb.insert(page, frame)
            status = "miss"
        if log is not None:
            log.append(f"{addr:>6}  стр {page:>2}  {status}  физ {frame * PAGE_SIZE + offset:>5}"
                       f"  TLB {list(tlb.entries)}")
    return tlb, faults, bad


def eat(hit_ratio, levels=1):
    """Эффективное время доступа: TLB ищется всегда; при промахе читается
    таблица страниц (levels обращений к памяти), затем сами данные."""
    hit = TLB_NS + MEM_NS
    miss = TLB_NS + levels * MEM_NS + MEM_NS
    return hit_ratio * hit + (1 - hit_ratio) * miss


def main(argv):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("-k", type=int, default=4, help="размер TLB (по умолчанию 4)")
    p.add_argument("-v", action="store_true", help="подробно по каждому обращению")
    args = p.parse_args(argv)
    if args.k < 1:
        p.error("размер TLB должен быть не меньше 1")

    table = load_table()
    addrs = load_refs()
    log = [] if args.v else None
    tlb, faults, bad = simulate(addrs, table, args.k, log)
    if log:
        print("\n".join(log))
        print()
    print(f"TLB: K = {args.k}, LRU; обращений {len(addrs)}: "
          f"hit {tlb.hits}, miss {tlb.misses}, из них отказов {faults}; неверных адресов {bad}")
    print(f"Доля попаданий h = {tlb.hits}/{tlb.hits + tlb.misses} = {tlb.hit_ratio:.3f}")
    print()
    print(f"EAT = h * ({TLB_NS} + {MEM_NS}) + (1 - h) * ({TLB_NS} + {MEM_NS} + {MEM_NS}), нс")
    print(f"{'h':>6}  {'EAT, нс':>8}  {'замедление':>10}")
    for h in (0.0, 0.5, 0.8, 0.9, 0.95, 0.98, 0.99, 1.0):
        e = eat(h)
        print(f"{h:>6.2f}  {e:>8.1f}  {e / MEM_NS:>9.2f}x")
    e = eat(tlb.hit_ratio)
    print(f"{tlb.hit_ratio:>6.3f}  {e:>8.1f}  {e / MEM_NS:>9.2f}x   <- измерено на refs.txt")
    print(f"без TLB: {2 * MEM_NS} нс (2.00x): таблица страниц + данные")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
