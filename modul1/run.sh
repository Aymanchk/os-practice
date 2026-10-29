#!/usr/bin/env bash
# Модуль 1, Проект 1: планировщик учебного сервера.
# Все блоки (A, B, C) одной командой. Вывод сохраняется в evidence/.
# Автор: Эркинбеков Айман
set -euo pipefail
cd "$(dirname "$0")" || exit 1
mkdir -p evidence results

{
  python3 --version
  uname -m
  if [ -r /etc/os-release ]; then . /etc/os-release && echo "$PRETTY_NAME"; else uname -s; fi
} > evidence/environment.txt

echo "== Самопроверка: set1.txt против эталона ПР-5"
python3 selfcheck.py | tee evidence/selfcheck.txt

echo; echo "== jobs.txt: все пять алгоритмов"
python3 main.py data/jobs.txt all | tee evidence/jobs_all.txt

echo; echo "== Отчёт по блокам A, B, C"
python3 report.py | tee evidence/report.txt

echo; echo "Готово. Вывод команд: evidence/, отчёт и диаграммы Ганта: results/"
