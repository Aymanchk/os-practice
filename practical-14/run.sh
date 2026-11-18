#!/usr/bin/env bash
# ПР-14: буферизация, системные вызовы, страничный кэш, O_DIRECT, опрос и проверка одной командой.
# Нужен Linux с gcc, make и strace; части с кэшем и O_DIRECT нужен root.
set -uo pipefail
cd "$(dirname "$0")" || exit 1

echo "== Три способа записи и strace -c";   ./syscalls.sh
echo; echo "== Опрос против блокирующего чтения"; ./poll_demo.py
echo
if [[ $EUID -eq 0 ]]; then
    echo "== Страничный кэш: холодное и горячее чтение"; ./cache_demo.sh
    echo; echo "== Обычная запись и O_DIRECT";          ./direct_demo.sh
else
    echo "== cache_demo.sh и direct_demo.sh пропущены: нужен root"
fi
echo; echo "== Общая проверка";                   ./check_pr14.py
make -s clean
