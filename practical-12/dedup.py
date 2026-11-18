#!/usr/bin/env python3
"""ПР-12: поиск файлов-дубликатов по содержимому и замена их жёсткими ссылками.

    ./dedup.py КАТАЛОГ            найти и заменить
    ./dedup.py -n КАТАЛОГ         только показать (dry run)

Сначала файлы группируются по размеру (файлы разного размера не могут совпасть),
и хэш SHA-256 считается только внутри групп. Файлы, которые уже являются одним
inode (жёсткие ссылки друг на друга), повторно не считаются. Замена атомарная:
ссылка создаётся под временным именем и переименовывается поверх дубликата,
поэтому при сбое файл не пропадёт.
"""
import argparse
import hashlib
import os
import sys
from collections import defaultdict


def sha256(path, chunk=1 << 16):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while block := f.read(chunk):
            h.update(block)
    return h.hexdigest()


def find_duplicates(root):
    """Возвращает список групп: [оригинал, дубликат, ...] с одинаковым содержимым
    и разными inode. Оригинал - первый по имени."""
    by_size = defaultdict(list)
    seen_inodes = set()
    for dirpath, _dirs, files in os.walk(root):
        for name in files:
            path = os.path.join(dirpath, name)
            st = os.lstat(path)
            if not os.path.isfile(path) or os.path.islink(path):
                continue
            key = (st.st_dev, st.st_ino)
            if key in seen_inodes:          # уже жёсткая ссылка на учтённый файл
                continue
            seen_inodes.add(key)
            by_size[st.st_size].append(path)
    groups = []
    for size, paths in by_size.items():
        if len(paths) < 2 or size == 0:
            continue
        by_hash = defaultdict(list)
        for p in paths:
            by_hash[sha256(p)].append(p)
        groups.extend(sorted(g) for g in by_hash.values() if len(g) > 1)
    return sorted(groups)


def link_over(original, duplicate):
    """Атомарно заменить duplicate жёсткой ссылкой на original."""
    if os.stat(original).st_dev != os.stat(duplicate).st_dev:
        raise OSError(f"{duplicate}: другая файловая система, жёсткая ссылка невозможна")
    tmp = duplicate + ".dedup-tmp"
    os.link(original, tmp)
    os.replace(tmp, duplicate)


def main(argv):
    p = argparse.ArgumentParser(description="Дубликаты по содержимому -> жёсткие ссылки")
    p.add_argument("root")
    p.add_argument("-n", "--dry-run", action="store_true", help="только показать")
    args = p.parse_args(argv)
    if not os.path.isdir(args.root):
        p.error(f"нет каталога {args.root}")

    groups = find_duplicates(args.root)
    saved = 0
    for group in groups:
        original, dups = group[0], group[1:]
        size = os.path.getsize(original)
        print(f"{size:>9} Б  {os.path.relpath(original, args.root)}")
        for d in dups:
            print(f"{'':>11}  = {os.path.relpath(d, args.root)}")
            if not args.dry_run:
                link_over(original, d)
            saved += size
    verb = "можно сэкономить" if args.dry_run else "сэкономлено"
    print(f"групп дубликатов: {len(groups)}, лишних копий: {sum(len(g) - 1 for g in groups)}, "
          f"{verb}: {saved} Б ({saved / 1024:.1f} КБ)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
