#!/usr/bin/env python3
"""ПР-10, вариант B: двухуровневая таблица страниц.

Номер страницы (4 бита) делится на p1 (2 бита, индекс во внешней таблице) и
p2 (2 бита, индекс во внутренней). Каждое чтение таблицы считается отдельным
обращением к памяти, поэтому видно, во что обходится трансляция без TLB.
Во второй части считается объём таблиц для 32-битного адреса (страницы 4 КБ).
"""
import sys

from translate import PAGE_SIZE, PAGES, BadAddress, PageFault, load_refs, load_table, split

P2_BITS = 2
INNER = 1 << P2_BITS                 # 4 записи во внутренней таблице
OUTER = PAGES // INNER               # 4 записи во внешней таблице


class TwoLevel:
    def __init__(self, table):
        # Внутренняя таблица создаётся, только если в ней есть хоть одна загруженная страница.
        self.outer = [None] * OUTER
        for page, frame in table.items():
            if frame is None:
                continue
            p1, p2 = divmod(page, INNER)
            if self.outer[p1] is None:
                self.outer[p1] = [None] * INNER
            self.outer[p1][p2] = frame
        self.mem_accesses = 0

    def translate(self, addr):
        """Возвращает (физический адрес, число обращений к памяти за трансляцию + данные)."""
        page, offset = split(addr)
        p1, p2 = divmod(page, INNER)
        before = self.mem_accesses
        self.mem_accesses += 1                       # чтение записи внешней таблицы
        inner = self.outer[p1]
        if inner is None:
            raise PageFault(f"внутренней таблицы {p1} нет")
        self.mem_accesses += 1                       # чтение записи внутренней таблицы
        frame = inner[p2]
        if frame is None:
            raise PageFault(f"страница {page} отсутствует")
        self.mem_accesses += 1                       # само обращение к данным
        return frame * PAGE_SIZE + offset, self.mem_accesses - before


def table_sizes():
    """32-битный адрес, страница 4 КБ, запись таблицы 4 Б."""
    entry = 4
    flat = (1 << 20) * entry                         # 2^20 записей
    outer = (1 << 10) * entry                        # внешняя: 2^10 записей
    inner = (1 << 10) * entry                        # одна внутренняя покрывает 4 МБ
    # Процесс: код 1 МБ внизу, куча 8 МБ, стек 1 МБ под самым верхом.
    regions = {"код (0 .. 1 МБ)": (0, 1 << 20),
               "куча (16 .. 24 МБ)": (16 << 20, 24 << 20),
               "стек (4 ГБ - 1 МБ .. 4 ГБ)": ((1 << 32) - (1 << 20), 1 << 32)}
    used_inner = set()
    for lo, hi in regions.values():
        for vpn in range(lo >> 12, hi >> 12):
            used_inner.add(vpn >> 10)
    return flat, outer, inner, regions, used_inner


def main():
    table = load_table()
    tl = TwoLevel(table)
    print(f"Логическое пространство {PAGES} страниц по {PAGE_SIZE} Б; "
          f"номер страницы = p1 ({OUTER} записи) + p2 ({INNER} записи)")
    print("Внешняя таблица:", ["есть" if t else "нет" for t in tl.outer])
    for i, t in enumerate(tl.outer):
        if t:
            print(f"  внутренняя {i}: страницы {i * INNER}..{i * INNER + INNER - 1} -> {t}")
    print()
    print(f"{'адрес':>6}  {'p1':>2} {'p2':>2} {'смещ':>4}  {'физ':>6}  обращений к памяти")
    for addr in load_refs()[:8]:
        try:
            page, offset = split(addr)
            phys, n = tl.translate(addr)
            print(f"{addr:>6}  {page // INNER:>2} {page % INNER:>2} {offset:>4}  {phys:>6}  {n}")
        except (PageFault, BadAddress) as e:
            print(f"{addr:>6}  отказ: {e}")
    print()
    print("Одна трансляция без TLB:")
    print("  одноуровневая таблица: 1 (таблица) + 1 (данные) = 2 обращения, 200 нс")
    print("  двухуровневая:         2 (две таблицы) + 1 (данные) = 3 обращения, 300 нс")
    print("  с TLB при попадании:   0 + 1 = 1 обращение (+10 нс на TLB), 110 нс")
    print()
    flat, outer, inner, regions, used = table_sizes()
    print("Объём таблиц для 32-битного адреса, страница 4 КБ, запись 4 Б:")
    print(f"  одноуровневая: 2^20 записей * 4 Б = {flat // 1024} КБ на каждый процесс")
    for name in regions:
        print(f"  область: {name}")
    two = outer + len(used) * inner
    print(f"  двухуровневая: внешняя {outer // 1024} КБ + {len(used)} внутренних по {inner // 1024} КБ"
          f" = {two // 1024} КБ (в {flat / two:.0f} раз меньше)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
