#!/usr/bin/env bash
# ПР-1: проверка настроек одной командой. Скрипт ничего не меняет в системе:
# он только показывает пользователей, права и настройки ~/.bashrc.
set -uo pipefail

echo "== Пользователь и группа"
whoami
getent group developers || echo "Группы developers нет (см. «Как повторить» в README)"
id student2 2>/dev/null || echo "Пользователя student2 нет"

echo; echo "== Каталог /srv/shared"
ls -ld /srv/shared 2>/dev/null || { echo "Каталога /srv/shared нет"; exit 1; }
stat -c '%U %G %a %n' /srv/shared

file=/srv/shared/student2.txt
if [[ -e "$file" ]]; then
    stat -c '%U %G %a %n' "$file"
    cat "$file"
    if [[ -w /srv/shared ]]; then
        echo "У $(whoami) есть право записи в /srv/shared: удалить файл он смог бы, проверка удаления пропущена"
    else
        # Права записи в каталог нет, поэтому rm гарантированно не сработает.
        rm -f "$file"
        echo "rm exit status: $?"
    fi
else
    echo "Файла $file нет: создайте его от имени student2"
fi

echo; echo "== Настройки ~/.bashrc в новой интерактивной сессии"
bash -ic 'alias ll; alias cshared; echo "OS_PRACTICE=$OS_PRACTICE"; bash -c "echo дочерний процесс видит: \$OS_PRACTICE"' 2>/dev/null
