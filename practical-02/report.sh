#!/usr/bin/env bash
set -euo pipefail

usage() {
    printf 'Использование: %s <каталог> <ERROR|WARN> [--top N]\n' "$0" >&2
}

fail() {
    printf 'Ошибка: %s\n' "$1" >&2
    usage
    exit 1
}

if [[ $# -ne 2 && $# -ne 4 ]]; then
    fail "неверное число аргументов"
fi

directory=$1
level=$2
top=0

if [[ ! -d "$directory" ]]; then
    fail "каталог не существует: $directory"
fi

if [[ "$level" != ERROR && "$level" != WARN ]]; then
    fail "уровень должен быть ERROR или WARN"
fi

if [[ $# -eq 4 ]]; then
    if [[ "$3" != --top ]]; then
        fail "ожидается --top N"
    fi
    if [[ ! "$4" =~ ^[0-9]+$ || "$4" =~ ^0+$ ]]; then
        fail "N должно быть положительным целым числом"
    fi
    top=$4
fi

printf 'Модуль\tСообщений\n'

find "$directory" -type f -name '*.log' -exec awk -v wanted="$level" '
    $3 == wanted {
        for (i = 4; i <= NF; i++) {
            if ($i ~ /^module=/) {
                sub(/^module=/, "", $i)
                print $i
                break
            }
        }
    }
' {} + |
    LC_ALL=C sort |
    uniq -c |
    LC_ALL=C sort -k1,1nr -k2,2 |
    awk -v limit="$top" '
        limit == 0 || NR <= limit {
            printf "%s\t%d\n", $2, $1
        }
    '
