#!/usr/bin/env bash
# ПР-10: трансляция адресов, TLB, график и двухуровневая таблица одной командой.
set -uo pipefail
cd "$(dirname "$0")" || exit 1

echo "== Трансляция refs.txt";                ./translate.py
echo; echo "== TLB на 4 записи, по шагам";    ./tlb.py -v
echo; echo "== Длинная строка с локальностью"; ./gen_refs.py
echo; echo "== Размер TLB -> доля попаданий";  ./tlb_plot.py
echo; echo "== Двухуровневая таблица";         ./twolevel.py
echo; echo "== Общая проверка";                ./check_pr10.py
