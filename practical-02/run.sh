#!/usr/bin/env bash
# ПР-2: генерация журналов, отчёты report.sh, hello.py и strace одной командой.
set -uo pipefail
cd "$(dirname "$0")" || exit 1

echo "== Исходные данные"
./gen_logs.py
echo "файлов: $(find data -name '*.log' | wc -l), md5: $(cat data/*.log | md5sum)"

echo; echo "== ./report.sh data ERROR --top 3"
./report.sh data ERROR --top 3
echo; echo "== ./report.sh data WARN"
./report.sh data WARN

echo; echo "== Неверные аргументы (каждый раз код 1)"
for args in "" "/nope ERROR" "data INFO" "data ERROR --top abc"; do
    # shellcheck disable=SC2086
    ./report.sh $args; echo "код возврата: $?"
done

echo; echo "== hello.py"
./hello.py data/01.log
stat -c '%s' data/01.log

echo; echo "== Системные вызовы (strace)"
if command -v strace >/dev/null; then
    mkdir -p out
    strace -f -y -o out/trace.txt python3 hello.py data/01.log > /dev/null
    strace -f -y -o out/trace_cat.txt cat data/01.log > /dev/null
    echo "python3 hello.py: $(grep -vc '+++ exited' out/trace.txt) вызовов, из них с файлом data/01.log: $(grep 'data/01.log' out/trace.txt | grep -vc execve)"
    echo "cat:              $(grep -vc '+++ exited' out/trace_cat.txt) вызовов, из них с файлом data/01.log: $(grep 'data/01.log' out/trace_cat.txt | grep -vc execve)"
    echo "Трассировки этого запуска: out/trace.txt, out/trace_cat.txt"
else
    echo "strace не установлен: sudo apt install -y strace"
fi
