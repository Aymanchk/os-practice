#!/usr/bin/env python3
import sys


def main():
    if len(sys.argv) != 2:
        print("Использование: python3 hello.py <файл>", file=sys.stderr)
        return 1

    size = 0

    try:
        with open(sys.argv[1], "rb") as source:
            while True:
                block = source.read(65536)
                if not block:
                    break
                size += len(block)
    except OSError as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return 1

    print(f"Размер: {size} байт")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
