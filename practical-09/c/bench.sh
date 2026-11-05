#!/bin/bash
# Запускает все сценарии бенчмарка и печатает таблицу в формате Markdown.
cd "$(dirname "$0")" || exit 1
declare -A title=([small]="Много мелких выделений" [mixed]="Чередование alloc / free" [large]="Крупные блоки")
declare -A who=([first]="свой, first fit" [best]="свой, best fit" [glibc]="glibc malloc")
echo "| Сценарий | Аллокатор | Время, мс | Пик RSS, КБ | Фрагментация | Отказов |"
echo "|---|---|---:|---:|---:|---:|"
for s in small mixed large; do
    for a in first best glibc; do
        read -r _ _ ms rss frag fails < <(./bench "$s" "$a") || exit 1
        echo "| ${title[$s]} | ${who[$a]} | $ms | $rss | $frag | $fails |"
    done
done
