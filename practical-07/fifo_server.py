#!/usr/bin/env python3
"""Сервер вычислений на двух именованных каналах (FIFO)."""
import os
import signal
import stat
import sys

from calc import answer
from ipc_common import REQUEST_FIFO, RESPONSE_FIFO, open_for_writing

STOP_COMMAND = "!stop"


def make_fifo(path):
    if os.path.exists(path):
        if not stat.S_ISFIFO(os.stat(path).st_mode):
            raise SystemExit(f"{path} существует и это не FIFO")

        return

    os.mkfifo(path, 0o600)


def remove_fifo(path):
    try:
        os.unlink(path)
    except FileNotFoundError:
        pass


def stop_handler(signum, frame):
    raise SystemExit(0)


def main():
    signal.signal(signal.SIGINT, stop_handler)
    signal.signal(signal.SIGTERM, stop_handler)

    make_fifo(REQUEST_FIFO)
    make_fifo(RESPONSE_FIFO)

    print(f"Сервер FIFO запущен, PID={os.getpid()}", flush=True)
    print(f"Запросы: {REQUEST_FIFO}", flush=True)
    print(f"Ответы: {RESPONSE_FIFO}", flush=True)
    print("Для остановки нажмите Ctrl+C", flush=True)

    try:
        while True:
            # open() ждёт, пока клиент откроет канал на запись.
            with open(REQUEST_FIFO, "r", encoding="utf-8") as requests:
                line = requests.readline().strip()

            if not line:
                continue

            if line == STOP_COMMAND:
                print("Получена команда остановки", flush=True)
                return 0

            reply = answer(line)
            print(f"Запрос: {line} -> {reply}", flush=True)

            try:
                with open_for_writing(RESPONSE_FIFO) as responses:
                    responses.write(reply + "\n")
            except TimeoutError as error:
                print(f"Клиент не забрал ответ: {error}", flush=True)
    finally:
        remove_fifo(REQUEST_FIFO)
        remove_fifo(RESPONSE_FIFO)
        print("Сервер остановлен, FIFO удалены", flush=True)


if __name__ == "__main__":
    sys.exit(main())
