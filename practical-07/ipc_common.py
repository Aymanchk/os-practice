"""Общие пути и вспомогательные функции для работы по IPC."""
import errno
import os
import time

REQUEST_FIFO = "/tmp/pr07_request.fifo"
RESPONSE_FIFO = "/tmp/pr07_response.fifo"
SOCKET_PATH = "/tmp/pr07.sock"
OPEN_TIMEOUT = 5.0


def open_for_writing(path, timeout=OPEN_TIMEOUT):
    """Открывает FIFO на запись, но не висит вечно, если читателя нет.

    Обычный open() на запись блокируется, пока другой процесс не откроет
    FIFO на чтение. Здесь ждём не дольше timeout секунд.
    """
    deadline = time.monotonic() + timeout

    while True:
        try:
            descriptor = os.open(path, os.O_WRONLY | os.O_NONBLOCK)
        except OSError as error:
            if error.errno != errno.ENXIO:
                raise

            if time.monotonic() > deadline:
                raise TimeoutError(
                    f"никто не читает {path} уже {timeout:.0f} с"
                ) from None

            time.sleep(0.02)
            continue

        os.set_blocking(descriptor, True)
        return os.fdopen(descriptor, "w", encoding="utf-8")
