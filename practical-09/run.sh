#!/usr/bin/env bash
# ПР-9: стратегии размещения, склейка, buddy, сравнение, проверка и уровень C одной командой.
# Для уровня C нужны gcc и make; valgrind необязателен (без него шаг пропускается).
set -uo pipefail
cd "$(dirname "$0")" || exit 1

for s in first best worst; do
    echo "== ops1, $s fit";            python3 run_ops1.py "$s"; echo
done
echo "== ops1, first fit со склейкой"; python3 run_ops1.py first --coalesce; echo
echo "== ops1, buddy system";         python3 run_ops1.py buddy; echo
echo "== Где отказы на ops1";         python3 ops1_table.py; echo
echo "== Сравнение на ops2";          python3 compare.py; echo
echo "== График fragmentation.svg";   python3 plot.py; echo
echo "== Проверка Python-части";      python3 check_pr9.py; echo

echo "== Уровень C: сборка и тесты"
make -s -C c all && make -s -C c test
if command -v valgrind >/dev/null 2>&1; then
    echo; echo "== Уровень C: valgrind"; make -s -C c valgrind
else
    echo; echo "== valgrind не установлен, шаг пропущен (sudo apt install valgrind)"
fi
echo; echo "== Уровень C: сравнение с glibc malloc"; ./c/bench.sh
make -s -C c clean
