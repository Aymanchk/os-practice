#!/usr/bin/env python3
import signal
import time
from functools import partial
from pathlib import Path
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer


HOST = "127.0.0.1"
PORT = 8000
DELAY = 0.1
WEB = Path(__file__).resolve().parent / "web"


class SlowHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        time.sleep(DELAY)
        super().do_GET()

    def log_message(self, format_string, *arguments):
        pass


def stop_handler(signum, frame):
    raise KeyboardInterrupt


def main():
    # kill -TERM останавливает сервер так же аккуратно, как Ctrl+C.
    signal.signal(signal.SIGTERM, stop_handler)
    handler = partial(SlowHandler, directory=str(WEB))
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
