#!/usr/bin/env python3
"""Клиент вычислений на именованных каналах."""
import os
import signal
import sys

from ipc_common import OPEN_TIMEOUT, REQUEST_FIFO, RESPONSE_FIFO, open_for_writing


def on_alarm(signum, frame):
    raise TimeoutError


def main():
    if len(sys.argv) != 2:
        print("Использование: ./fifo_client.py 'выражение'")
        return 2

    expression = sys.argv[1]

    if not os.path.exists(REQUEST_FIFO):
        print("Сервер не запущен: нет файла", REQUEST_FIFO)
        return 1

    try:
        with open_for_writing(REQUEST_FIFO) as requests:
            requests.write(expression + "\n")
    except TimeoutError as error:
        print(f"Сервер не отвечает: {error}")
        return 1

    if expression.strip() == "!stop":
        print("Команда остановки отправлена")
        return 0

    # open() на чтение ждёт, пока сервер откроет канал ответов на запись.
    # Если сервер упал, не ждём вечно: SIGALRM прервёт ожидание.
    signal.signal(signal.SIGALRM, on_alarm)
    signal.alarm(int(OPEN_TIMEOUT))

    try:
        with open(RESPONSE_FIFO, "r", encoding="utf-8") as responses:
            reply = responses.readline().strip()
    except TimeoutError:
        print(f"Сервер не ответил за {OPEN_TIMEOUT:.0f} с")
        return 1
    finally:
        signal.alarm(0)

    print(f"{expression} {reply}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
