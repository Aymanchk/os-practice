#!/usr/bin/env python3
"""ПР-15: клиент калькулятора по TCP.

    ./client.py "2 + 2 * 2" "10 / 4"      по одному выражению на строку ответа
    ./client.py --load 8 "!cpu 5"         8 клиентов одновременно шлют одну команду
"""
import argparse
import socket
import sys
from concurrent.futures import ThreadPoolExecutor


def ask(host, port, lines, timeout=60):
    with socket.create_connection((host, port), timeout=timeout) as s:
        f = s.makefile("rw", encoding="utf-8")
        out = []
        for line in lines:
            f.write(line + "\n")
            f.flush()
            reply = f.readline()
            if not reply:
                out.append("(соединение закрыто сервером)")
                break
            out.append(reply.rstrip("\n"))
        return out


def main(argv):
    p = argparse.ArgumentParser()
    p.add_argument("lines", nargs="+")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--load", type=int, default=0, help="число одновременных клиентов")
    args = p.parse_args(argv)
    try:
        if args.load:
            with ThreadPoolExecutor(args.load) as pool:
                results = list(pool.map(lambda _: ask(args.host, args.port, args.lines), range(args.load)))
            for i, r in enumerate(results, 1):
                print(f"клиент {i}: {r[-1]}")
        else:
            for line, reply in zip(args.lines, ask(args.host, args.port, args.lines)):
                print(f"{line:<20} -> {reply}")
    except OSError as e:
        print(f"ошибка соединения: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
