#!/usr/bin/env bash
# ПР-12: резервное копирование, дубликаты, модель размещения, образ ext4 и проверка одной командой.
# Нужен Linux; часть с образом ext4 (fsimage.sh) нужен root, без него пропускается.
set -uo pipefail
cd "$(dirname "$0")" || exit 1

demo=$(mktemp -d); trap 'rm -rf "$demo"' EXIT
mkdir -p "$demo/src/docs"
echo "отчёт" > "$demo/src/report.txt"; echo "план" > "$demo/src/docs/plan.txt"
chmod 640 "$demo/src/report.txt"

echo "== backup.sh: первый запуск";      ./backup.sh "$demo/src" "$demo/bak"
echo "== backup.sh: повторный запуск";   ./backup.sh "$demo/src" "$demo/bak"
sleep 1; echo "новая строка" >> "$demo/src/report.txt"; echo "новый" > "$demo/src/docs/new.txt"
echo "== backup.sh: после изменений";    ./backup.sh "$demo/src" "$demo/bak"
echo "== журнал";                        sed 's/^[0-9-]* [0-9:]* /  /' "$demo/bak/.backup.log"
echo "== права в копии";                 stat -c '  %A %n' "$demo/bak/report.txt"
echo "== восстановление";                ./backup.sh --restore "$demo/bak" "$demo/restored"
diff -r "$demo/bak" "$demo/restored" | grep -v backup.log || true

mkdir -p "$demo/dup/a" "$demo/dup/b"
head -c 50000 /dev/urandom > "$demo/dup/a/photo.jpg"
cp "$demo/dup/a/photo.jpg" "$demo/dup/b/photo-copy.jpg"; cp "$demo/dup/a/photo.jpg" "$demo/dup/b/photo (1).jpg"
echo "== dedup.py -n";                   ./dedup.py -n "$demo/dup"
echo "== dedup.py";                      ./dedup.py "$demo/dup"
ls -li "$demo/dup/a" "$demo/dup/b" | awk 'NF > 3 {printf "  inode %s, ссылок %s:", $1, $3; for (i = 10; i <= NF; i++) printf " %s", $i; print ""}'

echo; echo "== Модель размещения файлов"; ./alloc.py
echo; echo "== Ссылки и inode";           ./links_demo.sh
echo
if [[ $EUID -eq 0 ]]; then ./fsimage.sh; else echo "== fsimage.sh пропущен: нужен root (sudo ./fsimage.sh)"; fi
echo; echo "== Общая проверка";            ./check_pr12.py
