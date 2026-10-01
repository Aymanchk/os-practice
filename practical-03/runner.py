#!/usr/bin/env python3
import os
import shlex
import sys
import time


def usage():
    print(
        f"Использование: {sys.argv[0]} N команда [аргументы...]",
        file=sys.stderr,
    )


def main():
    if len(sys.argv) < 3:
        usage()
        return 1

    try:
        count = int(sys.argv[1])
    except ValueError:
        print("Ошибка: N должно быть целым числом", file=sys.stderr)
        usage()
        return 1

    if count <= 0:
        print("Ошибка: N должно быть больше нуля", file=sys.stderr)
        usage()
        return 1

    command = sys.argv[2:]
    children = {}

    print(f"Команда: {shlex.join(command)}")
    print(f"Количество процессов: {count}")

    for number in range(1, count + 1):
        started = time.monotonic()
        pid = os.fork()

        if pid == 0:
            try:
                os.execvp(command[0], command)
            except OSError as error:
                print(
                    f"Ошибка exec: {error}",
                    file=sys.stderr,
                    flush=True,
                )
                os._exit(127)

        children[pid] = {
            "number": number,
            "started": started,
        }

        print(f"Создан процесс {number}: PID={pid}")

    remaining = set(children)

    while remaining:
        pid, status = os.wait()
        finished = time.monotonic()
        information = children[pid]
        exit_code = os.waitstatus_to_exitcode(status)
        elapsed = finished - information["started"]

        print(
            f"Процесс {information['number']}: "
            f"PID={pid}, "
            f"код={exit_code}, "
            f"время={elapsed:.3f} с"
        )

        remaining.remove(pid)

    print("Все дочерние процессы завершены")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
