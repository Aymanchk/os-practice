#!/usr/bin/env python3
"""Запись в pipe, у которого закрыт читающий конец."""
import os


def main():
    read_end, write_end = os.pipe()
    os.close(read_end)  # читателей больше нет

    try:
        os.write(write_end, b"hello")
    except BrokenPipeError as error:
        print(f"BrokenPipeError: {error}")
        print("Читающих концов нет, запись завершилась ошибкой EPIPE")
        return 0
    finally:
        os.close(write_end)

    print("Ошибки не было")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
