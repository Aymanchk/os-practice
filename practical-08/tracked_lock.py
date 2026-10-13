"""TrackedLock: обёртка над threading.Lock с графом ожидания в реальном времени.

Если поток собирается заснуть на блокировке и это замыкает цикл в графе
ожидания, вместо зависания бросается DeadlockError."""
import threading

from waitgraph import find_cycle


class DeadlockError(RuntimeError):
    """Цикл ожидания: описание лежит в тексте исключения."""


# Одна общая Condition защищает весь граф и заодно служит для ожидания.
# Проверка цикла и засыпание делаются под ней, поэтому между ними никто
# не успеет изменить граф.
_cv = threading.Condition()
_waiting = {}   # id потока -> блокировка, которую он ждёт
_names = {}     # id потока -> имя для сообщений


def _chain_text(cycle):
    parts = []
    for tid in cycle:
        lock = _waiting[tid]
        parts.append(f"{_names[tid]} ждёт {lock.name} (держит {_names[lock.owner]})")
    return "; ".join(parts)


class TrackedLock:
    def __init__(self, name):
        self.name = name
        self._lock = threading.Lock()
        self.owner = None

    def acquire(self):
        me = threading.get_ident()
        with _cv:
            _names[me] = threading.current_thread().name
            while True:
                if self._lock.acquire(blocking=False):
                    self.owner = me
                    _waiting.pop(me, None)
                    return True
                _waiting[me] = self
                graph = {tid: {lock.owner} for tid, lock in _waiting.items()
                         if lock.owner is not None}
                cycle = find_cycle(graph)
                if cycle:
                    text = _chain_text(cycle)
                    del _waiting[me]
                    raise DeadlockError("взаимоблокировка: " + text)
                # ждём, пока кто-нибудь освободит какую-нибудь блокировку,
                # и пробуем снова: поэтому ожидание стоит в цикле while
                _cv.wait()

    def release(self):
        with _cv:
            if self.owner != threading.get_ident():
                raise RuntimeError(f"поток не держит блокировку {self.name}")
            self.owner = None
            self._lock.release()
            _cv.notify_all()

    def locked(self):
        return self._lock.locked()

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.release()
        return False
