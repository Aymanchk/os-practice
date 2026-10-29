#!/usr/bin/env python3
"""Полный отчёт по Проекту 1: блоки A, B, C.

Автор: Эркинбеков Айман

Запуск:  python3 report.py
Печатает все таблицы в консоль и сохраняет:
  results/report.md      : отчёт с таблицами и диаграммами Ганта
  results/gantt_*.svg    : диаграммы Ганта картинками (открываются в браузере)
"""
import os
import sys

import scheduler as s
from selfcheck import run_checks

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
OUT = os.path.join(HERE, "results")

LONG_BURST = 30          # задачи с burst >= 30 считаем "длинными расчётами"
RR_BEST_Q = 2            # квант, который рекомендуем заказчику (обоснование в README)
AGING_STEP = 5           # основной шаг старения для блока C
MLFQ_QUANTA = (2, 4, 8)  # кванты трёх уровней MLFQ
MLFQ_BOOST = 50          # период boost

PALETTE = ["#4e79a7", "#f28e2b", "#e15759", "#76b7b2", "#59a14f", "#edc948",
           "#b07aa1", "#ff9da7", "#9c755f", "#bab0ac"]

lines = []


def out(text: str = "") -> None:
    print(text)
    lines.append(text)


def load(name: str):
    return s.load(os.path.join(DATA, name))


def gantt_block(res: s.Result) -> None:
    out("```text")
    out(s.gantt_text(res))
    out("```")


def svg_gantt(results, filename: str, title: str) -> str:
    """Рисует диаграммы Ганта нескольких алгоритмов в один SVG (только стандартная библиотека)."""
    end = max(r.makespan for r in results)
    left, right, row_h, top = 190, 20, 34, 40
    width = 1100
    unit = (width - left - right) / end
    height = top + row_h * len(results) + 40
    pids = sorted({p.pid for r in results for p in r.procs}, key=lambda x: s.Process(x, 0, 1, 0).num)
    color = {pid: PALETTE[i % len(PALETTE)] for i, pid in enumerate(pids)}
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
             f'font-family="Arial, sans-serif" font-size="12">',
             f'<rect width="100%" height="100%" fill="white"/>',
             f'<text x="10" y="22" font-size="16" font-weight="bold">{title}</text>']
    for row, r in enumerate(results):
        y = top + row * row_h
        parts.append(f'<text x="10" y="{y + 21}" font-weight="bold">{r.name}</text>')
        for pid, a, b in r.gantt:
            x, w = left + a * unit, (b - a) * unit
            fill = color[pid] if pid else "#eeeeee"
            parts.append(f'<rect x="{x:.1f}" y="{y}" width="{w:.1f}" height="26" fill="{fill}" stroke="white"/>')
            if pid and w >= 18:
                parts.append(f'<text x="{x + w / 2:.1f}" y="{y + 17}" text-anchor="middle" fill="white">{pid}</text>')
    axis_y = top + row_h * len(results) + 4
    step = max(1, round(end / 20))
    for t in range(0, end + 1, step):
        x = left + t * unit
        parts.append(f'<line x1="{x:.1f}" y1="{top - 4}" x2="{x:.1f}" y2="{axis_y}" stroke="#ccc" stroke-width="0.5"/>')
        parts.append(f'<text x="{x:.1f}" y="{axis_y + 14}" text-anchor="middle" fill="#555">{t}</text>')
    parts.append("</svg>")
    path = os.path.join(OUT, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(parts))
    return path


def summary_row(r: s.Result, short=None, long_=None) -> str:
    row = (f"| {r.name} | {s.fmt(r.avg_waiting())} | {s.fmt(r.avg_turnaround())} | "
           f"{s.fmt(r.avg_response())} | {r.switches} |")
    if short is not None:
        row += (f" {s.fmt(r.avg_waiting(short))} | {max(r.waiting(p) for p in short)} | "
                f"{', '.join(str(r.finish[p.pid]) for p in long_)} |")
    return row


SUMMARY_HEAD = ("| Алгоритм | Ср. ожидание | Ср. оборот | Ср. отклик | Переключений |",
                "| --- | --: | --: | --: | --: |")
MIXED_HEAD = ("| Алгоритм | Ср. ожидание | Ср. оборот | Ср. отклик | Переключений "
              "| Ожидание коротких (ср.) | Ожидание коротких (макс.) | Завершение длинных P1, P3, P4 |",
              "| --- | --: | --: | --: | --: | --: | --: | --: |")


# ======================================================================= A

def block_a() -> None:
    jobs = load("jobs.txt")
    out("# Проект 1. Планировщик учебного сервера, отчёт")
    out()
    out("Отчёт создан автоматически командой `python3 report.py`.")
    out()
    out("## Блок A. Базовый")
    out()
    out("### A1. FCFS для jobs.txt")
    r = s.fcfs(jobs)
    svg_gantt([r], "gantt_fcfs_jobs.svg", "jobs.txt: FCFS")
    gantt_block(r)
    out(s.process_table(r))
    out()

    out("### A2. FCFS, SJF и RR q=2 для jobs.txt")
    results = [s.fcfs(jobs), s.sjf(jobs), s.rr(jobs, 2)]
    for r in results[1:]:
        out(f"**{r.name}**")
        out()
        gantt_block(r)
        out(s.process_table(r))
        out()
    svg_gantt(results, "gantt_jobs_A.svg", "jobs.txt: FCFS, SJF, RR q=2")

    out("### A3. Самопроверка на set1.txt")
    out("| Алгоритм | Ожидание (код) | Ожидание (эталон) | Оборот (код) | Оборот (эталон) | Итог |")
    out("| --- | --: | --: | --: | --: | :-: |")
    for name, w, ew, t, et, ok in run_checks():
        out(f"| {name} | {s.fmt(w)} | {s.fmt(ew)} | {s.fmt(t)} | {s.fmt(et)} | {'OK' if ok else 'ОШИБКА'} |")
    out()

    out("### A4. Сравнение на jobs.txt")
    out("| Алгоритм | Ср. ожидание | Ср. оборот |")
    out("| --- | --: | --: |")
    for r in results:
        out(f"| {r.name} | {s.fmt(r.avg_waiting())} | {s.fmt(r.avg_turnaround())} |")
    best = min(results, key=lambda x: x.avg_waiting())
    out()
    out(f"Лучший по среднему ожиданию и обороту: **{best.name}** "
        f"({s.fmt(best.avg_waiting())} и {s.fmt(best.avg_turnaround())}).")
    out()


# ======================================================================= B

def block_b() -> None:
    jobs = load("jobs.txt")
    mixed = load("mixed.txt")
    short = [p for p in mixed if p.burst < LONG_BURST]
    long_ = [p for p in mixed if p.burst >= LONG_BURST]

    out("## Блок B. Основной")
    out()
    out("### B1. SRTF и Priority (вытесняющий) для jobs.txt")
    for r in (s.srtf(jobs), s.priority(jobs)):
        out(f"**{r.name}**")
        out()
        gantt_block(r)
        out(s.process_table(r))
        out()
    five_jobs = [s.fcfs(jobs), s.sjf(jobs), s.rr(jobs, 2), s.srtf(jobs), s.priority(jobs)]
    out("Все пять алгоритмов на jobs.txt:")
    out()
    out(SUMMARY_HEAD[0])
    out(SUMMARY_HEAD[1])
    for r in five_jobs:
        out(summary_row(r))
    out()

    out(f"### B2. Все 5 алгоритмов на mixed.txt ({len(long_)} длинных, {len(short)} коротких)")
    five = [s.fcfs(mixed), s.sjf(mixed), s.rr(mixed, 2), s.srtf(mixed), s.priority(mixed)]
    out(MIXED_HEAD[0])
    out(MIXED_HEAD[1])
    for r in five:
        out(summary_row(r, short, long_))
    out()

    out("### B3. RR на mixed.txt при кванте от 1 до 10")
    out("| Квант | Ср. ожидание | Ср. отклик | Переключений | Ожидание коротких (ср.) |")
    out("| --: | --: | --: | --: | --: |")
    for q in range(1, 11):
        r = s.rr(mixed, q)
        out(f"| {q} | {s.fmt(r.avg_waiting())} | {s.fmt(r.avg_response())} | {r.switches} | "
            f"{s.fmt(r.avg_waiting(short))} |")
    out()

    out("### B4. Рекомендация заказчику")
    r1, r2, r4 = s.rr(mixed, 1), s.rr(mixed, RR_BEST_Q), s.rr(mixed, 4)
    out(f"* Из пяти алгоритмов в жизни можно применить **RR q={RR_BEST_Q}**: ему не нужно знать "
        f"длительность задач заранее, и никто не голодает.")
    out(f"* q=1 даёт отклик {s.fmt(r1.avg_response())} вместо {s.fmt(r2.avg_response())}, но "
        f"переключений {r1.switches} вместо {r2.switches} (почти вдвое больше накладных расходов).")
    out(f"* q=4 уже хуже по отклику ({s.fmt(r4.avg_response())}) и ожиданию коротких "
        f"({s.fmt(r4.avg_waiting(short))} против {s.fmt(r2.avg_waiting(short))}).")
    out("* SRTF и Priority по числам лучше, но SRTF требует знать burst заранее, "
        "а Priority морит голодом задачи с низким приоритетом (см. блок C1).")
    out()


# ======================================================================= C

def block_c() -> None:
    starve = load("starve.txt")
    mixed = load("mixed.txt")
    short = [p for p in mixed if p.burst < LONG_BURST]
    long_ = [p for p in mixed if p.burst >= LONG_BURST]

    out("## Блок C. Продвинутый")
    out()
    out("### C1. Голодание P1 в Priority на starve.txt")
    r = s.priority(starve)
    p1 = next(p for p in starve if p.pid == "P1")
    out(f"P1 (приоритет {p1.priority}, burst {p1.burst}) пришёл в момент {p1.arrival}, "
        f"**стартует в {r.first_start['P1']}**, **завершается в {r.finish['P1']}**, "
        f"ждал {r.waiting(p1)} единиц. Всё это время процессор занимали задачи с приоритетом 1-3.")
    out()
    out("```text")
    out(s.gantt_compact(r))
    out("```")
    out()

    out(f"### C2. Старение: приоритет улучшается на 1 за каждые N единиц ожидания")
    out("| Шаг N | Старт P1 | Завершение P1 | Ожидание P1 | Раньше, чем без старения | Ср. ожидание всех |")
    out("| --- | --: | --: | --: | --: | --: |")
    base = r.first_start["P1"]
    out(f"| без старения | {base} | {r.finish['P1']} | {r.waiting(p1)} | 0 | {s.fmt(r.avg_waiting())} |")
    for step in (2, 3, 4, 5, 6, 8, 10):
        a = s.priority_aging(starve, step)
        out(f"| {step} | {a.first_start['P1']} | {a.finish['P1']} | {a.waiting(p1)} | "
            f"{base - a.first_start['P1']} | {s.fmt(a.avg_waiting())} |")
    a = s.priority_aging(starve, AGING_STEP)
    out()
    out(f"При шаге {AGING_STEP} P1 стартует в {a.first_start['P1']} вместо {base}, "
        f"то есть на **{base - a.first_start['P1']}** единиц раньше.")
    out()
    svg_gantt([r, a], "gantt_starve.svg", "starve.txt: Priority без старения и со старением")

    out(f"### C3. MLFQ: 3 уровня, кванты {'/'.join(map(str, MLFQ_QUANTA))}, boost каждые {MLFQ_BOOST}")
    m = s.mlfq(mixed, MLFQ_QUANTA, MLFQ_BOOST)
    out(MIXED_HEAD[0])
    out(MIXED_HEAD[1])
    for res in (s.srtf(mixed), s.rr(mixed, RR_BEST_Q), m):
        out(summary_row(res, short, long_))
    out()
    out("Влияние периода boost (те же кванты):")
    out()
    out(MIXED_HEAD[0])
    out(MIXED_HEAD[1])
    for b in (0, 20, 30, 50, 100):
        out(summary_row(s.mlfq(mixed, MLFQ_QUANTA, b), short, long_))
    out()
    svg_gantt([s.srtf(mixed), s.rr(mixed, RR_BEST_Q), m], "gantt_mixed_mlfq.svg",
              "mixed.txt: SRTF, RR и MLFQ")

    out("### C4. Почему MLFQ работает без знания длительности задач")
    out("MLFQ не спрашивает burst, он смотрит на поведение процесса. Каждый новый процесс "
        "считается коротким и попадает на верхний уровень с маленьким квантом. Короткий запрос "
        "успевает завершиться за первый квант, как в SJF. Длинный расчёт съедает квант целиком "
        "и опускается ниже, где квант больше и переключений меньше. Так очередь сама сортирует "
        "задачи по длительности. Boost периодически поднимает всех наверх, поэтому длинные задачи "
        "не голодают.")
    out()


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    os.makedirs(OUT, exist_ok=True)
    block_a()
    block_b()
    block_c()
    path = os.path.join(OUT, "report.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"\nОтчёт сохранён: {os.path.relpath(path, HERE)}; диаграммы: results/gantt_*.svg")
    return 0


if __name__ == "__main__":
    sys.exit(main())
