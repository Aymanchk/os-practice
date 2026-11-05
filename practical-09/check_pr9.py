#!/usr/bin/env python3
"""Проверка ПР-9: first/best/worst fit, склейка дыр, buddy system, сравнение."""
import contextlib
import io
import random
import subprocess
import sys

from buddy import Buddy
from memsim import MEMORY, Block, MemoryManager, external_fragmentation, load, run

total = 0
failed = 0


def check(name, condition):
    global total, failed
    total += 1
    if condition:
        print(f"[ok]     {name}")
    else:
        failed += 1
        print(f"[ОШИБКА] {name}")


def cli(*args):
    res = subprocess.run([sys.executable, *args], capture_output=True, text=True, timeout=60)
    return res.returncode, res.stdout


def maps(text):
    """Из вывода run_ops1.py берёт только карты памяти (от первой "[" до конца, без пометки отказа)."""
    return [line[line.index("["):].replace("  ← ОТКАЗ", "") for line in text.splitlines() if "[" in line]


# ---------- независимые эталоны ----------

def holes_of(cells):
    """Дыры по побитовой карте памяти: список (начало, размер)."""
    result, i = [], 0
    while i < len(cells):
        if cells[i] is None:
            j = i
            while j < len(cells) and cells[j] is None:
                j += 1
            result.append((i, j - i))
            i = j
        else:
            i += 1
    return result


def oracle_alloc(cells, pid, size, strategy):
    found = [(start, length) for start, length in holes_of(cells) if length >= size]
    if not found:
        return False
    if strategy == "first":
        start = found[0][0]
    elif strategy == "best":
        start = min(found, key=lambda h: (h[1], h[0]))[0]
    else:
        start = max(found, key=lambda h: (h[1], -h[0]))[0]
    for i in range(start, start + size):
        cells[i] = pid
    return True


def oracle_free(cells, pid):
    for i, owner in enumerate(cells):
        if owner == pid:
            cells[i] = None


def cells_of(manager):
    """Побитовая карта памяти по блокам менеджера."""
    cells = [None] * MEMORY
    for b in manager.blocks:
        for i in range(b.start, b.start + b.size):
            cells[i] = b.pid
    return cells


def tiles(blocks):
    """Блоки (начало, размер) идут подряд без щелей и перекрытий и покрывают всю память."""
    pos = 0
    for start, size in blocks:
        if start != pos or size <= 0:
            return False
        pos += size
    return pos == MEMORY


def random_ops(rng, count, max_size=300):
    ops, alive, number = [], [], 0
    for _ in range(count):
        if alive and rng.random() < 0.42:
            ops.append(("free", alive.pop(rng.randrange(len(alive)))))
        else:
            number += 1
            alive.append(f"P{number}")
            ops.append(("alloc", f"P{number}", rng.randint(1, max_size)))
    return ops


# ---------- buddy-эталон ----------

def round_up(size):
    block = 1
    while block < size:
        block *= 2
    return block


def free_blocks_by_cells(cells, addr=0, size=MEMORY):
    """Максимальные свободные блоки, выровненные по размеру (то, что должен держать buddy)."""
    used = sum(1 for c in cells[addr:addr + size] if c is not None)
    if used == 0:
        return [(addr, size)]
    if size == 1:
        return []
    half = size // 2
    return free_blocks_by_cells(cells, addr, half) + free_blocks_by_cells(cells, addr + half, half)


def oracle_buddy_alloc(cells, pid, size):
    need = round_up(size)
    if need > MEMORY:
        return False
    found = [(blk, addr) for addr, blk in free_blocks_by_cells(cells) if blk >= need]
    if not found:
        return False
    blk, addr = min(found)           # самый маленький блок, из равных самый левый
    for i in range(addr, addr + need):
        cells[i] = pid
    return True


def buddy_cells(buddy):
    cells = [None] * MEMORY
    for addr, size, pid in buddy.blocks():
        for i in range(addr, addr + size):
            cells[i] = pid
    return cells


# ======================================================================
print("== Слайд 9.1 и 9.2: first fit на ops1 ==")
EXPECTED_FIRST = """\
 1 alloc P1   200  [P1:200] [-:824]
 2 alloc P2   300  [P1:200] [P2:300] [-:524]
 3 alloc P3   150  [P1:200] [P2:300] [P3:150] [-:374]
 4 alloc P4   250  [P1:200] [P2:300] [P3:150] [P4:250] [-:124]
 5 free  P2        [P1:200] [-:300] [P3:150] [P4:250] [-:124]
 6 free  P4        [P1:200] [-:300] [P3:150] [-:250] [-:124]
 7 alloc P5   120  [P1:200] [P5:120] [-:180] [P3:150] [-:250] [-:124]
 8 alloc P6   280  [P1:200] [P5:120] [-:180] [P3:150] [-:250] [-:124]  ← ОТКАЗ
 9 free  P1        [-:200] [P5:120] [-:180] [P3:150] [-:250] [-:124]
10 alloc P7   400  [-:200] [P5:120] [-:180] [P3:150] [-:250] [-:124]  ← ОТКАЗ
11 free  P3        [-:200] [P5:120] [-:180] [-:150] [-:250] [-:124]
12 alloc P8   350  [-:200] [P5:120] [-:180] [-:150] [-:250] [-:124]  ← ОТКАЗ
свободно=904 макс. дыра=250 дыр=5 отказов=3
"""
code, text = cli("run_ops1.py", "first")
check("run_ops1.py first выводит ровно то, что на слайде", code == 0 and text == EXPECTED_FIRST)
code, text = cli("run_ops1.py")
check("run_ops1.py без аргументов работает как first", text == EXPECTED_FIRST)
with contextlib.redirect_stdout(io.StringIO()) as captured:
    mm = run(load("ops1.txt"), "first", verbose=True)
check("run(load(...), 'first', verbose=True) печатает то же и возвращает менеджер",
      captured.getvalue() + "свободно=904 макс. дыра=250 дыр=5 отказов=3\n" == EXPECTED_FIRST
      and mm.stats() == (904, 250, 5) and mm.refused == 3)

print("== Слайд 9.3: best fit и worst fit ==")
code, text = cli("run_ops1.py", "best")
m = maps(text)
check("best fit, операция 7: P5 (120) в дыру 124, остаток 4",
      m[6] == "[P1:200] [-:300] [P3:150] [-:250] [P5:120] [-:4]")
check("best fit, операция 8: проходит, дыра 300 осталась целой",
      m[7] == "[P1:200] [P6:280] [-:20] [P3:150] [-:250] [P5:120] [-:4]" and "ОТКАЗ" not in text.splitlines()[7])
check("best fit: итог свободно=624 макс. дыра=250 дыр=5 отказов=2",
      text.splitlines()[-1] == "свободно=624 макс. дыра=250 дыр=5 отказов=2")
code, text = cli("run_ops1.py", "worst")
check("worst fit на ops1 даёт ту же карту, что first fit (операция 8 отказ)", text == EXPECTED_FIRST)

print("== Слайд 9.5: склейка дыр ==")
with contextlib.redirect_stdout(io.StringIO()) as captured:
    mm = run(load("ops1.txt"), "first", coalesce=True, verbose=True)
m = maps(captured.getvalue())
check("first + coalesce, операция 6: дыры 250 и 124 слились в 374",
      m[5] == "[P1:200] [-:300] [P3:150] [-:374]")
check("first + coalesce, операция 7",
      m[6] == "[P1:200] [P5:120] [-:180] [P3:150] [-:374]")
check("first + coalesce, операция 8 проходит: P6 280, остаток 94",
      m[7] == "[P1:200] [P5:120] [-:180] [P3:150] [P6:280] [-:94]")
check("first + coalesce: в конце 3 дыры вместо 5 и 2 отказа вместо 3",
      mm.stats() == (624, 330, 3) and mm.refused == 2)
for strategy in ("first", "worst"):
    off = run(load("ops1.txt"), strategy, coalesce=False)
    on = run(load("ops1.txt"), strategy, coalesce=True)
    check(f"{strategy}: склейка спасает операцию 8 (отказов {off.refused} -> {on.refused})",
          on.refused == off.refused - 1)
off = run(load("ops1.txt"), "best", coalesce=False)
on = run(load("ops1.txt"), "best", coalesce=True)
check("best: отказов столько же, меняется только число дыр",
      on.refused == off.refused and on.stats()[2] != off.stats()[2])

print("== Выбор дыры ==")
choice_best = MemoryManager("best")
choice_best.blocks = [Block(0, 100), Block(100, 100, "X"), Block(200, 100), Block(300, 100, "Y"),
                      Block(400, 624)]
check("best fit: из двух равных дыр берёт левую", choice_best.choose(100).start == 0)
choice_worst = MemoryManager("worst")
choice_worst.blocks = [Block(0, 100), Block(100, 100, "X"), Block(200, 100), Block(300, 724, "Y")]
check("worst fit: из двух равных дыр берёт левую", choice_worst.choose(10).start == 0)
check("запрос больше всей памяти отклоняется", not MemoryManager("first").alloc("P1", MEMORY + 1))
fresh = MemoryManager("first")
fresh.alloc("P1", MEMORY)
check("запрос на всю память влезает, а следующий отклоняется",
      fresh.show() == "[P1:1024]" and not fresh.alloc("P2", 1) and fresh.refused == 1)
before = fresh.show()
fresh.alloc("P3", 5)
check("отказ не меняет карту памяти", fresh.show() == before)
check("free несуществующего процесса ничего не ломает", MemoryManager("first").free("P99") is False)
try:
    MemoryManager("random")
    unknown_rejected = False
except ValueError:
    unknown_rejected = True
check("MemoryManager не принимает неизвестную стратегию", unknown_rejected)

print("== Случайные прогоны first/best/worst против побитового эталона (склейка включена) ==")
for strategy in ("first", "best", "worst"):
    rng = random.Random(strategy)
    good = True
    for _ in range(150):
        manager = MemoryManager(strategy, coalesce=True)
        cells = [None] * MEMORY
        for op in random_ops(rng, 80):
            if op[0] == "alloc":
                mine = manager.alloc(op[1], op[2])
                theirs = oracle_alloc(cells, op[1], op[2], strategy)
            else:
                manager.free(op[1])
                oracle_free(cells, op[1])
                mine = theirs = True
            if mine != theirs or cells_of(manager) != cells:
                good = False
                break
        if not good:
            break
    check(f"{strategy}: 150 случайных прогонов по 80 операций совпали с эталоном", good)

print("== Инварианты без склейки ==")
rng = random.Random(7)
good_tiles = good_owner = good_adjacent = True
for strategy in ("first", "best", "worst"):
    for _ in range(100):
        manager = MemoryManager(strategy, coalesce=False)
        live = {}
        for op in random_ops(rng, 80):
            if op[0] == "alloc":
                if manager.alloc(op[1], op[2]):
                    live[op[1]] = op[2]
            else:
                manager.free(op[1])
                live.pop(op[1], None)
            if not tiles([(b.start, b.size) for b in manager.blocks]):
                good_tiles = False
            used = {b.pid: b.size for b in manager.blocks if not b.free}
            if used != live:
                good_owner = False
        manager.merge()
        if any(a.free and b.free for a, b in zip(manager.blocks, manager.blocks[1:])):
            good_adjacent = False
check("блоки всегда идут подряд и покрывают память без щелей", good_tiles)
check("занятые блоки совпадают с тем, что выдано и не освобождено", good_owner)
check("после merge() двух свободных дыр подряд нет", good_adjacent)
manager = MemoryManager("first", coalesce=False)
for pid in ("P1", "P2", "P3"):
    manager.alloc(pid, 100)
for pid in ("P1", "P2", "P3"):
    manager.free(pid)
check("без склейки после освобождения всего остаются 4 дыры", len(manager.blocks) == 4)
manager.merge()
check("merge() превращает их в одну дыру на всю память", manager.show() == "[-:1024]")
manager = MemoryManager("first", coalesce=True)
for pid in ("P1", "P2", "P3"):
    manager.alloc(pid, 100)
for pid in ("P1", "P2", "P3"):
    manager.free(pid)
check("со склейкой после освобождения всего одна дыра [-:1024]", manager.show() == "[-:1024]")

print("== Метрики ==")
check("внешняя фрагментация: свободно 904, макс. дыра 250 -> 0.72",
      abs(external_fragmentation(904, 250) - 0.7234) < 0.001)
check("внешняя фрагментация: одна дыра -> 0, нет свободной памяти -> 0",
      external_fragmentation(100, 100) == 0 and external_fragmentation(0, 0) == 0)
check("пустая память: stats() = (1024, 1024, 1), отказов 0",
      MemoryManager("first").stats() == (1024, 1024, 1) and MemoryManager("first").refused == 0)

print("== Слайд 9.6: buddy system ==")
b = Buddy(log=True)
with contextlib.redirect_stdout(io.StringIO()) as captured:
    b.alloc("P1", 200)
check("alloc P1 200: печатает деление 512+512 и 256+256",
      captured.getvalue().splitlines() == ["   делим → 512+512", "   делим → 256+256"])
check("alloc P1 200: свободные блоки {256: [256], 512: [512]}",
      {s: l for s, l in b.free.items() if l} == {256: [256], 512: [512]})
check("alloc P1 200: блок 256 по адресу 0, внутренняя фрагментация 56",
      b.owned["P1"] == (0, 256, 200) and b.stats()[2] == 56)
check("запрос 1025 отклоняется, 1024 принимается",
      not Buddy().alloc("P1", 1025) and Buddy().alloc("P1", 1024))
code, text = cli("run_ops1.py", "buddy")
lines = text.splitlines()
check("buddy на ops1: P1 (200) занял блок 256", maps(text)[0] == "[P1:256] [-:256] [-:512]")
check("buddy на ops1: после free P3 блоки 256 и 256 склеились в 512",
      maps(text)[10].startswith("[-:512] [P5:128]"))
check("buddy на ops1: итог свободно=384 макс. дыра=256 дыр=2 отказов=3 внутр. потери=170",
      lines[-1] == "свободно=384 макс. дыра=256 дыр=2 отказов=3 внутр. потери=170")
rng = random.Random(99)
good_oracle = good_shape = good_back = True
for _ in range(100):
    buddy = Buddy()
    cells = [None] * MEMORY
    for op in random_ops(rng, 80, max_size=400):
        if op[0] == "alloc":
            mine = buddy.alloc(op[1], op[2])
            theirs = oracle_buddy_alloc(cells, op[1], op[2])
        else:
            buddy.release(op[1])
            oracle_free(cells, op[1])
            mine = theirs = True
        if mine != theirs or buddy_cells(buddy) != cells:
            good_oracle = False
        blocks = buddy.blocks()
        if not tiles([(a, s) for a, s, _ in blocks]):
            good_shape = False
        for addr, size_b, pid_b in blocks:
            if size_b & (size_b - 1) or addr % size_b:
                good_shape = False
            friend = addr ^ size_b
            if pid_b is None and size_b < MEMORY and any(
                    a == friend and s == size_b and p is None for a, s, p in blocks):
                good_shape = False
    for pid in {p for _, _, p in buddy.blocks() if p}:
        buddy.release(pid)
    if buddy.show() != "[-:1024]":
        good_back = False
check("buddy: 100 случайных прогонов совпали с независимым эталоном", good_oracle)
check("buddy: размеры степени двойки, выравнивание, свободные друзья всегда склеены", good_shape)
check("buddy: после освобождения всего снова один блок [-:1024]", good_back)
check("release процесса, которого нет, ничего не ломает", Buddy().release("P99") is False)

print("== Файлы и слайд 9.8: сравнение на ops2 ==")
ops = load("ops1.txt")
check("ops1.txt: 12 операций, 8 alloc и 4 free",
      len(ops) == 12 and sum(1 for o in ops if o[0] == "alloc") == 8)
ops2 = load("ops2.txt")
check("ops2.txt: 200 операций, 113 alloc и 87 free",
      len(ops2) == 200 and sum(1 for o in ops2 if o[0] == "alloc") == 113)
EXPECTED_TABLE = """\
подход           отказов  внешняя фр.  внутренняя
first +merge          33         0.47           0
best +merge           32         0.36           0
worst +merge          38         0.52           0
buddy                 38         0.36         175
"""
code, text = cli("compare.py")
check("compare.py: таблица совпадает с ожидаемой на слайде (33/0.47, 32/0.36, 38/0.52, 38/0.36/175)",
      code == 0 and text.startswith(EXPECTED_TABLE))
code, text = cli("ops1_table.py")
rows = {line.split(" | ")[0].strip("| "): line.split(" | ")[1] for line in text.splitlines()
        if line.startswith("| ") and "---" not in line and "Вариант" not in line}
check("ops1_table.py: отказы как на слайде (first 8,10,12; best 10,12; worst 8,10,12)",
      rows.get("first fit") == "8, 10, 12" and rows.get("best fit") == "10, 12"
      and rows.get("worst fit") == "8, 10, 12")
check("ops1_table.py: любая стратегия со слиянием 10,12; buddy 4,8,10",
      all(rows.get(f"{s} fit + слияние") == "10, 12" for s in ("first", "best", "worst"))
      and rows.get("buddy") == "4, 8, 10")
check("ops1_table.py: buddy после трёх выделений теряет внутри блоков 374 из 1024", "374 из 1024" in text)
code, text = cli("plot.py", "ops2.txt", "/tmp/fragmentation_check.svg")
with open("/tmp/fragmentation_check.svg", encoding="utf-8") as f:
    svg = f.read()
check("plot.py: SVG-график с четырьмя линиями по 200 точек",
      code == 0 and svg.count("<polyline") == 4
      and all(len(part.split('points="')[1].split('"')[0].split()) == 200
              for part in svg.split("<polyline")[1:]))
code, text = cli("compare.py", "no_such_file.txt")
check("compare.py с несуществующим файлом: код 2 и понятное сообщение",
      code == 2 and text.startswith("Ошибка:"))
with open("/tmp/bad_ops_pr9.txt", "w", encoding="utf-8") as f:
    f.write("alloc P1 100\nalloc P2 -5\n")
code, text = cli("run_ops1.py", "first", "--file", "/tmp/bad_ops_pr9.txt")
check("run_ops1.py с отрицательным размером: код 2 и номер строки", code == 2 and ":2:" in text)
with open("/tmp/bad_ops_pr9.txt", "w", encoding="utf-8") as f:
    f.write("# комментарий\n\nalloc P1 100  # хвост\nfoo P1\n")
code, text = cli("run_ops1.py", "first", "--file", "/tmp/bad_ops_pr9.txt")
check("run_ops1.py с неизвестной командой: код 2 и номер строки", code == 2 and ":4:" in text)
code, text = cli("run_ops1.py", "first")
check("повторный запуск даёт тот же вывод (детерминированность)", text == EXPECTED_FIRST)

print()
print(f"Проверок: {total}, провалено: {failed}")
sys.exit(1 if failed else 0)
