#!/usr/bin/env python3
"""Проверка ПР-12: backup.sh (инкрементальность, права, восстановление), dedup.py, alloc.py.
Нужен Linux (backup.sh использует stat и chmod из GNU coreutils)."""
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import alloc

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


def sh(*args):
    return subprocess.run([str(a) for a in args], capture_output=True, text=True, timeout=120)


def tree(root):
    """Снимок дерева: путь -> (тип, права, mtime, содержимое или цель ссылки)."""
    out = {}
    for p in sorted(Path(root).rglob("*")):
        rel = str(p.relative_to(root))
        if rel == ".backup.log":
            continue
        st = p.lstat()
        if p.is_symlink():
            out[rel] = ("link", os.readlink(p))
        elif p.is_dir():
            out[rel] = ("dir", oct(st.st_mode & 0o7777))
        else:
            out[rel] = ("file", oct(st.st_mode & 0o7777), int(st.st_mtime), p.read_bytes())
    return out


with tempfile.TemporaryDirectory() as tmp:
    tmp = Path(tmp)
    src, bak, res = tmp / "src", tmp / "bak", tmp / "restored"
    (src / "docs" / "deep").mkdir(parents=True)
    (src / "a.txt").write_text("первый\n")
    (src / "docs" / "b.txt").write_text("второй\n")
    (src / "docs" / "deep" / "c.bin").write_bytes(os.urandom(5000))
    (src / "имя с пробелом.txt").write_text("пробелы\n")
    (src / "secret.txt").write_text("только владелец\n")
    os.chmod(src / "secret.txt", 0o600)
    os.chmod(src / "docs", 0o750)
    os.symlink("a.txt", src / "link-to-a")

    r1 = sh(HERE / "backup.sh", src, bak)
    check("первый запуск: скопировано 6, код 0", r1.returncode == 0 and "скопировано 6," in r1.stdout)
    check("копия совпадает с источником: содержимое, права, mtime, ссылка", tree(src) == tree(bak))
    r2 = sh(HERE / "backup.sh", src, bak)
    check("повторный запуск без изменений: скопировано 0 (идемпотентность)", "скопировано 0," in r2.stdout)

    time.sleep(1.1)
    (src / "a.txt").write_text("первый, изменённый\n")
    (src / "new.txt").write_text("новый\n")
    (src / "docs" / "b.txt").unlink()
    r3 = sh(HERE / "backup.sh", src, bak)
    log = (bak / ".backup.log").read_text()
    check("после изменений: скопировано 2 (изменённый и новый)", "скопировано 2," in r3.stdout)
    check("удалённый в источнике файл остался в копии и отмечен в журнале",
          (bak / "docs" / "b.txt").exists() and "удалён в источнике, в копии оставлен: docs/b.txt" in log)
    check("в журнале есть «изменён a.txt» и «новый new.txt»", "изменён  a.txt" in log and "новый    new.txt" in log)
    check("права 600 у secret.txt и 750 у docs сохранены",
          (bak / "secret.txt").stat().st_mode & 0o777 == 0o600 and (bak / "docs").stat().st_mode & 0o777 == 0o750)

    r4 = sh(HERE / "backup.sh", "--restore", bak, res)
    t_bak, t_res = tree(bak), tree(res)
    check("восстановление: дерево совпадает с копией (права, время, ссылка)", r4.returncode == 0 and t_bak == t_res)
    check("восстановление не тащит журнал копии", not (res / ".backup.log").exists())
    check("--restore из каталога без журнала отказывается", sh(HERE / "backup.sh", "--restore", src, tmp / "x").returncode == 1)
    check("без аргументов: подсказка и код 2", sh(HERE / "backup.sh").returncode == 2)

    # ---------- dedup ----------
    d = tmp / "dup"
    (d / "sub").mkdir(parents=True)
    blob = os.urandom(10_000)
    for name in ("one.bin", "sub/two.bin", "sub/three.bin"):
        (d / name).write_bytes(blob)
    (d / "other.bin").write_bytes(os.urandom(10_000))              # тот же размер, другое содержимое
    (d / "small.txt").write_text("x" * 100)
    (d / "small-copy.txt").write_text("x" * 100)
    os.link(d / "one.bin", d / "already-link.bin")                # уже жёсткая ссылка
    (d / "empty1").touch(); (d / "empty2").touch()
    before = {p: p.read_bytes() for p in d.rglob("*") if p.is_file()}

    dry = sh(HERE / "dedup.py", "-n", d)
    check("dry run: 2 группы, 3 лишние копии, можно сэкономить 20100 Б",
          "групп дубликатов: 2, лишних копий: 3, можно сэкономить: 20100 Б" in dry.stdout)
    check("dry run ничего не меняет: у .bin по-прежнему 4 разных inode", len({p.stat().st_ino for p in d.rglob("*.bin")}) == 4)
    run = sh(HERE / "dedup.py", d)
    check("замена: сэкономлено 20100 Б", "сэкономлено: 20100 Б" in run.stdout)
    inode = (d / "one.bin").stat().st_ino
    check("one, two, three и already-link теперь один inode с 4 ссылками",
          all((d / n).stat().st_ino == inode for n in ("sub/two.bin", "sub/three.bin", "already-link.bin"))
          and (d / "one.bin").stat().st_nlink == 4)
    check("other.bin того же размера не тронут", (d / "other.bin").stat().st_ino != inode)
    check("содержимое всех файлов не изменилось", all(p.read_bytes() == b for p, b in before.items()))
    check("пустые файлы не объединяются", (d / "empty1").stat().st_ino != (d / "empty2").stat().st_ino)
    check("временных файлов не осталось", not list(d.rglob("*.dedup-tmp")))
    check("повторный запуск: дубликатов 0", "групп дубликатов: 0" in sh(HERE / "dedup.py", d).stdout)

# ---------- модель размещения ----------
ops = alloc.workload()
r = {cls.name: alloc.run(cls, ops) for cls in (alloc.Contiguous, alloc.Linked, alloc.Indexed)}
check("непрерывное: есть отказы при достаточном свободном месте (внешняя фрагментация)",
      r["непрерывный"]["failed_with_space"] > 0)
check("связанное: отказов при свободном месте нет", r["связанный"]["failed_with_space"] == 0)
check("произвольный доступ: непрерывное 1 чтение, индексное 2, связанное k+1",
      r["непрерывный"]["max_reads"] == 1 and r["индексный"]["max_reads"] == 2
      and r["связанный"]["max_reads"] == alloc.MAX_FILE)
check("у индексного по одному служебному блоку на файл (файлы до 128 блоков)",
      r["индексный"]["meta"] == r["индексный"]["files"])
check("поток операций воспроизводится (seed)", alloc.workload() == ops)
check("суммы блоков сходятся: данные + служебные + свободные = 512",
      all(v["data"] + v["meta"] + v["free"] == alloc.DISK for v in r.values()))

print()
print(f"Проверок: {total}, провалено: {failed}")
sys.exit(1 if failed else 0)
