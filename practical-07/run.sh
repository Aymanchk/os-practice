#!/usr/bin/env bash
# ПР-7: клиент-сервер на FIFO и на сокете, замеры IPC и проверка очистки.
# Серверы здесь запускаются в фоне. Вручную их можно запустить в двух
# терминалах, как описано в README.
set -uo pipefail
cd "$(dirname "$0")" || exit 1
mkdir -p out

wait_for() {  # ждём, пока сервер создаст файл FIFO или сокета
    for _ in $(seq 50); do [[ -e "$1" ]] && return 0; sleep 0.1; done
    echo "Сервер не запустился"; exit 1
}

echo "== FIFO: клиент без сервера"
./fifo_client.py "2+2"

echo; echo "== FIFO: сервер и клиенты по очереди"
./fifo_server.py > out/fifo_server.txt & server=$!
wait_for /tmp/pr07_request.fifo
for expression in "2+2" "10/4" "(3+4)*5" "2**10" "1/0" "abc"; do
    ./fifo_client.py "$expression"
done
./fifo_client.py '!stop'
wait "$server"
echo "-- журнал сервера:"; cat out/fifo_server.txt

echo; echo "== Unix-сокет: 5 клиентов одновременно, по процессу на клиента"
./socket_server.py > out/socket_server.txt & server=$!
wait_for /tmp/pr07.sock
./socket_clients.py
kill -TERM "$server"; wait "$server"
echo "-- журнал сервера:"; cat out/socket_server.txt

echo; echo "== Передача 10^7 чисел разными способами"
./ipc_bench.py

echo; echo "== Запись в pipe без читателей"
./broken_pipe_demo.py

echo; echo "== Проверка очистки"
if ls /tmp/pr07* 2>/dev/null; then echo "Остались файлы в /tmp!"; else echo "В /tmp нет FIFO и сокетов этой работы"; fi
if ls /dev/shm/psm_* 2>/dev/null; then echo "Остались сегменты в /dev/shm!"; else echo "В /dev/shm нет сегментов разделяемой памяти"; fi
