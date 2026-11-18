#!/usr/bin/env python3
"""Проверка ПР-15: образ собирается, сервис отвечает, работает не от root,
лимиты CPU и памяти соблюдаются, контейнеры изолированы. Нужен Docker."""
import re
import subprocess
import sys
import time
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


def sh(*args, timeout=300):
    return subprocess.run([str(a) for a in args], capture_output=True, text=True, timeout=timeout)


def client(port, *lines):
    return sh(sys.executable, HERE / "client.py", "--port", port, *lines).stdout


def run_calc(name, *opts):
    """Запуск контейнера, порт на хосте выбирает Docker (не будет конфликта занятых портов)."""
    sh("docker", "run", "-d", "--name", name, *opts, "-p", "127.0.0.1::8000", "pr15-calc")
    return int(sh("docker", "port", name, "8000").stdout.split(":")[-1])


def wait_port(port):
    for _ in range(100):
        r = sh(sys.executable, HERE / "client.py", "--port", port, "1 + 1")
        if "= 2" in r.stdout:
            return True
        time.sleep(0.1)
    return False


names = ("chk-calc", "chk-lim", "chk-b")
sh("docker", "rm", "-f", *names)
try:
    b = sh("docker", "build", "-q", "-t", "pr15-calc", HERE / "app")
    check("docker build собирает образ из app/Dockerfile", b.returncode == 0)

    p1 = run_calc("chk-calc")
    check(f"контейнер с пробросом порта {p1} -> 8000 отвечает", wait_port(p1))
    out = client(p1, "2 + 2 * 2", "1 / 0", "__import__('os')")
    check("калькулятор считает и отклоняет опасный ввод (как в ПР-7)",
          "= 6" in out and "деление на ноль" in out and "недопустимое" in out)
    uid = sh("docker", "exec", "chk-calc", "id", "-u").stdout.strip()
    check(f"процесс в контейнере не root (UID {uid})", uid not in ("", "0"))
    check("в образе нельзя писать в код приложения",
          sh("docker", "exec", "chk-calc", "sh", "-c", "echo x >> /app/calc.py").returncode != 0)

    p2 = run_calc("chk-lim", "--cpus=0.5", "--memory=128m", "--memory-swap=128m")
    wait_port(p2)
    check("cgroup: cpu.max = 50000 100000, memory.max = 128 МБ",
          sh("docker", "exec", "chk-lim", "cat", "/sys/fs/cgroup/cpu.max").stdout.split() == ["50000", "100000"]
          and sh("docker", "exec", "chk-lim", "cat", "/sys/fs/cgroup/memory.max").stdout.strip() == str(128 << 20))
    load = subprocess.Popen([sys.executable, HERE / "client.py", "--port", str(p2), "--load", "4", "!cpu 6"],
                            stdout=subprocess.DEVNULL)
    time.sleep(3)
    cpu = sh("docker", "stats", "--no-stream", "--format", "{{.CPUPerc}}", "chk-lim").stdout.strip().rstrip("%")
    load.wait()
    check(f"под нагрузкой из 4 клиентов CPU упирается в лимит 50% (было {cpu}%)", 30 < float(cpu) < 60)
    check("64 МБ в пределах лимита занимаются", "занято 64 МБ" in client(p2, "!mem 64"))
    oom = client(p2, "!mem 300")
    events = sh("docker", "exec", "chk-lim", "cat", "/sys/fs/cgroup/memory.events").stdout
    check("300 МБ больше лимита: обработчик убит OOM (oom_kill >= 1)",
          "закрыто" in oom and int(re.search(r"oom_kill (\d+)", events).group(1)) >= 1)
    check("после OOM сервер продолжает работать", "= 42" in client(p2, "6 * 7"))

    sh("docker", "run", "-d", "--name", "chk-b", "pr15-calc")
    time.sleep(1)
    pids = sh("docker", "exec", "chk-calc", "sh", "-c", "ls -d /proc/[0-9]*").stdout.split()
    check(f"контейнер видит только свои процессы: {len(pids)} (сервер и сама команда проверки)", len(pids) <= 4)
    ns = {c: sh("docker", "exec", c, "readlink", "/proc/1/ns/pid", "/proc/1/ns/net", "/proc/1/ns/mnt").stdout
          for c in ("chk-calc", "chk-b")}
    check("у двух контейнеров разные пространства имён PID, net и mnt",
          all(a != b for a, b in zip(ns["chk-calc"].split(), ns["chk-b"].split())))
    check("PID 1 в контейнере - сервер калькулятора",
          "calc_server.py" in sh("docker", "exec", "chk-calc", "cat", "/proc/1/cmdline").stdout)
finally:
    sh("docker", "rm", "-f", *names)

print()
print(f"Проверок: {total}, провалено: {failed}")
sys.exit(1 if failed else 0)
