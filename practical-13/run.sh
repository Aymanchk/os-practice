#!/usr/bin/env bash
# ПР-13: планирование диска, сравнение, голодание и справедливость, проверка одной командой.
set -uo pipefail
cd "$(dirname "$0")" || exit 1

echo "== Контрольный набор";                          python3 disk.py -v
echo; echo "== Случайные наборы и график movement.png"; python3 compare.py
echo; echo "== Голодание и справедливость";            python3 dynamic.py
echo; echo "== Общая проверка";                        python3 check_pr13.py
