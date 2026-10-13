#!/usr/bin/env python3
"""Клиент Unix-сокета: отправляет выражения и печатает ответы."""
import os
import socket
import sys

from ipc_common import SOCKET_PATH


def main():
    expressions = sys.argv[1:]

    if not expressions:
        print("Использование: ./socket_client.py 'выражение' ['выражение' ...]")
        return 2

    connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

    try:
        connection.connect(SOCKET_PATH)
    except OSError as error:
        print(f"Не удалось подключиться к {SOCKET_PATH}: {error}")
        return 1

    with connection, connection.makefile("rw", encoding="utf-8") as stream:
        for expression in expressions:
            stream.write(expression + "\n")
            stream.flush()
            reply = stream.readline().strip()
            print(f"клиент PID={os.getpid()}: {expression} {reply}", flush=True)

    return 0


if __name__ == "__main__":
    sys.exit(main())
