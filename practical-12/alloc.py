#!/usr/bin/env python3
"""ПР-12, вариант B: модель диска из блоков и три способа размещения файла.

Диск из 512 блоков. Один и тот же поток операций (создание файлов случайного
размера и удаление случайных файлов, seed 12) прогоняется для трёх способов:

  непрерывный  файл занимает подряд идущие блоки, в каталоге (начало, длина);
  связанный    блоки где угодно, в каждом блоке указатель на следующий;
  индексный    блоки где угодно, номера блоков в отдельном индексном блоке.

Сравниваются: сколько созданий не удалось при достаточном общем свободном месте
(внешняя фрагментация), сколько блоков уходит на служебные данные, сколько чтений
с диска нужно, чтобы прочитать k-й блок файла (произвольный доступ), и на сколько
кусков разбит файл (сколько раз головке HDD придётся перескакивать).
"""
import random
import sys

DISK = 512
OPS = 400
SEED = 12
MAX_FILE = 30
PTRS_PER_INDEX = 128     # блок 512 Б / номер блока 4 Б


class Disk:
    def __init__(self):
        self.free = [True] * DISK

    def free_count(self):
        return sum(self.free)

    def take(self, blocks):
        for b in blocks:
            assert self.free[b]
            self.free[b] = False

    def release(self, blocks):
        for b in blocks:
            self.free[b] = True

    def runs(self):
        """Свободные участки подряд: список (начало, длина)."""
        out, start = [], None
        for i, f in enumerate(self.free + [False]):
            if f and start is None:
                start = i
            elif not f and start is not None:
                out.append((start, i - start))
                start = None
        return out


class Contiguous:
    name = "непрерывный"

    def __init__(self):
        self.disk, self.files = Disk(), {}

    def create(self, fid, size):
        for start, length in self.disk.runs():          # first fit
            if length >= size:
                blocks = list(range(start, start + size))
                self.disk.take(blocks)
                self.files[fid] = blocks
                return True
        return False

    def reads_for(self, fid, k):
        return 1                                       # адрес = начало + k

    def meta_blocks(self, fid):
        return 0                                       # (начало, длина) лежат в каталоге


class Linked:
    name = "связанный"

    def __init__(self):
        self.disk, self.files = Disk(), {}

    def create(self, fid, size):
        free = [i for i, f in enumerate(self.disk.free) if f]
        if len(free) < size:
            return False
        blocks = free[:size]
        self.disk.take(blocks)
        self.files[fid] = blocks
        return True

    def reads_for(self, fid, k):
        return k + 1                                   # пройти цепочку от первого блока

    def meta_blocks(self, fid):
        return 0                                       # указатель внутри блока данных


class Indexed:
    name = "индексный"

    def __init__(self):
        self.disk, self.files, self.index = Disk(), {}, {}

    def create(self, fid, size):
        need = size + -(-size // PTRS_PER_INDEX)          # данные + индексные блоки
        free = [i for i, f in enumerate(self.disk.free) if f]
        if len(free) < need:
            return False
        idx, data = free[:need - size], free[need - size:need]
        self.disk.take(idx + data)
        self.index[fid], self.files[fid] = idx, data
        return True

    def reads_for(self, fid, k):
        return 2                                       # индексный блок + блок данных

    def meta_blocks(self, fid):
        return len(self.index[fid])


def delete(method, fid):
    method.disk.release(method.files.pop(fid))
    if isinstance(method, Indexed):
        method.disk.release(method.index.pop(fid))


def workload():
    """Поток операций: ('create', id, размер) или ('delete', id)."""
    rng = random.Random(SEED)
    ops, alive, nid = [], [], 0
    for _ in range(OPS):
        if alive and rng.random() < 0.5:
            fid = alive.pop(rng.randrange(len(alive)))
            ops.append(("delete", fid))
        else:
            ops.append(("create", nid, rng.randint(1, MAX_FILE)))
            alive.append(nid)
            nid += 1
    return ops


def fragments(blocks):
    return 1 + sum(1 for a, b in zip(blocks, blocks[1:]) if b != a + 1)


def run(cls, ops):
    m = cls()
    created = failed = failed_with_space = 0
    for op in ops:
        if op[0] == "create":
            _, fid, size = op
            if m.create(fid, size):
                created += 1
            else:
                failed += 1
                if m.disk.free_count() >= size:
                    failed_with_space += 1
        elif op[1] in m.files:
            delete(m, op[1])
    files = m.files
    data = sum(len(b) for b in files.values())
    meta = sum(m.meta_blocks(f) for f in files)
    reads = [m.reads_for(f, k) for f, b in files.items() for k in range(len(b))]
    frag = [fragments(b) for b in files.values()]
    runs = m.disk.runs()
    return {
        "created": created, "failed": failed, "failed_with_space": failed_with_space,
        "files": len(files), "data": data, "meta": meta, "free": m.disk.free_count(),
        "largest_hole": max((l for _, l in runs), default=0), "holes": len(runs),
        "avg_reads": sum(reads) / len(reads), "max_reads": max(reads),
        "avg_frag": sum(frag) / len(frag),
    }


def main():
    ops = workload()
    n_create = sum(1 for o in ops if o[0] == "create")
    print(f"Диск {DISK} блоков, {len(ops)} операций ({n_create} созданий, "
          f"{len(ops) - n_create} удалений), размер файла 1..{MAX_FILE} блоков, seed {SEED}")
    results = {cls.name: run(cls, ops) for cls in (Contiguous, Linked, Indexed)}
    rows = [
        ("создано файлов", "created", "{}"),
        ("не удалось создать", "failed", "{}"),
        ("  из них при достаточном свободном месте", "failed_with_space", "{}"),
        ("файлов на диске в конце", "files", "{}"),
        ("блоков данных", "data", "{}"),
        ("служебных блоков", "meta", "{}"),
        ("свободно блоков", "free", "{}"),
        ("свободных участков (дыр)", "holes", "{}"),
        ("самая большая дыра", "largest_hole", "{}"),
        ("чтений для k-го блока, среднее", "avg_reads", "{:.2f}"),
        ("чтений для k-го блока, худшее", "max_reads", "{}"),
        ("кусков на файл, среднее", "avg_frag", "{:.2f}"),
    ]
    names = list(results)
    print(f"{'':42}" + "".join(f"{n:>13}" for n in names))
    for title, key, fmt in rows:
        print(f"{title:42}" + "".join(f"{fmt.format(results[n][key]):>13}" for n in names))
    return 0


if __name__ == "__main__":
    sys.exit(main())
