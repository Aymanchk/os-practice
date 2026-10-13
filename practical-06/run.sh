#!/usr/bin/env bash
# ПР-6: производитель-потребитель, барьер и ошибка if/while одной командой.
set -uo pipefail
cd "$(dirname "$0")" || exit 1

echo "== (а) семафоры и мьютекс";        ./producer_consumer.py sem
echo; echo "== (б) мьютекс и условная переменная"; ./producer_consumer.py cond

echo; echo "== Повторные запуски"
for mode in sem cond; do
    fails=0
    for _ in $(seq 20); do ./producer_consumer.py "$mode" > /dev/null || fails=$((fails + 1)); done
    echo "$mode: запусков 20, сбоев $fails"
done

echo; echo "== Барьер (4 потока, 3 фазы)"; ./barrier_demo.py

echo; echo "== wait под if (ошибка, код 1 ожидаем)"
./wakeup_broken.py; echo "код возврата: $?"
echo; echo "== wait под while (исправлено)"
./wakeup_fixed.py; echo "код возврата: $?"
