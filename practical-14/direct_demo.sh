#!/usr/bin/env bash
# ПР-14: обычная запись через страничный кэш против O_DIRECT.
# Пишем на настоящую ext4 в loop-образе (на overlayfs Docker O_DIRECT ведёт себя
# по-разному). Смотрим время и рост Cached в /proc/meminfo. Нужен root.
set -euo pipefail
[[ $EUID -eq 0 ]] || { echo "нужен root: sudo $0" >&2; exit 1; }
cd "$(dirname "$0")"
make -s iobench

work=$(mktemp -d); mnt=/mnt/pr14
loopdev=""
cleanup() {
    mountpoint -q "$mnt" && umount "$mnt"
    [[ -n "$loopdev" ]] && losetup -d "$loopdev" 2>/dev/null
    rm -rf "$work"; rmdir "$mnt" 2>/dev/null || true
}
trap cleanup EXIT
dd if=/dev/zero of="$work/fs.img" bs=1M count=700 status=none
mkfs.ext4 -q "$work/fs.img"; mkdir -p "$mnt"
# loop-устройство с direct-io: сам файл-образ не кэшируется, в Cached видно только кэш ext4
loopdev=$(losetup --direct-io=on -f --show "$work/fs.img")
mount "$loopdev" "$mnt"

cached() { awk '/^Cached:/ {printf "%d", $2 / 1024}' /proc/meminfo; }
for mode in block cached direct; do
    sync; echo 3 > /proc/sys/vm/drop_caches
    before=$(cached)
    line=$(./iobench "$mode" "$mnt/$mode.bin" 200)
    after=$(cached)
    printf '%s   Cached: %4s -> %4s МБ (%+d)\n' "$line" "$before" "$after" "$((after - before))"
done
echo "block  = write без fsync: данные только в кэше, на диск ядро сбросит позже"
echo "cached = write + fsync: через кэш, но fsync ждёт, пока данные дойдут до устройства"
echo "direct = O_DIRECT + fsync: мимо кэша, прямо в устройство"
