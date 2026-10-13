"""Общие части для работ по синхронизации: кольцевой буфер и журнал нарушений."""
import threading

CAPACITY = 5
PRODUCERS = 3
CONSUMERS = 2
ITEMS = 1000
STOP = "STOP"


class Violations:
    """Потокобезопасный журнал нарушений."""

    def __init__(self):
        self._lock = threading.Lock()
        self._items = []

    def add(self, text):
        with self._lock:
            self._items.append(text)

    def all(self):
        with self._lock:
            return list(self._items)


class Ring:
    """Кольцевой буфер. Сам по себе он не защищён: блокировки ставит
    тот, кто его использует. Буфер только проверяет свои инварианты."""

    def __init__(self, capacity, violations):
        self.capacity = capacity
        self.slots = [None] * capacity
        self.head = 0
        self.tail = 0
        self.count = 0
        self.max_count = 0
        self.violations = violations

    def put(self, item):
        if self.count >= self.capacity:
            self.violations.add(
                f"переполнение: запись {item!r} в полный буфер"
            )
            return False

        self.slots[self.tail] = item
        self.tail = (self.tail + 1) % self.capacity
        self.count += 1
        self.max_count = max(self.max_count, self.count)
        return True

    def get(self):
        if self.count <= 0:
            self.violations.add("опустошение: чтение из пустого буфера")
            return None

        item = self.slots[self.head]
        self.slots[self.head] = None
        self.head = (self.head + 1) % self.capacity
        self.count -= 1
        return item
