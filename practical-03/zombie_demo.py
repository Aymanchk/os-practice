#!/usr/bin/env python3
import os
import subprocess
import time
from pathlib import Path


def main():
    child_pid = os.fork()

    if child_pid == 0:
        print(
            f"Ребёнок PID={os.getpid()} завершается",
            flush=True,
        )
        os._exit(0)

    print(
        f"Родитель PID={os.getpid()}, ребёнок PID={child_pid}",
        flush=True,
    )

    time.sleep(1)

    print("\nДо waitpid ребёнок находится в состоянии зомби:")
    subprocess.run(
        [
            "ps",
            "-o",
            "pid,ppid,state,stat,cmd",
            "-p",
            str(child_pid),
        ],
        check=False,
    )

    waited_pid, status = os.waitpid(child_pid, 0)
    exit_code = os.waitstatus_to_exitcode(status)

    print(
        f"\nwaitpid получил PID={waited_pid}, код={exit_code}"
    )
    print(
        f"/proc/{child_pid} существует после waitpid: "
        f"{Path(f'/proc/{child_pid}').exists()}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
