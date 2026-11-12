#!/usr/bin/env python3
"""ПР-10: трансляция логического адреса в физический по таблице страниц.

Запуск:
    ./translate.py                 # прогон refs.txt
    ./translate.py 1200 3100 5000  # перевести отдельные адреса
"""
import sys
from pathlib import Path

PAGE_SIZE = 1024          # 1 КБ, степень двойки: 2**10
PAGES = 16                # логическое пространство 16 КБ
ADDRESS_SPACE = PAGE_SIZE * PAGES

HERE = Path(__file__).resolve().parent


class PageFault(Exception):
    """Страница есть в адресном пространстве, но не загружена в кадр."""


class BadAddress(Exception):
    """Адрес за пределами логического адресного пространства."""


def load_table(path=HERE / "pagetable.txt"):
    """Читает pagetable.txt: строки 'страница кадр' или 'страница -'."""
    table = {}
    for n, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) != 2:
            raise ValueError(f"{path}:{n}: ожидалось 'страница кадр', получено {line!r}")
        page = int(parts[0])
        table[page] = None if parts[1] == "-" else int(parts[1])
    return table


def load_refs(path=HERE / "refs.txt"):
    """Читает строку обращений: логические адреса через пробел или перевод строки."""
    text = Path(path).read_text(encoding="utf-8")
    return [int(x) for line in text.splitlines()
            for x in line.split("#", 1)[0].split()]


def split(addr):
    """Логический адрес -> (номер страницы, смещение)."""
    if not 0 <= addr < ADDRESS_SPACE:
        raise BadAddress(f"адрес {addr} вне пространства 0..{ADDRESS_SPACE - 1}")
    return addr // PAGE_SIZE, addr % PAGE_SIZE


def translate(addr, table):
    """Логический адрес -> физический. Бросает PageFault или BadAddress."""
    page, offset = split(addr)
    frame = table.get(page)
    if frame is None:
        raise PageFault(f"страница {page} отсутствует (страничный отказ)")
    return frame * PAGE_SIZE + offset


def describe(addr, table):
    """Одна строка отчёта по адресу."""
    try:
        page, offset = split(addr)
    except BadAddress as e:
        return f"{addr:>6}  ошибка: {e}"
    try:
        phys = translate(addr, table)
    except PageFault as e:
        return f"{addr:>6}  стр {page:>2} смещ {offset:>4}  ->  {e}"
    frame = table[page]
    return (f"{addr:>6}  стр {page:>2} смещ {offset:>4}  ->  кадр {frame:>2}  "
            f"физ {frame} * {PAGE_SIZE} + {offset} = {phys}")


def main(argv):
    table = load_table()
    addrs = [int(a) for a in argv] if argv else load_refs()
    ok = faults = bad = 0
    print(f"Размер страницы {PAGE_SIZE} Б, страниц {PAGES}, обращений {len(addrs)}")
    for a in addrs:
        line = describe(a, table)
        print(line)
        if "ошибка" in line:
            bad += 1
        elif "отказ" in line:
            faults += 1
        else:
            ok += 1
    print(f"Итого: переведено {ok}, страничных отказов {faults}, неверных адресов {bad}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
