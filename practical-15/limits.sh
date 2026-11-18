#!/usr/bin/env bash
# ПР-15: лимиты памяти и CPU для контейнера (--memory, --cpus) под нагрузкой.
# Запускается на машине с Docker (хост), образ pr15-calc должен быть собран.
set -euo pipefail
cd "$(dirname "$0")"
cleanup() { docker rm -f calc-free calc-limited >/dev/null 2>&1 || true; }
trap cleanup EXIT
cleanup

stats() {   # снимок docker stats через 3 с после начала нагрузки
    sleep 3
    docker stats --no-stream --format '  {{.Name}}: CPU {{.CPUPerc}}, память {{.MemUsage}}' "$1"
}

echo "== 1. Без лимитов: 4 клиента по «!cpu 6»"
docker run -d --rm --name calc-free -p 8001:8000 pr15-calc >/dev/null; sleep 1.5
./client.py --port 8001 --load 4 "!cpu 6" > /dev/null & load=$!
stats calc-free; wait $load

echo
echo "== 2. С лимитами --cpus=0.5 --memory=128m: та же нагрузка"
docker run -d --rm --name calc-limited --cpus=0.5 --memory=128m --memory-swap=128m \
    -p 8002:8000 pr15-calc >/dev/null; sleep 1.5
echo "  cgroup внутри контейнера: cpu.max = $(docker exec calc-limited cat /sys/fs/cgroup/cpu.max)," \
     "memory.max = $(docker exec calc-limited cat /sys/fs/cgroup/memory.max)"
./client.py --port 8002 --load 4 "!cpu 6" > /dev/null & load=$!
stats calc-limited; wait $load

echo
echo "== 3. Память: занять 64 МБ (в пределах лимита) и 300 МБ (больше лимита 128 МБ)"
./client.py --port 8002 "!mem 64" & sleep 1.5
docker stats --no-stream --format '  во время !mem 64: память {{.MemUsage}}' calc-limited; wait
./client.py --port 8002 "!mem 300" || true
echo "  memory.events: $(docker exec calc-limited cat /sys/fs/cgroup/memory.events | tr '\n' ' ')"
echo "  сервер после OOM жив: $(./client.py --port 8002 '6 * 7')"
echo "  журнал сервера:"; docker logs calc-limited 2>&1 | tail -4 | sed 's/^/    /'
