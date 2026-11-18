#!/usr/bin/env bash
# ПР-14: время записи 100 МБ тремя способами и число системных вызовов (strace -c).
# Запись по одному байту под strace идёт очень долго (каждый вызов ловится
# отладчиком), поэтому для неё strace запускается на 1 МБ: число write ровно
# равно числу байт, его легко умножить на 100.
set -euo pipefail
cd "$(dirname "$0")"
make -s iobench
out=$(mktemp -d); trap 'rm -rf "$out"' EXIT

echo "== Время, 100 МБ (без strace)"
for m in byte block fwrite; do ./iobench "$m" "$out/f.bin" 100; done

summary() {   # строки write/итог из strace -c
    awk '/^ *[0-9.]+ +[0-9.]+ +[0-9]+ +[0-9]+ / && ($NF == "write" || $NF == "total") {printf "  %-6s вызовов %10s, время в ядре %s с\n", $NF, $4, $2}
         /^-+ / {next} $NF == "total" {}' "$1"
}

echo
echo "== strace -c: block, 100 МБ"
strace -c -o "$out/s1" ./iobench block "$out/f.bin" 100 > /dev/null; summary "$out/s1"
echo "== strace -c: fwrite, 100 МБ"
strace -c -o "$out/s2" ./iobench fwrite "$out/f.bin" 100 > /dev/null; summary "$out/s2"
echo "== strace -c: byte, 1 МБ"
strace -c -o "$out/s3" ./iobench byte "$out/f.bin" 1 > /dev/null; summary "$out/s3"
echo "== размер буфера stdio = st_blksize файловой системы: $(stat -c %o "$out/f.bin") Б"
