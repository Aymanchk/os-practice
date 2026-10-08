#!/usr/bin/env python3
from pathlib import Path

# Файлы создаются рядом со скриптом, из какой бы папки его ни запустили.
HERE = Path(__file__).resolve().parent

NUMBER_COUNT = 10_000_000
BLOCK_SIZE = 100_000
URL_COUNT = 20
WEB_FILE_SIZE = 65_536


def generate_numbers():
    path = HERE / "numbers.txt"

    with path.open("w", encoding="utf-8", buffering=1024 * 1024) as output:
        for start in range(0, NUMBER_COUNT, BLOCK_SIZE):
            end = min(start + BLOCK_SIZE, NUMBER_COUNT)
            block = "".join(f"{index % 1000}\n" for index in range(start, end))
            output.write(block)

    print(f"Создан {path.name}: {NUMBER_COUNT} чисел")


def generate_web_data():
    web_directory = HERE / "web"
    web_directory.mkdir(exist_ok=True)

    urls = []

    for number in range(1, URL_COUNT + 1):
        path = web_directory / f"file{number:02d}.txt"
        header = f"file {number:02d}\n".encode("utf-8")
        payload = bytes([65 + number % 26]) * WEB_FILE_SIZE
        path.write_bytes(header + payload)

        urls.append(f"http://127.0.0.1:8000/{path.name}")

    (HERE / "urls.txt").write_text(
        "\n".join(urls) + "\n",
        encoding="utf-8",
    )

    print(f"Создано {URL_COUNT} файлов в каталоге web")
    print("Создан urls.txt с 20 адресами")


def main():
    generate_numbers()
    generate_web_data()


if __name__ == "__main__":
    main()
