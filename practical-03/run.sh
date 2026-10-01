#!/usr/bin/env bash
# ПР-3: все демонстрации процессов одной командой.
set -euo pipefail
cd "$(dirname "$0")" || exit 1

echo "== Дерево процессов (первые 15 строк)"
./ptree.py | head -15 || true

echo; echo "== fork + exec + wait"
./runner.py 3 sleep 1
echo
./runner.py 2 no_such_command || echo "код возврата: $? (exec не нашёл команду)"

echo; echo "== Зомби";  ./zombie_demo.py
echo; echo "== Сирота"; ./orphan_demo.py
echo; echo "== Copy-on-Write"; ./cow_demo.py

echo; echo "== Проверка: не осталось зомби и процессов демонстраций"
# pgrep -r Z ищет процессы в состоянии Z (зомби), pgrep -f - оставшиеся демо.
if pgrep -a -r Z || pgrep -a -f '_demo\.py|runner\.py'; then
    echo "Остались процессы!"; exit 1
fi
echo "Процессы демонстраций не найдены"
