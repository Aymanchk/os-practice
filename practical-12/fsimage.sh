#!/usr/bin/env bash
# ПР-12: файловая система ext4 в файле-образе и «диск полон, а место есть».
#
# Создаёт образ 16 МБ (dd), форматирует ext4 с маленьким числом inode (-N 128),
# монтирует через loop, создаёт пустые файлы, пока не кончатся inode, и
# показывает, что блоков свободно почти всё, а новый файл создать нельзя.
# Нужен root (mount). В Docker: docker run --privileged ...
# Всё создаётся во временном каталоге и удаляется в конце, даже при ошибке.
set -euo pipefail

[[ $EUID -eq 0 ]] || { echo "нужен root: sudo $0" >&2; exit 1; }

work=$(mktemp -d)
img="$work/fs.img"
mnt=/mnt/pr12
cleanup() {
    mountpoint -q "$mnt" && umount "$mnt"
    rm -rf "$work"; rmdir "$mnt" 2>/dev/null || true
}
trap cleanup EXIT

echo "== 1. Образ 16 МБ и ext4 на 128 inode"
dd if=/dev/zero of="$img" bs=1M count=16 status=none
mkfs.ext4 -q -N 128 -L pr12 "$img"
mkdir -p "$mnt"
mount -o loop "$img" "$mnt"
echo "смонтировано: $(findmnt -n -o SOURCE,FSTYPE "$mnt")"
dumpe2fs -h "$img" 2>/dev/null | grep -E '^(Inode count|Block count|Block size|Inode size|Free inodes|Free blocks):'

echo
echo "== 2. До: место и inode"
df -h "$mnt" | sed 's/^/  /'
df -i "$mnt" | sed 's/^/  /'

echo
echo "== 3. Создаю пустые файлы, пока не кончатся inode"
n=0
while touch "$mnt/f$n" 2>"$work/err"; do
    n=$((n + 1))
    if (( n % 25 == 0 )); then
        echo "  создано $n файлов, занято inode: $(df --output=iused "$mnt" | tail -1 | tr -d ' ')"
    fi
done
echo "  создано файлов: $n, следующий touch: $(cat "$work/err")"

echo
echo "== 4. После: inode кончились, а блоков свободно почти всё"
df -h "$mnt" | sed 's/^/  /'
df -i "$mnt" | sed 's/^/  /'

echo
echo "== 5. В существующий файл писать можно: блоки есть, новый inode не нужен"
dd if=/dev/zero of="$mnt/f0" bs=1M count=4 status=none && ls -l "$mnt/f0" | awk '{print "  f0:", $5, "Б"}'
echo "  mkdir: $(mkdir "$mnt/newdir" 2>&1 || true)"

echo
echo "== 6. Удаляю один файл: inode освободился, файл снова создаётся"
rm "$mnt/f1"
touch "$mnt/again" && echo "  touch again: ok, свободно inode: $(df --output=iavail "$mnt" | tail -1 | tr -d ' ')"
