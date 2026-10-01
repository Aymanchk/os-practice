#!/usr/bin/env python3
import os
import subprocess
import time
from pathlib import Path


def process_name(pid):
    try:
        return Path(f"/proc/{pid}/comm").read_text().strip()
    except OSError:
        return "неизвестно"


def main():
    read_fd, write_fd = os.pipe()
    intermediate_pid = os.fork()

    if intermediate_pid == 0:
        os.close(read_fd)

        original_parent = os.getpid()
        orphan_pid = os.fork()

        if orphan_pid == 0:
            time.sleep(1)

            new_parent = os.getppid()
            adopter_name = process_name(new_parent)

            print(
                f"\nРебёнок PID={os.getpid()}",
                flush=True,
            )
            print(
                f"Первоначальный PPID={original_parent}",
                flush=True,
            )
            print(
                f"Новый PPID={new_parent}, "
                f"имя усыновителя={adopter_name}",
                flush=True,
            )

            subprocess.run(
                [
                    "ps",
                    "-o",
                    "pid,ppid,state,stat,cmd",
                    "-p",
                    str(new_parent),
                    "-p",
                    str(os.getpid()),
                ],
                check=False,
            )

            os.close(write_fd)
            os._exit(0)

        print(
            f"Промежуточный родитель PID={original_parent} "
            f"создал ребёнка PID={orphan_pid} и завершается",
            flush=True,
        )

        os.close(write_fd)
        os._exit(0)

    os.close(write_fd)
    os.waitpid(intermediate_pid, 0)

    # Чтение закончится только после завершения осиротевшего ребёнка.
    while os.read(read_fd, 1024):
        pass

    os.close(read_fd)
    print("\nДемонстрация сироты завершена")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
