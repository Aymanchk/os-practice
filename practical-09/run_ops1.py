#!/usr/bin/env python3
"""Прогон файла операций с картой памяти после каждой операции.

Примеры:
    python3 run_ops1.py first
    python3 run_ops1.py best
    python3 run_ops1.py first --coalesce
    python3 run_ops1.py buddy --log
"""
import argparse
import sys

from memsim import STRATEGIES, load, run


def main():
    parser = argparse.ArgumentParser(description="Карта памяти после каждой операции")
    parser.add_argument("strategy", nargs="?", default="first", choices=STRATEGIES + ("buddy",))
    parser.add_argument("--file", default="ops1.txt", help="файл операций (по умолчанию ops1.txt)")
    parser.add_argument("--coalesce", action="store_true",
                        help="склеивать соседние дыры при free")
    parser.add_argument("--log", action="store_true",
                        help="для buddy: печатать деление и слияние блоков")
    args = parser.parse_args()

    try:
        ops = load(args.file)
    except (OSError, ValueError) as error:
        print(f"Ошибка: {error}")
        return 2

    if args.strategy == "buddy":
        from buddy import run_buddy       # подключаем только когда он нужен
        mm = run_buddy(ops, verbose=True, log=args.log)
        total, largest, internal = mm.stats()
        holes = sum(len(lst) for lst in mm.free.values())
        print(f"свободно={total} макс. дыра={largest} дыр={holes} отказов={mm.refused} "
              f"внутр. потери={internal}")
    else:
        mm = run(ops, args.strategy, coalesce=args.coalesce, verbose=True)
        total, largest, holes = mm.stats()
        print(f"свободно={total} макс. дыра={largest} дыр={holes} отказов={mm.refused}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
