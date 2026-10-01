#!/usr/bin/env python3
import os
from pathlib import Path


def read_process(pid):
    try:
        lines = Path(f"/proc/{pid}/status").read_text().splitlines()
        fields = {}

        for line in lines:
            if ":" in line:
                key, value = line.split(":", 1)
                fields[key] = value.strip()

        uid = int(fields["Uid"].split()[0])

        if uid != os.getuid():
            return None

        return {
            "pid": pid,
            "ppid": int(fields["PPid"]),
            "name": fields.get("Name", "?"),
            "state": fields.get("State", "?").split()[0],
            "rss": int(fields.get("VmRSS", "0 kB").split()[0]),
        }
    except (OSError, ValueError, KeyError):
        # Процесс мог завершиться, пока мы читали /proc.
        return None


def print_tree(pid, processes, children, indent=""):
    process = processes[pid]

    print(
        f"{indent}PID={process['pid']} "
        f"state={process['state']} "
        f"RSS={process['rss']} kB "
        f"name={process['name']}"
    )

    for child_pid in sorted(children.get(pid, [])):
        print_tree(child_pid, processes, children, indent + "    ")


def main():
    processes = {}

    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue

        process = read_process(int(entry.name))

        if process is not None:
            processes[process["pid"]] = process

    children = {}
    roots = []

    for pid, process in processes.items():
        parent_pid = process["ppid"]

        if parent_pid in processes:
            children.setdefault(parent_pid, []).append(pid)
        else:
            roots.append(pid)

    print(f"Дерево процессов пользователя UID={os.getuid()}")

    for root_pid in sorted(roots):
        print_tree(root_pid, processes, children)


if __name__ == "__main__":
    main()
