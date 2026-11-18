#!/usr/bin/env bash
# ПР-12: жёсткая и символическая ссылка, inode и число ссылок (для контрольных вопросов).
set -euo pipefail
work=$(mktemp -d); trap 'rm -rf "$work"' EXIT
cd "$work"

echo "данные" > file.txt
ln file.txt hard.txt
ln -s file.txt soft.txt
echo "== до удаления (первый столбец - номер inode, третий - число жёстких ссылок)"
ls -li | awk 'NR>1 {printf "  %s %s %s", $1, $2, $3; for (i = 10; i <= NF; i++) printf " %s", $i; print ""}'

rm file.txt
echo "== после rm file.txt"
ls -li | awk 'NR>1 {printf "  %s %s %s", $1, $2, $3; for (i = 10; i <= NF; i++) printf " %s", $i; print ""}'
echo "  cat hard.txt: $(cat hard.txt)"
echo "  cat soft.txt: $(cat soft.txt 2>&1 || true)"

echo "== жёсткая ссылка на каталог и между ФС"
mkdir d
echo "  ln d d2: $(ln d d2 2>&1 || true)"
echo "  ln hard.txt /dev/shm/x: $(ln hard.txt /dev/shm/pr12-x 2>&1 || true)"
rm -f /dev/shm/pr12-x
