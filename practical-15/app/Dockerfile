# ПР-15: образ сервера-калькулятора (код из ПР-7, TCP-версия).
# Сборка:  docker build -t pr15-calc app
# Запуск:  docker run --rm -d -p 8000:8000 --name calc pr15-calc
FROM python:3.14-slim

# Приложение не должно работать от root: создаём обычного пользователя без пароля
# и без домашнего каталога с правами записи.
RUN useradd --system --no-create-home --shell /usr/sbin/nologin calc

WORKDIR /app
COPY calc.py calc_server.py ./
RUN chmod 0444 calc.py calc_server.py

USER calc
ENV PORT=8000 PYTHONUNBUFFERED=1
EXPOSE 8000

CMD ["python3", "calc_server.py"]
