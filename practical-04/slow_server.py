#!/usr/bin/env python3
import time
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer


HOST = "127.0.0.1"
PORT = 8000
DELAY = 0.1


class SlowHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        time.sleep(DELAY)
        super().do_GET()

    def log_message(self, format_string, *arguments):
        pass


def main():
    handler = partial(SlowHandler, directory="web")
    server = ThreadingHTTPServer((HOST, PORT), handler)
    server.daemon_threads = True

    print(
        f"Сервер запущен: http://{HOST}:{PORT}, "
        f"задержка={DELAY} с",
        flush=True,
    )
    print("Для остановки нажми Ctrl+C", flush=True)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nСервер остановлен")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
