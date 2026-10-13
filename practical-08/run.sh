#!/usr/bin/env bash
# ПР-8: банкир, детектор, TrackedLock, философы и общая проверка одной командой.
set -uo pipefail
cd "$(dirname "$0")" || exit 1

echo "== Банкир: bank1 и запросы";  ./banker.py bank1.txt --all -r < requests1.txt
echo; echo "== Банкир: bank2";       ./banker.py bank2.txt

echo; echo "== Детектор по журналу (код 1 = найдена взаимоблокировка)"
./deadlock_detector.py events_deadlock.log; echo "код возврата: $?"
echo
./deadlock_detector.py events_ok.log; echo "код возврата: $?"

echo; echo "== deadlock.py зависает: timeout убьёт его через 5 с (код 124)"
timeout 5 ./deadlock.py; echo "код возврата: $?"

echo; echo "== deadlock.py --dump 2: где ждёт каждый поток"
./deadlock.py --dump 2

echo; echo "== deadlock.py на TrackedLock"
./deadlock.py --tracked

echo; echo "== Обедающие философы, по 3 с на режим"
./philosophers.py all 3

echo; echo "== Общая проверка"
./check_pr8.py
