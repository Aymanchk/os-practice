#!/usr/bin/env python3
"""Алгоритм банкира: проверка безопасности состояния и обработка запросов."""
import argparse
import sys


def fmt(vector):
    return "(" + ", ".join(str(x) for x in vector) + ")"


def read_state(path):
    """Читает файл с разделами # Available, # Allocation, # Max."""
    sections = {}
    current = None
    with open(path, encoding="utf-8") as f:
        for number, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            if line.startswith("#"):
                name = line[1:].strip().lower()
                if name in ("available", "allocation", "max"):
                    current = name
                    sections[current] = []
                continue
            if current is None:
                raise ValueError(f"{path}:{number}: строка вне раздела")
            sections[current].append([int(x) for x in line.split()])

    for name in ("available", "allocation", "max"):
        if name not in sections:
            raise ValueError(f"{path}: нет раздела {name}")
    if len(sections["available"]) != 1:
        raise ValueError(f"{path}: в разделе Available должна быть одна строка")
    return sections["available"][0], sections["allocation"], sections["max"]


class Banker:
    def __init__(self, available, allocation, maximum):
        self.m = len(available)
        self.n = len(allocation)
        self.available = list(available)
        self.allocation = [list(row) for row in allocation]
        self.maximum = [list(row) for row in maximum]
        self.check_input()

    def check_input(self):
        if len(self.maximum) != self.n:
            raise ValueError("Allocation и Max содержат разное число процессов")
        for i in range(self.n):
            if len(self.allocation[i]) != self.m or len(self.maximum[i]) != self.m:
                raise ValueError(f"у P{i} длина строки не равна {self.m}")
            for j in range(self.m):
                if self.allocation[i][j] < 0 or self.maximum[i][j] < 0:
                    raise ValueError(f"у P{i} есть отрицательное число")
                if self.allocation[i][j] > self.maximum[i][j]:
                    raise ValueError(f"у P{i} Allocation больше Max")
        if any(x < 0 for x in self.available):
            raise ValueError("в Available есть отрицательное число")

    def need(self, i):
        """Need = Max - Allocation для процесса i."""
        return [self.maximum[i][j] - self.allocation[i][j] for j in range(self.m)]

    def need_matrix(self):
        return [self.need(i) for i in range(self.n)]

    def fits(self, i, work):
        return all(n <= w for n, w in zip(self.need(i), work))

    def safe_sequence(self):
        """Алгоритм безопасности. Возвращает список номеров процессов
        или None, если состояние небезопасное."""
        work = list(self.available)
        finish = [False] * self.n
        order = []
        found = True
        while found:
            found = False
            for i in range(self.n):
                if not finish[i] and self.fits(i, work):
                    # процесс "завершился": его ресурсы возвращаются в Work
                    for j in range(self.m):
                        work[j] += self.allocation[i][j]
                    finish[i] = True
                    order.append(i)
                    found = True
        if all(finish):
            return order
        return None

    def is_valid_sequence(self, order):
        """Проверяет, что данная последовательность действительно безопасна."""
        if sorted(order) != list(range(self.n)):
            return False
        work = list(self.available)
        for i in order:
            if not self.fits(i, work):
                return False
            for j in range(self.m):
                work[j] += self.allocation[i][j]
        return True

    def all_safe_sequences(self):
        """Все безопасные последовательности (перебор с возвратом)."""
        result = []

        def go(work, done, order):
            if len(order) == self.n:
                result.append(list(order))
                return
            for i in range(self.n):
                if i not in done and self.fits(i, work):
                    new_work = [work[j] + self.allocation[i][j] for j in range(self.m)]
                    order.append(i)
                    done.add(i)
                    go(new_work, done, order)
                    done.remove(i)
                    order.pop()

        go(list(self.available), set(), [])
        return result

    def request(self, pid, req):
        """Запрос процесса pid на вектор req.
        Возвращает (статус, пояснение). Статусы:
        GRANTED - выдано, состояние безопасное;
        WAIT    - ресурсов сейчас нет, процесс должен ждать;
        UNSAFE  - выдача сделала бы состояние небезопасным, выполнен откат;
        ERROR   - запрос больше, чем процесс заявил в Max."""
        if len(req) != self.m:
            return "ERROR", f"нужно {self.m} чисел в запросе"
        if any(x < 0 for x in req):
            return "ERROR", "в запросе есть отрицательное число"
        need = self.need(pid)
        if any(r > n for r, n in zip(req, need)):
            return "ERROR", f"запрос больше Need = {fmt(need)}"
        if any(r > a for r, a in zip(req, self.available)):
            return "WAIT", f"ресурсов нет, Available = {fmt(self.available)}"

        # пробная выдача, старое состояние запоминаем для отката
        old_available = list(self.available)
        old_row = list(self.allocation[pid])
        for j in range(self.m):
            self.available[j] -= req[j]
            self.allocation[pid][j] += req[j]

        order = self.safe_sequence()
        if order is None:
            self.available = old_available
            self.allocation[pid] = old_row
            return "UNSAFE", "после выдачи состояние стало бы небезопасным, откат"
        return "GRANTED", order

    def show_state(self):
        print("Процесс  Allocation  Max        Need")
        for i in range(self.n):
            print(f"P{i:<7} {fmt(self.allocation[i]):<11} "
                  f"{fmt(self.maximum[i]):<10} {fmt(self.need(i))}")
        print(f"Available = {fmt(self.available)}")


def names(order):
    return " -> ".join(f"P{i}" for i in order)


def parse_request(line):
    parts = line.split()
    pid_text = parts[0].upper().lstrip("P")
    return int(pid_text), [int(x) for x in parts[1:]]


def main():
    parser = argparse.ArgumentParser(description="Алгоритм банкира")
    parser.add_argument("file", help="файл состояния (bank1.txt)")
    parser.add_argument("-r", "--requests", action="store_true",
                        help="читать запросы из stdin, строка: P1 1 0 2")
    parser.add_argument("--all", action="store_true",
                        help="вывести все безопасные последовательности")
    args = parser.parse_args()

    try:
        banker = Banker(*read_state(args.file))
    except (OSError, ValueError) as error:
        print(f"Ошибка во входном файле: {error}")
        return 2

    banker.show_state()
    order = banker.safe_sequence()
    if order is None:
        print("Результат: UNSAFE")
    else:
        print(f"Результат: безопасно, последовательность {names(order)}")
    if args.all:
        everything = banker.all_safe_sequences()
        print(f"Всего безопасных последовательностей: {len(everything)}")
        for seq in everything:
            print("  " + names(seq))

    if args.requests:
        print("\nЗапросы:")
        for line in sys.stdin:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                pid, req = parse_request(line)
                if not 0 <= pid < banker.n:
                    raise ValueError(f"нет процесса P{pid}")
            except ValueError as error:
                print(f"{line}: ошибка разбора ({error})")
                continue
            status, info = banker.request(pid, req)
            head = f"P{pid} просит {fmt(req)}: "
            if status == "GRANTED":
                print(head + f"ВЫДАНО, безопасная последовательность {names(info)}")
            elif status == "WAIT":
                print(head + f"ОТКАЗ, {info}")
            elif status == "UNSAFE":
                print(head + f"ОТКАЗ, {info}")
            else:
                print(head + f"ОШИБКА, {info}")
        print()
        banker.show_state()
    return 0


if __name__ == "__main__":
    sys.exit(main())
