#!/usr/bin/env bash
# ПР-14: страничный кэш - «холодное» и «горячее» чтение одного файла.
# Нужен root: сброс кэша echo 3 > /proc/sys/vm/drop_caches. В Docker: --privileged.
set -euo pipefail
[[ $EUID -eq 0 ]] || { echo "нужен root: sudo $0" >&2; exit 1; }

file=${1:-/var/tmp/pr14-cache.bin}
mb=${2:-256}
trap 'rm -f "$file"' EXIT

head -c "${mb}M" /dev/urandom > "$file"
sync

cached_mb() { awk '/^Cached:/ {printf "%d", $2 / 1024}' /proc/meminfo; }
read_time() {   # читает файл целиком и печатает время в секундах
    local t0 t1
    t0=$(date +%s.%N); dd if="$file" of=/dev/null bs=1M status=none; t1=$(date +%s.%N)
    awk -v a="$t0" -v b="$t1" 'BEGIN {printf "%.3f", b - a}'
}

echo "файл $file, $mb МБ"
for i in 1 2 3; do
    sync; echo 3 > /proc/sys/vm/drop_caches
    c0=$(cached_mb)
    cold=$(read_time)
    c1=$(cached_mb)
    hot=$(read_time)
    printf 'попытка %d: холодное %s с (%.0f МБ/с), горячее %s с (%.0f МБ/с); Cached в /proc/meminfo %s -> %s МБ\n' \
        "$i" "$cold" "$(awk -v m="$mb" -v t="$cold" 'BEGIN {print m / t}')" \
        "$hot" "$(awk -v m="$mb" -v t="$hot" 'BEGIN {print m / t}')" "$c0" "$c1"
done
