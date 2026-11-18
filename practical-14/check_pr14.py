#!/usr/bin/env python3
"""Проверка ПР-14: сборка без предупреждений, корректность записи, число системных
вызовов, опрос против блокировки; от root ещё O_DIRECT мимо кэша."""
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
total = 0
failed = 0


def check(name, condition):
    global total, failed
    total += 1
    if condition:
        print(f"[ok]     {name}")
    else:
        failed += 1
        print(f"[ОШИБКА] {name}")


def sh(*args, **kw):
    return subprocess.run([str(a) for a in args], capture_output=True, text=True, timeout=600, **kw)


with tempfile.TemporaryDirectory() as tmp:
    tmp = Path(tmp)
    exe = tmp / "iobench"
    b = sh("gcc", "-O2", "-Wall", "-Wextra", "-Werror", "-o", exe, HERE / "iobench.c")
    check("gcc -Wall -Wextra -Werror: собирается без предупреждений", b.returncode == 0 and not b.stderr)

    ok = True
    for mode in ("byte", "block", "fwrite", "cached"):
        f = tmp / f"{mode}.bin"
        r = sh(exe, mode, f, 1)
        data = f.read_bytes() if f.exists() else b""
        ok &= r.returncode == 0 and len(data) == 1 << 20 and data == b"x" * (1 << 20)
    check("все способы записывают ровно 1 МБ из байтов 'x'", ok)
    check("неверный способ и объём 0: код 2", sh(exe, "nope", tmp / "z", 1).returncode == 2
          and sh(exe, "block", tmp / "z", 0).returncode == 2)

    def writes(mode, mb):
        out = tmp / f"strace-{mode}"
        sh("strace", "-c", "-o", out, exe, mode, tmp / "s.bin", mb)
        m = re.search(r"^\s*[\d.]+\s+[\d.]+\s+\d+\s+(\d+)\s+(?:\d+\s+)?write$", out.read_text(), re.M)
        return int(m.group(1)) - 1 if m else -1          # минус один write: printf итога в stdout

    have_strace = sh("sh", "-c", "command -v strace").returncode == 0
    if have_strace:
        check("byte, 1 МБ: ровно 1048576 вызовов write", writes("byte", 1) == 1 << 20)
        check("block, 100 МБ: 1600 вызовов write (по 64 КБ)", writes("block", 100) == 1600)
        blk = os.stat(tmp).st_blksize
        check(f"fwrite, 10 МБ: write по {blk} Б, то есть {10 * (1 << 20) // blk} вызовов",
              writes("fwrite", 10) == 10 * (1 << 20) // blk)
    else:
        print("[пропуск] strace не установлен")

r = sh(sys.executable, HERE / "poll_demo.py", "busy")
busy = float(re.search(r"\((\d+)% одного ядра\)", r.stdout).group(1))
r = sh(sys.executable, HERE / "poll_demo.py", "block")
block = float(re.search(r"\((\d+)% одного ядра\)", r.stdout).group(1))
check(f"busy-wait занимает ядро почти целиком ({busy:.0f}% > 80%)", busy > 80)
check(f"блокирующее чтение почти не тратит CPU ({block:.0f}% < 5%)", block < 5)

if os.geteuid() == 0:
    r = sh(HERE / "direct_demo.sh")
    rows = dict(re.findall(r"^(\w+)\s.*\(([+-]\d+)\)$", r.stdout, re.M))
    check("O_DIRECT не растит страничный кэш, обычная запись растит на объём файла",
          r.returncode == 0 and int(rows.get("direct", 999)) < 20 and int(rows.get("block", 0)) >= 180)
    r = sh(HERE / "cache_demo.sh")
    m = re.search(r"Cached в /proc/meminfo (\d+) -> (\d+)", r.stdout)
    check("холодное чтение кладёт файл 256 МБ в страничный кэш", m and int(m.group(2)) - int(m.group(1)) >= 230)
else:
    print("[пропуск] O_DIRECT и drop_caches: нужен root")

print()
print(f"Проверок: {total}, провалено: {failed}")
sys.exit(1 if failed else 0)
