#!/usr/bin/env python3
"""Сервер вычислений на Unix-сокете. Каждый клиент обслуживается в потоке."""
import os
import signal
import socket
import socketserver
import struct
import sys
import time

from calc import answer
from ipc_common import SOCKET_PATH

WORK_DELAY = 0.3  # имитация долгого вычисления, чтобы была видна параллельность


class Handler(socketserver.StreamRequestHandler):
    def handle(self):
        creds = self.request.getsockopt(
            socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i")
        )
        client_pid = struct.unpack("3i", creds)[0]
        print(f"Клиент PID={client_pid} подключился", flush=True)

        for raw in self.rfile:
            line = raw.decode("utf-8").strip()

            if not line:
                continue

            time.sleep(WORK_DELAY)
            reply = answer(line)
            print(f"PID={client_pid}: {line} -> {reply}", flush=True)
            self.wfile.write((reply + "\n").encode("utf-8"))

        print(f"Клиент PID={client_pid} отключился", flush=True)


class Server(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    daemon_threads = True


def stop_handler(signum, frame):
    raise KeyboardInterrupt


def remove_stale_socket():
    if not os.path.exists(SOCKET_PATH):
        return

    probe = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

    try:
        probe.connect(SOCKET_PATH)
    except OSError:
        os.unlink(SOCKET_PATH)  # от старого сервера остался файл
    else:
        raise SystemExit("Сервер уже запущен")
    finally:
        probe.close()


def main():
    signal.signal(signal.SIGTERM, stop_handler)
    remove_stale_socket()

    server = Server(SOCKET_PATH, Handler)
    print(f"Сервер сокета запущен, PID={os.getpid()}", flush=True)
    print(f"Сокет: {SOCKET_PATH}", flush=True)
    print("Для остановки нажмите Ctrl+C", flush=True)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

        try:
            os.unlink(SOCKET_PATH)
        except FileNotFoundError:
            pass

        print("Сервер остановлен, сокет удалён", flush=True)

    return 0


if __name__ == "__main__":
    sys.exit(main())
