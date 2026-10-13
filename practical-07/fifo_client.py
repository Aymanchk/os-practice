#!/usr/bin/env python3
"""Клиент вычислений на именованных каналах."""
import os
import sys

from ipc_common import REQUEST_FIFO, RESPONSE_FIFO, open_for_writing


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
    with open(RESPONSE_FIFO, "r", encoding="utf-8") as responses:
        reply = responses.readline().strip()

    print(f"{expression} {reply}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
