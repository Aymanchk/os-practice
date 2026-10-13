#!/usr/bin/env bash
# ПР-5: все проверки и сравнения одной командой.
set -euo pipefail
cd "$(dirname "$0")" || exit 1

echo "== Наборы данных (из методички)"
./gen_sets.py

echo; echo "== Сверка с эталоном на set1"
./check_set1.py

echo; echo "== Диаграммы Ганта на set1"
./sched.py --algo srtf --gantt set1.txt
echo
./sched.py --algo rr --quantum 3 --gantt set1.txt

echo; echo "== Сравнение алгоритмов на set1, set2, set3"
./compare.py

echo; echo "== RR: зависимость от кванта на set2"
mkdir -p out
./rr_quantum.py set2.txt out/rr_quantum.png

echo; echo "== Старение: starve.txt без старения и со старением каждые 5 тактов"
echo "Без старения:"
./sched.py --algo priority starve.txt | grep -E '^(PID|LOW|H30) |Среднее ожидание'
echo
echo "Со старением:"
./sched.py --algo priority --aging 5 starve.txt | grep -E '^(PID|LOW|H30) |Среднее ожидание'
