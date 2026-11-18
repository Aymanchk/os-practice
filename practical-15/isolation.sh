#!/usr/bin/env bash
# ПР-15: изоляция контейнеров через пространства имён (PID, mount, network, UTS).
# Два контейнера pr15-calc и третий «наблюдатель» с --pid=host, который видит
# процессы хоста (виртуальной машины Docker).
set -euo pipefail
cleanup() { docker rm -f iso-a iso-b >/dev/null 2>&1 || true; }
trap cleanup EXIT
cleanup

docker run -d --name iso-a --hostname box-a pr15-calc >/dev/null
docker run -d --name iso-b --hostname box-b pr15-calc >/dev/null
sleep 1.5

# Список процессов без ps (в образе slim его нет): читаем /proc
PS='import os
for p in sorted(int(x) for x in os.listdir("/proc") if x.isdigit()):
    try:
        cmd = open(f"/proc/{p}/cmdline", "rb").read().replace(b"\0", b" ").decode().strip()
        if not cmd:   # поток ядра: командной строки нет, берём имя
            cmd = "[" + open(f"/proc/{p}/comm").read().strip() + "]"
    except OSError:
        continue
    print(f"    PID {p:>5}  {cmd.splitlines()[0][:60]}")'

for c in iso-a iso-b; do
    echo "== $c: процессы, которые он видит"
    docker exec "$c" python3 -c "$PS"
done

echo
echo "== Хост (ВМ Docker) глазами контейнера с --pid=host"
docker run --rm --pid=host python:3.14-slim python3 -c "$PS" > /tmp/pr15-host-ps.txt
echo "    всего процессов на хосте: $(wc -l < /tmp/pr15-host-ps.txt | tr -d " ")"
grep calc_server /tmp/pr15-host-ps.txt | head -2
for c in iso-a iso-b; do
    echo "    $c: PID 1 внутри = PID $(docker inspect -f '{{.State.Pid}}' "$c") на хосте"
done
rm -f /tmp/pr15-host-ps.txt

echo
echo "== Пространства имён PID 1 (одинаковое число = общее пространство)"
NS=$(cat <<'PY'
import os
ids = []
for n in ("pid", "mnt", "net", "uts", "ipc"):
    ids.append(n + "=" + os.readlink("/proc/1/ns/" + n).split("[")[1].rstrip("]"))
print("    " + "  ".join(ids))
PY
)
for c in iso-a iso-b; do echo "  $c:"; docker exec "$c" python3 -c "$NS"; done
echo "  хост:"; docker run --rm --privileged --pid=host --net=host --uts=host --ipc=host python:3.14-slim python3 -c "$NS"

echo
echo "== UTS и сеть: у каждого своё имя и свой IP"
for c in iso-a iso-b; do
    docker exec "$c" python3 -c 'import socket; h = socket.gethostname(); print(f"    {h}: IP {socket.gethostbyname(h)}")'
done
echo "    iso-a -> iso-b по имени: $(docker exec iso-a python3 -c '
import socket
try:
    socket.gethostbyname("iso-b"); print("видит")
except OSError as e:
    print("не видит (" + type(e).__name__ + "): в сети по умолчанию нет DNS между контейнерами")')"

echo
echo "== mount: файл в /tmp одного контейнера не виден в другом"
docker exec iso-a sh -c 'echo секрет > /tmp/only-in-a; ls -l /tmp/only-in-a' | sed 's/^/    iso-a: /'
docker exec iso-b sh -c 'ls /tmp/only-in-a 2>&1 || true' | sed 's/^/    iso-b: /'
