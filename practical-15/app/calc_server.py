#!/usr/bin/env python3
"""ПР-15: сервер-калькулятор из ПР-7, переделанный с Unix-сокета на TCP, чтобы его
можно было запустить в контейнере и пробросить порт.

Протокол строковый, как в ПР-7: клиент шлёт выражение, сервер отвечает строкой.
Каждое подключение обслуживает отдельный процесс (fork).

Две служебные команды для нагрузочных опытов ПР-15:
    !cpu S    крутить процессор S секунд (до 30)
    !mem M    занять M МБ памяти на 3 секунды (до 2048)
"""
import os
import socketserver
import sys
import time

from calc import answer

PORT = int(os.environ.get("PORT", "8000"))


def busy(seconds):
    end = time.monotonic() + seconds
    n = 0
    while time.monotonic() < end:
        n += 1
    return f"cpu: {n} итераций за {seconds} с"


def hold_memory(mb):
    block = bytearray(mb * 1024 * 1024)
    for i in range(0, len(block), 4096):     # реально затронуть каждую страницу
        block[i] = 1
    time.sleep(3)
    return f"mem: занято {mb} МБ на 3 с"


class Handler(socketserver.StreamRequestHandler):
    def handle(self):
        peer = f"{self.client_address[0]}:{self.client_address[1]}"
        print(f"подключение {peer}, обслуживает PID {os.getpid()}", flush=True)
        for raw in self.rfile:
            line = raw.decode("utf-8", "replace").strip()
            if not line:
                continue
            try:
                if line.startswith("!cpu "):
                    reply = busy(min(float(line.split()[1]), 30))
                elif line.startswith("!mem "):
                    reply = hold_memory(min(int(line.split()[1]), 2048))
                else:
                    reply = answer(line)
            except (ValueError, IndexError):
                reply = "ошибка: неверная служебная команда"
            print(f"{peer}: {line} -> {reply}", flush=True)
            self.wfile.write((reply + "\n").encode("utf-8"))


class Server(socketserver.ForkingTCPServer):
    allow_reuse_address = True


def main():
    with Server(("0.0.0.0", PORT), Handler) as srv:
        print(f"калькулятор слушает порт {PORT}, PID {os.getpid()}, UID {os.getuid()}", flush=True)
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
