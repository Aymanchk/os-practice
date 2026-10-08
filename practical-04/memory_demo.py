#!/usr/bin/env python3
import multiprocessing as mp
import os
import threading


GLOBAL_LIST = ["parent"]


def thread_worker():
    GLOBAL_LIST.append("thread")
    print(
        f"Поток PID={os.getpid()}: {GLOBAL_LIST}",
        flush=True,
    )


def process_worker():
    GLOBAL_LIST.append("process")
    print(
        f"Дочерний процесс PID={os.getpid()}: {GLOBAL_LIST}",
        flush=True,
    )


def main():
    print(
        f"Родитель до запуска PID={os.getpid()}: {GLOBAL_LIST}",
        flush=True,
    )

    thread = threading.Thread(target=thread_worker)
    thread.start()
    thread.join()

    print(
        f"Родитель после потока: {GLOBAL_LIST}",
        flush=True,
    )

    context = mp.get_context("fork")
    process = context.Process(target=process_worker)
    process.start()
    process.join()

    print(
        f"Родитель после процесса: {GLOBAL_LIST}",
        flush=True,
    )
    print(f"Код дочернего процесса: {process.exitcode}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
