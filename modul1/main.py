#!/usr/bin/env python3
"""Запуск одного алгоритма на одном файле.

Автор: Эркинбеков Айман

Примеры:
  python3 main.py data/jobs.txt fcfs
  python3 main.py data/jobs.txt rr --q 2
  python3 main.py data/mixed.txt mlfq
  python3 main.py data/starve.txt aging --step 5
  python3 main.py data/jobs.txt all          # все пять основных алгоритмов
"""
import argparse
import sys

import scheduler as s


def show(res: s.Result) -> None:
    print(f"\n=== {res.name} ===")
    print(s.gantt_text(res))
    print()
    print(s.process_table(res))
    print(f"Переключений контекста: {res.switches}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Планировщик процессов (Проект 1, Модуль 1)")
    ap.add_argument("file", help="файл с процессами: PID arrival burst priority")
    ap.add_argument("algorithm", choices=list(s.ALGORITHMS) + ["all"], help="алгоритм")
    ap.add_argument("--q", type=int, default=2, help="квант для RR (по умолчанию 2)")
    ap.add_argument("--step", type=int, default=5, help="шаг старения для aging (по умолчанию 5)")
    ap.add_argument("--boost", type=int, default=50, help="период boost для MLFQ (0 = без boost)")
    args = ap.parse_args()

    try:
        procs = s.load(args.file)
        if args.q <= 0 or args.step <= 0 or args.boost < 0:
            raise ValueError("--q и --step должны быть > 0, --boost >= 0")
    except (OSError, ValueError) as e:
        print(f"Ошибка: {e}", file=sys.stderr)
        return 1

    if args.algorithm == "all":
        for res in (s.fcfs(procs), s.sjf(procs), s.rr(procs, args.q), s.srtf(procs), s.priority(procs)):
            show(res)
        return 0

    if args.algorithm == "rr":
        res = s.rr(procs, args.q)
    elif args.algorithm == "aging":
        res = s.priority_aging(procs, args.step)
    elif args.algorithm == "mlfq":
        res = s.mlfq(procs, boost=args.boost)
    else:
        res = s.ALGORITHMS[args.algorithm](procs)
    show(res)
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    sys.exit(main())
