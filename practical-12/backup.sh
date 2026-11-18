#!/usr/bin/env bash
# ПР-12: инкрементальное резервное копирование каталога.
#
#   ./backup.sh ИСТОЧНИК КОПИЯ             копировать новые и изменённые файлы
#   ./backup.sh --restore КОПИЯ КУДА       восстановить всё из копии
#
# Файл считается изменённым, если у него другой размер или время изменения (mtime).
# Копирование через cp -p: сохраняются права, владелец (если запуск от root) и
# временные метки, иначе следующий запуск считал бы все файлы изменёнными.
# Журнал операций дописывается в КОПИЯ/.backup.log. Повторный запуск без изменений
# ничего не копирует (идемпотентность). Файлы, удалённые в источнике, из копии не
# удаляются, а только отмечаются в журнале: копия не должна терять данные из-за
# случайного rm в источнике.
set -euo pipefail

LOG_NAME=".backup.log"

usage() {
    echo "использование: $0 ИСТОЧНИК КОПИЯ | $0 --restore КОПИЯ КУДА" >&2
    exit 2
}

log() {   # log ФАЙЛ_ЖУРНАЛА СООБЩЕНИЕ
    printf '%s %s\n' "$(date '+%F %T')" "$2" >> "$1"
}

# Одинаковы ли два файла по размеру и mtime (stat от GNU coreutils).
same_file() {
    [[ -f "$2" ]] && [[ "$(stat -c '%s %Y' "$1")" == "$(stat -c '%s %Y' "$2")" ]]
}

backup() {
    local src=${1%/} dst=${2%/}
    [[ -d "$src" ]] || { echo "нет каталога: $src" >&2; exit 1; }
    mkdir -p "$dst"
    local journal="$dst/$LOG_NAME" copied=0 skipped=0 gone=0
    log "$journal" "== резервная копия $src -> $dst"

    # Каталоги: создать и перенести права
    while IFS= read -r -d '' d; do
        mkdir -p "$dst/$d"
        chmod --reference="$src/$d" "$dst/$d"
    done < <(cd "$src" && find . -mindepth 1 -type d -print0)

    # Файлы и символические ссылки
    while IFS= read -r -d '' f; do
        f=${f#./}
        if [[ -L "$src/$f" ]]; then
            if [[ ! -L "$dst/$f" || "$(readlink "$src/$f")" != "$(readlink "$dst/$f")" ]]; then
                rm -f "$dst/$f"; cp -P "$src/$f" "$dst/$f"
                log "$journal" "ссылка   $f -> $(readlink "$src/$f")"; copied=$((copied + 1))
            else
                skipped=$((skipped + 1))
            fi
        elif same_file "$src/$f" "$dst/$f"; then
            skipped=$((skipped + 1))
        else
            local what="новый   "; [[ -e "$dst/$f" ]] && what="изменён "
            cp -p "$src/$f" "$dst/$f"
            log "$journal" "$what $f"; copied=$((copied + 1))
        fi
    done < <(cd "$src" && find . \( -type f -o -type l \) -print0)

    # Что есть в копии, но пропало в источнике
    while IFS= read -r -d '' f; do
        f=${f#./}
        [[ "$f" == "$LOG_NAME" ]] && continue
        if [[ ! -e "$src/$f" && ! -L "$src/$f" ]]; then
            log "$journal" "удалён в источнике, в копии оставлен: $f"; gone=$((gone + 1))
        fi
    done < <(cd "$dst" && find . \( -type f -o -type l \) -print0)

    log "$journal" "итог: скопировано $copied, без изменений $skipped, пропало в источнике $gone"
    echo "скопировано $copied, без изменений $skipped, пропало в источнике $gone (журнал: $journal)"
}

restore() {
    local bak=${1%/} dst=${2%/}
    [[ -f "$bak/$LOG_NAME" ]] || { echo "$bak не похож на резервную копию (нет $LOG_NAME)" >&2; exit 1; }
    mkdir -p "$dst"
    # cp -a сохраняет права, время, ссылки; журнал копии в восстановленные данные не нужен
    (cd "$bak" && find . -mindepth 1 -maxdepth 1 ! -name "$LOG_NAME" -exec cp -a {} "$dst/" \;)
    log "$bak/$LOG_NAME" "== восстановление $bak -> $dst"
    echo "восстановлено в $dst: $(find "$dst" -type f | wc -l) файлов"
}

case "${1:-}" in
    --restore) [[ $# -eq 3 ]] || usage; restore "$2" "$3" ;;
    -h|--help|"") usage ;;
    *) [[ $# -eq 2 ]] || usage; backup "$1" "$2" ;;
esac
