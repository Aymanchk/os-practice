#!/usr/bin/env bash
# ПР-15: контейнер против виртуальной машины - время запуска и ресурсы.
#
# Скрипт для macOS с Docker Desktop: Docker Desktop сам держит Linux-ВМ (Apple
# Virtualization.framework), внутри которой работают контейнеры. Поэтому на одной
# машине можно честно измерить обе вещи:
#   - запуск контейнера внутри уже работающей ВМ;
#   - холодный запуск самой ВМ (выключить Docker Desktop и включить снова).
# Шаг с ВМ перезапускает Docker Desktop (docker desktop stop/start);
# пропустить его: ./vm_vs_container.sh --no-vm
set -euo pipefail
cd "$(dirname "$0")"

median() { sort -n | awk '{a[NR] = $1} END {print (NR % 2) ? a[(NR + 1) / 2] : (a[NR / 2] + a[NR / 2 + 1]) / 2}'; }
ms() { python3 -c 'import time; print(int(time.time() * 1000))'; }

echo "== 1. Запуск контейнера (10 раз, медиана)"
times=(); for i in $(seq 10); do
    t0=$(ms); docker run --rm pr15-calc python3 -c pass; t1=$(ms); times+=($((t1 - t0)))
done
echo "  docker run --rm pr15-calc python3 -c pass: $(printf '%s\n' "${times[@]}" | median) мс (все: ${times[*]})"

docker rm -f calc-start >/dev/null 2>&1 || true
t0=$(ms); docker run -d --rm --name calc-start -p 8010:8000 pr15-calc >/dev/null
until ./client.py --port 8010 "1 + 1" >/dev/null 2>&1; do sleep 0.02; done; t1=$(ms)
echo "  от docker run до первого ответа калькулятора: $((t1 - t0)) мс"
sleep 1
echo "  память работающего контейнера: $(docker stats --no-stream --format '{{.MemUsage}}' calc-start | cut -d/ -f1)"
echo "  процессов в контейнере: $(docker top calc-start | tail -n +2 | wc -l | tr -d ' ')"
docker rm -f calc-start >/dev/null
echo "  размер образа pr15-calc: $(docker image inspect -f '{{.Size}}' pr15-calc | awk '{printf "%.0f МБ", $1 / 1e6}')"

echo
echo "== 2. Виртуальная машина Docker Desktop"
echo "  память, выделенная ВМ: $(docker info --format '{{.MemTotal}}' | awk '{printf "%.1f ГБ", $1 / 1024^3}'), процессоров: $(docker info --format '{{.NCPU}}')"
echo "  ядро ВМ: $(docker info --format '{{.KernelVersion}}'), процессов внутри ВМ: $(docker run --rm --pid=host pr15-calc sh -c 'ls -d /proc/[0-9]* | wc -l')"
vm_rss=$(ps -axo rss=,comm= | awk '/[Vv]irtual[Mm]achine|com.docker.virtualization|com.docker.krun/ {s += $1} END {printf "%.0f", s / 1024}')
echo "  резидентная память процесса ВМ на macOS: ${vm_rss} МБ"
disk=$(find ~/Library/Containers/com.docker.docker/Data/vms -name 'Docker.raw' 2>/dev/null | head -1)
[[ -n "$disk" ]] && echo "  диск ВМ: $(du -h "$disk" | cut -f1) занято (файл $(basename "$disk"))"

if [[ "${1:-}" != "--no-vm" ]]; then
    echo "  выключаю ВМ: docker desktop stop"
    docker desktop stop >/dev/null 2>&1
    while docker info >/dev/null 2>&1; do sleep 0.5; done
    sleep 3
    t0=$(ms); docker desktop start >/dev/null 2>&1 &
    until docker info >/dev/null 2>&1; do sleep 0.2; done
    t1=$(ms); wait
    echo "  холодный запуск ВМ (docker desktop start -> docker info отвечает): $(( (t1 - t0) / 1000 )).$(( (t1 - t0) % 1000 / 100 )) с"
    t0=$(ms); docker run --rm pr15-calc python3 -c pass; t1=$(ms)
    echo "  первый контейнер после запуска ВМ: $((t1 - t0)) мс"
fi
