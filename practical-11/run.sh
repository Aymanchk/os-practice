#!/usr/bin/env bash
# ПР-11: алгоритмы замещения страниц, график, аномалия Белади, сравнение и проверка одной командой.
set -uo pipefail
cd "$(dirname "$0")" || exit 1

echo "== Контрольная строка, 3 и 4 кадра";           python3 replace.py
echo; echo "== Пошагово, 3 кадра";                  python3 replace.py -f 3 -v
echo; echo "== Кадры 1..8 и график faults.png";     python3 plot_faults.py
echo; echo "== Аномалия Белади";                    python3 belady.py
echo; echo "== Случайная строка и строка с локальностью"; python3 compare.py
echo; echo "== Общая проверка";                     python3 check_pr11.py
