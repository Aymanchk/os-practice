#!/usr/bin/env python3
"""Сравнение способов передачи 10^7 чисел между двумя процессами.

Родитель передаёт массив из 10 000 000 чисел int64 (80 000 000 байт)
дочернему процессу четырьмя способами.

Время идёт от начала передачи до сообщения ребёнка "данные получены".
Создание процесса и подготовка массива в это время не входят.
Проверка целостности (SHA-256 от полученных данных) делается уже
после замера: ребёнок присылает хэш, родитель сверяет его с хэшем
исходного массива.
"""
import hashlib
import multiprocessing as mp
import os
import socket
import statistics
import sys
import time
from array import array
from multiprocessing import shared_memory

COUNT = 10_000_000
SIZE = COUNT * 8
CHUNK = 1024 * 1024
REPEATS = 3
FIFO_PATH = "/tmp/pr07_bench.fifo"
SOCKET_PATH = "/tmp/pr07_bench.sock"


def finish(result_conn, data):
    """Сообщает родителю, что данные получены, затем присылает хэш."""
    result_conn.send("получено")
    result_conn.send(hashlib.sha256(data).hexdigest())


def child_pipe(data_conn, result_conn):
    data = data_conn.recv_bytes()
    finish(result_conn, data)


def child_fifo(result_conn):
    buffer = bytearray(SIZE)
    view = memoryview(buffer)
    position = 0
    descriptor = os.open(FIFO_PATH, os.O_RDONLY)

    while position < SIZE:
        count = os.readv(descriptor, [view[position:position + CHUNK]])

        if count == 0:
            break

        position += count

    os.close(descriptor)
    finish(result_conn, view[:position])


def child_socket(result_conn):
    buffer = bytearray(SIZE)
    view = memoryview(buffer)
    position = 0
    connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    connection.connect(SOCKET_PATH)

    while position < SIZE:
        count = connection.recv_into(view[position:position + CHUNK])

        if count == 0:
            break

        position += count

    connection.close()
    finish(result_conn, view[:position])


def attach(name):
    try:
        return shared_memory.SharedMemory(name=name, track=False)
    except TypeError:  # Python до 3.13 не знает параметр track
        return shared_memory.SharedMemory(name=name)


def child_shared_memory(name, ready, result_conn):
    ready.wait()  # синхронизация: ждём, пока родитель допишет данные
    segment = attach(name)
    view = segment.buf[:SIZE]
    finish(result_conn, view)
    view.release()
    segment.close()


def child_shared_memory_warm(name, ready, result_conn):
    segment = attach(name)  # присоединяется заранее, до замера
    result_conn.send("готов")
    ready.wait()  # синхронизация: ждём, пока родитель допишет данные
    view = segment.buf[:SIZE]
    finish(result_conn, view)
    view.release()
    segment.close()


def send_all(descriptor_writer, view):
    for offset in range(0, len(view), CHUNK):
        descriptor_writer(view[offset:offset + CHUNK])


def write_fully(descriptor, block):
    while block:
        written = os.write(descriptor, block)
        block = block[written:]


def measure_pipe(context, view, expected):
    data_parent, data_child = context.Pipe()
    result_parent, result_child = context.Pipe(duplex=False)
    process = context.Process(
        target=child_pipe, args=(data_child, result_child)
    )
    process.start()

    started = time.perf_counter()
    data_parent.send_bytes(view)
    result_parent.recv()  # "получено"
    elapsed = time.perf_counter() - started
    digest = result_parent.recv()

    process.join()
    return elapsed, digest == expected


def measure_fifo(context, view, expected):
    if os.path.exists(FIFO_PATH):
        os.unlink(FIFO_PATH)

    os.mkfifo(FIFO_PATH, 0o600)
    result_parent, result_child = context.Pipe(duplex=False)
    process = context.Process(target=child_fifo, args=(result_child,))
    process.start()

    try:
        descriptor = os.open(FIFO_PATH, os.O_WRONLY)  # ждём читателя
        started = time.perf_counter()
        send_all(lambda block: write_fully(descriptor, block), view)
        os.close(descriptor)  # EOF для читателя
        result_parent.recv()  # "получено"
        elapsed = time.perf_counter() - started
        digest = result_parent.recv()
    finally:
        process.join()
        os.unlink(FIFO_PATH)

    return elapsed, digest == expected


def measure_socket(context, view, expected):
    if os.path.exists(SOCKET_PATH):
        os.unlink(SOCKET_PATH)

    listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    listener.bind(SOCKET_PATH)
    listener.listen(1)
    result_parent, result_child = context.Pipe(duplex=False)
    process = context.Process(target=child_socket, args=(result_child,))
    process.start()

    try:
        connection, _ = listener.accept()
        started = time.perf_counter()
        send_all(connection.sendall, view)
        connection.shutdown(socket.SHUT_WR)
        result_parent.recv()  # "получено"
        elapsed = time.perf_counter() - started
        digest = result_parent.recv()
        connection.close()
    finally:
        process.join()
        listener.close()
        os.unlink(SOCKET_PATH)

    return elapsed, digest == expected


def measure_shared_memory(context, view, expected):
    segment = shared_memory.SharedMemory(create=True, size=SIZE)
    ready = context.Event()
    result_parent, result_child = context.Pipe(duplex=False)
    process = context.Process(
        target=child_shared_memory, args=(segment.name, ready, result_child)
    )
    process.start()

    try:
        started = time.perf_counter()
        segment.buf[:SIZE] = view  # единственное копирование данных
        ready.set()
        result_parent.recv()  # "получено"
        elapsed = time.perf_counter() - started
        digest = result_parent.recv()
    finally:
        process.join()
        segment.close()
        segment.unlink()

    return elapsed, digest == expected


def measure_shared_memory_warm(context, view, expected):
    """Сегмент создан и прогрет заранее, ребёнок уже присоединён."""
    segment = shared_memory.SharedMemory(create=True, size=SIZE)
    segment.buf[:SIZE] = bytes(SIZE)  # страницы выделены до замера
    ready = context.Event()
    result_parent, result_child = context.Pipe(duplex=False)
    process = context.Process(
        target=child_shared_memory_warm,
        args=(segment.name, ready, result_child),
    )
    process.start()

    try:
        result_parent.recv()  # "готов"
        started = time.perf_counter()
        segment.buf[:SIZE] = view
        ready.set()
        result_parent.recv()  # "получено"
        elapsed = time.perf_counter() - started
        digest = result_parent.recv()
    finally:
        process.join()
        segment.close()
        segment.unlink()

    return elapsed, digest == expected


METHODS = [
    ("Pipe (multiprocessing)", "нет, ядро блокирует процессы", measure_pipe),
    ("FIFO", "нет, ядро блокирует процессы", measure_fifo),
    ("Unix-сокет", "нет, ядро блокирует процессы", measure_socket),
    (
        "Разделяемая память, новый сегмент",
        "да, нужен Event или семафор",
        measure_shared_memory,
    ),
    (
        "Разделяемая память, сегмент создан заранее",
        "да, нужен Event или семафор",
        measure_shared_memory_warm,
    ),
]


def main():
    context = mp.get_context("fork")

    print(f"Подготовка массива из {COUNT} чисел...", flush=True)
    numbers = array("q", range(COUNT))
    view = memoryview(numbers).cast("B")
    expected = hashlib.sha256(view).hexdigest()
    print(f"Объём данных: {SIZE} байт ({SIZE / 1_000_000:.0f} МБ)")
    print(f"Повторов каждого способа: {REPEATS}")
    print()

    table = []
    all_ok = True

    for title, sync, measure in METHODS:
        times = []

        for repeat in range(1, REPEATS + 1):
            elapsed, ok = measure(context, view, expected)
            all_ok = all_ok and ok
            times.append(elapsed)
            print(
                f"{title}: повтор {repeat}: {elapsed:.4f} с, "
                f"данные совпали: {ok}",
                flush=True,
            )

        table.append((title, sync, statistics.median(times)))

    print()
    print(
        "| Механизм | Синхронизация со стороны программиста "
        "| Объём данных | Время передачи, с (медиана) | Скорость, МБ/с |"
    )
    print("| --- | --- | ---: | ---: | ---: |")

    for title, sync, median in table:
        speed = SIZE / 1_000_000 / median
        print(
            f"| {title} | {sync} | {SIZE / 1_000_000:.0f} МБ "
            f"| {median:.4f} | {speed:.0f} |"
        )

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
