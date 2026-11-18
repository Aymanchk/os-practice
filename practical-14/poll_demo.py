#!/usr/bin/env python3
"""ПР-14: чтение из FIFO опросом (busy-wait) и блокирующим ожиданием.

    ./poll_demo.py busy    читатель открывает FIFO с O_NONBLOCK и крутится в цикле
    ./poll_demo.py block   читатель спит в read(), пока ядро не разбудит
    ./poll_demo.py both    оба режима подряд (по умолчанию)

Писатель (дочерний процесс) отправляет 6 сообщений с паузой 0,5 с. Читатель
считает, сколько процессорного времени (user + sys) он потратил за то же время.
Во время работы снимается строка из ps с %CPU читателя.
"""
import os
import resource
import subprocess
import sys
import tempfile
import time

MESSAGES = 6
PAUSE = 0.5


def writer(path):
    fd = os.open(path, os.O_WRONLY)
    for i in range(MESSAGES):
        time.sleep(PAUSE)
        os.write(fd, f"сообщение {i + 1}\n".encode())
    os.close(fd)


def reader(path, mode):
    flags = os.O_RDONLY | (os.O_NONBLOCK if mode == "busy" else 0)
    fd = os.open(path, flags)
    got, empty_reads, buf = 0, 0, b""
    while got < MESSAGES:
        try:
            chunk = os.read(fd, 4096)
        except BlockingIOError:          # данных нет: в busy-wait просто пробуем снова
            empty_reads += 1
            continue
        if not chunk:
            if mode == "busy":           # писатель ещё не открыл FIFO или между сообщениями
                empty_reads += 1
                continue
            break
        buf += chunk
        got = buf.count(b"\n")
    os.close(fd)
    return got, empty_reads


def run(mode):
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "fifo")
        os.mkfifo(path)
        pid = os.fork()
        if pid == 0:
            if mode == "block":
                writer(path)
            else:
                time.sleep(0.05)         # дать читателю открыть FIFO с O_NONBLOCK первым
                writer(path)
            os._exit(0)
        # снимок ps через 1,5 с работы читателя
        snap = subprocess.Popen(["sh", "-c", f"sleep 1.5; ps -o pid,stat,%cpu,time,cmd -p {os.getpid()}"],
                                stdout=subprocess.PIPE, text=True)
        before = resource.getrusage(resource.RUSAGE_SELF)
        t0 = time.monotonic()
        got, empty = reader(path, mode)
        wall = time.monotonic() - t0
        after = resource.getrusage(resource.RUSAGE_SELF)
        os.waitpid(pid, 0)
        ps_out = snap.communicate()[0].rstrip()
    cpu = (after.ru_utime - before.ru_utime) + (after.ru_stime - before.ru_stime)
    print(f"== {mode}: получено {got} сообщений за {wall:.2f} с")
    print(f"   процессорное время читателя: {cpu:.3f} с ({cpu / wall:.0%} одного ядра), "
          f"пустых попыток чтения: {empty}")
    print("   ps во время ожидания:")
    for line in ps_out.splitlines():
        print("     " + line)
    return cpu / wall


def main(argv):
    mode = argv[0] if argv else "both"
    if mode not in ("busy", "block", "both"):
        print("использование: poll_demo.py busy|block|both", file=sys.stderr)
        return 2
    if mode == "both":
        # каждый режим в отдельном процессе: %CPU в ps считается за всю жизнь процесса
        for m in ("busy", "block"):
            subprocess.run([sys.executable, __file__, m], check=True)
        return 0
    run(mode)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
