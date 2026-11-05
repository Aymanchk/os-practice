/* Тесты аллокатора: разбиение, слияние, стратегии, realloc, детектор, случайная нагрузка. */
#define _DEFAULT_SOURCE
#include "myalloc.h"

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static int total = 0, failed = 0;

static void check(const char *name, int ok)
{
    total++;
    if (ok) {
        printf("[ok]     %s\n", name);
    } else {
        failed++;
        printf("[ОШИБКА] %s\n", name);
    }
}

static uint64_t rng_state = 12345;
static uint64_t rnd(void)                 /* xorshift64: одинаковые числа при каждом запуске */
{
    rng_state ^= rng_state << 13;
    rng_state ^= rng_state >> 7;
    rng_state ^= rng_state << 17;
    return rng_state;
}

/* Перенаправляет stderr в /dev/null на время теста с намеренными ошибками. */
static int quiet_begin(void)
{
    fflush(stderr);
    int saved = dup(2);
    FILE *null = fopen("/dev/null", "w");
    if (null) {
        dup2(fileno(null), 2);
        fclose(null);
    }
    return saved;
}

static void quiet_end(int saved)
{
    fflush(stderr);
    dup2(saved, 2);
    close(saved);
}

static void test_basic(void)
{
    my_stats_t st;
    char *a = my_malloc(100);
    char *b = my_malloc(1);
    char *c = my_malloc(4000);
    check("my_malloc возвращает адреса, выровненные по 16 байт",
          a && b && c && (uintptr_t)a % 16 == 0 && (uintptr_t)b % 16 == 0 && (uintptr_t)c % 16 == 0);
    memset(a, 'a', 100);
    memset(b, 'b', 1);
    memset(c, 'c', 4000);
    check("блоки не перекрываются (данные не испортились)", a[99] == 'a' && b[0] == 'b' && c[0] == 'c');
    my_stats(&st);
    check("три занятых блока и один свободный остаток (разбиение)",
          st.used_blocks == 3 && st.free_blocks == 1);
    my_free(b);
    my_stats(&st);
    check("после free среднего блока свободных блоков два (соседи заняты)", st.free_blocks == 2);
    my_free(a);
    my_stats(&st);
    check("после free левого блока он слился с соседом: свободных опять два", st.free_blocks == 2);
    my_free(c);
    my_stats(&st);
    check("после free всех блоков снова один свободный блок на весь регион (слияние)",
          st.free_blocks == 1 && st.used_blocks == 0 && my_fragmentation() == 0.0);
    check("my_free(NULL) ничего не делает", (my_free(NULL), my_check_heap() == 0));
    check("my_malloc(0) возвращает уникальный указатель, его можно освободить",
          (b = my_malloc(0)) != NULL && (my_free(b), my_check_heap() == 0));
    check("слишком большой запрос возвращает NULL", my_malloc((size_t)1 << 40) == NULL);
}

static void test_strategies(void)
{
    /* Дыры 304 и 64 байта, между ними занятые блоки. Запрос 48 байт:
     * first fit берёт первую дыру из списка (последнюю освобождённую, 304),
     * best fit берёт самую маленькую подходящую (64). */
    for (int s = 0; s < 2; s++) {
        my_destroy();
        my_set_strategy(s == 0 ? MY_FIRST_FIT : MY_BEST_FIT);
        char *a = my_malloc(64);
        char *x = my_malloc(16);
        char *big = my_malloc(304);
        char *y = my_malloc(16);
        my_free(a);
        my_free(big);
        char *p = my_malloc(48);
        if (s == 0)
            check("first fit: запрос 48 попал в первую дыру списка (304 байта)", p == big);
        else
            check("best fit: запрос 48 попал в самую маленькую дыру (64 байта)", p == a);
        my_free(p);
        my_free(x);
        my_free(y);
        check(s == 0 ? "first fit: после освобождения всего куча целая"
                     : "best fit: после освобождения всего куча целая",
              my_check_heap() == 0);
    }
    my_set_strategy(MY_FIRST_FIT);
}

static void test_realloc(void)
{
    my_destroy();
    char *a = my_malloc(64);
    for (int i = 0; i < 64; i++)
        a[i] = (char)i;
    char *b = my_realloc(a, 200);
    check("realloc растёт на месте, если сосед свободен", b == a && b[63] == 63);
    char *guard = my_malloc(32);
    char *c = my_realloc(b, 5000);
    int same = 1;
    for (int i = 0; i < 64; i++)
        same &= c[i] == (char)i;
    check("realloc переносит блок, если сосед занят, и сохраняет данные", c != b && same);
    char *d = my_realloc(c, 16);
    check("realloc уменьшает блок на месте", d == c && d[15] == 15);
    check("realloc(NULL, n) работает как malloc", (a = my_realloc(NULL, 10)) != NULL);
    check("realloc(p, 0) освобождает блок и возвращает NULL", my_realloc(a, 0) == NULL);
    my_free(d);
    my_free(guard);
    check("после realloc-операций куча целая и снова один блок", my_check_heap() == 0
          && my_fragmentation() == 0.0);
}

static void test_detector(void)
{
    my_destroy();
    my_set_debug(1);
    int saved = quiet_begin();
    char *p = my_malloc(32);
    my_free(p);
    int before = my_check_freed();
    p[5] = 'x';                              /* намеренная запись после free */
    int after = my_check_freed();
    char *q = my_malloc(16);
    my_free(q);
    my_free(q);                              /* намеренный двойной free */
    int x;
    my_free(&x);                             /* free чужого указателя */
    char *leak1 = my_malloc(100);
    char *leak2 = my_malloc(200);
    int leaks = my_report_leaks();
    int errs = my_errors();
    quiet_end(saved);
    check("детектор: без записи после free яд цел", before == 0);
    check("детектор: запись после free найдена", after == 1);
    check("детектор: двойной free и free чужого указателя найдены (всего 3 ошибки)", errs == 3);
    check("детектор: найдено 2 утечки", leaks == 2);
    my_free(leak1);
    my_free(leak2);
    saved = quiet_begin();
    leaks = my_report_leaks();
    quiet_end(saved);
    check("детектор: после освобождения утечек нет", leaks == 0);
    for (int i = 0; i < 3000; i++)           /* больше, чем вмещает карантин */
        my_free(my_malloc(64));
    check("детектор: карантин переполняется без ошибок, куча целая", my_check_heap() == 0);
    my_set_debug(0);
    my_destroy();
}

static void test_random(void)
{
    enum { SLOTS = 500, STEPS = 200000 };
    for (int s = 0; s < 2; s++) {
        my_destroy();
        my_set_strategy(s == 0 ? MY_FIRST_FIT : MY_BEST_FIT);
        static unsigned char *ptr[SLOTS];
        static size_t len[SLOTS];
        static unsigned char tag[SLOTS];
        memset(ptr, 0, sizeof ptr);
        int corrupt = 0, heap_bad = 0;
        for (int step = 0; step < STEPS; step++) {
            int i = (int)(rnd() % SLOTS);
            if (ptr[i]) {
                for (size_t k = 0; k < len[i]; k++)
                    if (ptr[i][k] != tag[i]) {
                        corrupt++;
                        break;
                    }
                if (rnd() % 4 == 0) {         /* иногда realloc вместо free */
                    size_t n = 1 + rnd() % 3000;
                    unsigned char *r = my_realloc(ptr[i], n);
                    size_t keep = n < len[i] ? n : len[i];
                    for (size_t k = 0; k < keep; k++)
                        if (r[k] != tag[i]) {
                            corrupt++;
                            break;
                        }
                    memset(r, tag[i], n);
                    ptr[i] = r;
                    len[i] = n;
                } else {
                    my_free(ptr[i]);
                    ptr[i] = NULL;
                }
            } else {
                len[i] = 1 + rnd() % 3000;
                ptr[i] = my_malloc(len[i]);
                tag[i] = (unsigned char)(rnd() % 255 + 1);
                memset(ptr[i], tag[i], len[i]);
            }
            if (step % 5000 == 0 && my_check_heap() != 0)
                heap_bad++;
        }
        for (int i = 0; i < SLOTS; i++)
            my_free(ptr[i]);
        my_stats_t st;
        my_stats(&st);
        check(s == 0 ? "first fit: 200000 случайных malloc/realloc/free, данные не испорчены"
                     : "best fit: 200000 случайных malloc/realloc/free, данные не испорчены",
              corrupt == 0 && heap_bad == 0);
        check(s == 0 ? "first fit: после освобождения всего один свободный блок"
                     : "best fit: после освобождения всего один свободный блок",
              st.free_blocks == 1 && st.used_blocks == 0 && my_check_heap() == 0);
    }
    my_set_strategy(MY_FIRST_FIT);
    my_destroy();
}

int main(void)
{
    printf("== Основа: разбиение и слияние ==\n");
    test_basic();
    printf("== Две стратегии ==\n");
    test_strategies();
    printf("== realloc ==\n");
    test_realloc();
    printf("== Детектор утечек и use-after-free ==\n");
    test_detector();
    printf("== Случайная нагрузка ==\n");
    test_random();
    printf("\nПроверок: %d, провалено: %d\n", total, failed);
    return failed ? 1 : 0;
}
