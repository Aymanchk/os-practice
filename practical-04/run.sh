#!/usr/bin/env bash
# ПР-4: данные, замеры CPU и сети, память потоков и процессов одной командой.
set -euo pipefail
cd "$(dirname "$0")" || exit 1

echo "== Данные"
./generate_data.py
echo "Логических ядер (nproc): $(nproc)"

echo; echo "== Вычислительная задача"
./cpu_benchmark.py numbers.txt

echo; echo "== Общая и раздельная память"
./memory_demo.py

echo; echo "== Сетевая задача (локальный сервер с задержкой 0,1 с)"
./slow_server.py & server=$!
trap 'kill "$server" 2>/dev/null || true' EXIT
sleep 1
./network_benchmark.py urls.txt
kill -TERM "$server"; wait "$server" || true
trap - EXIT
echo "HTTP-сервер завершён"
