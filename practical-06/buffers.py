"""Две реализации ограниченного буфера без queue.Queue."""
import threading

from common import Ring


class SemaphoreBuffer:
    """Два семафора считают места, мьютекс защищает сам буфер."""

    def __init__(self, capacity, violations):
        self.ring = Ring(capacity, violations)
        self.empty = threading.Semaphore(capacity)
        self.full = threading.Semaphore(0)
        self.mutex = threading.Lock()

    def put(self, item):
        self.empty.acquire()

        with self.mutex:
            self.ring.put(item)

        self.full.release()

    def get(self):
        self.full.acquire()

        with self.mutex:
            item = self.ring.get()

        self.empty.release()
        return item


class ConditionBuffer:
    """Один мьютекс и две условные переменные на нём."""

    def __init__(self, capacity, violations):
        self.ring = Ring(capacity, violations)
        self.lock = threading.Lock()
        self.not_full = threading.Condition(self.lock)
        self.not_empty = threading.Condition(self.lock)

    def put(self, item):
        with self.not_full:
            while self.ring.count == self.ring.capacity:
                self.not_full.wait()

            self.ring.put(item)
            self.not_empty.notify()

    def get(self):
        with self.not_empty:
            while self.ring.count == 0:
                self.not_empty.wait()

            item = self.ring.get()
            self.not_full.notify()
            return item
