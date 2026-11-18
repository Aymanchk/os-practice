#!/usr/bin/env bash
# ПР-15: образ, лимиты, изоляция, контейнер против ВМ и проверка одной командой.
# Запускается на хосте с Docker. Шаг с ВМ (vm_vs_container.sh) рассчитан на
# macOS + Docker Desktop и перезапускает его; здесь он вызывается с --no-vm.
set -uo pipefail
cd "$(dirname "$0")" || exit 1

echo "== Сборка образа";   docker build -q -t pr15-calc app
docker rm -f calc >/dev/null 2>&1
echo "== Запуск и запросы"; docker run -d --rm --name calc -p 8000:8000 pr15-calc >/dev/null; sleep 1.5
./client.py "2 + 2 * 2" "10 / 4" "2 ** 10" "1 / 0" "__import__('os')"
echo "  пользователь в контейнере: $(docker exec calc id)"
docker rm -f calc >/dev/null
echo; echo "== Лимиты";            ./limits.sh
echo; echo "== Изоляция";          ./isolation.sh
echo; echo "== Контейнер и ВМ";    ./vm_vs_container.sh --no-vm
echo; echo "== Общая проверка";    ./check_pr15.py
