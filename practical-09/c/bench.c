/* Бенчмарк: свой аллокатор (first fit, best fit) против glibc malloc.
 *
 * Запуск: ./bench <small|mixed|large> <first|best|glibc>
 * Печатает одну строку: сценарий, аллокатор, время, пик RSS, фрагментация, отказы.
 *
 * Сценарии:
 *   small - много мелких выделений: 200000 блоков по 16-64 байта, потом free через один;
 *   mixed - чередование alloc/free: 1000 ячеек, 300000 случайных шагов, размеры 16-8192;
 *   large - крупные блоки: 64 ячейки, 4000 шагов, размеры 64 КБ - 2 МБ.
 * Время - медиана пяти прогонов с одинаковыми случайными числами. Для своего аллокатора
 * потом идёт ещё один прогон, в котором во время работы считается фрагментация.
 */
#define _DEFAULT_SOURCE
#include "myalloc.h"

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/resource.h>
#include <time.h>

static int use_glibc = 0;
static int sample = 0;          /* 1 - считать фрагментацию во время прогона */
static double frag_sum = 0.0;
static long frag_n = 0;
static long fails = 0;

static uint64_t rng_state;
static uint64_t rnd(void)
{
    rng_state ^= rng_state << 13;
    rng_state ^= rng_state >> 7;
    rng_state ^= rng_state << 17;
    return rng_state;
}

static size_t between(size_t lo, size_t hi) { return lo + (size_t)(rnd() % (hi - lo + 1)); }

static void *a_malloc(size_t n)
{
    void *p = use_glibc ? malloc(n) : my_malloc(n);
    if (!p)
        fails++;
    else
        memset(p, 0x5A, n);     /* трогаем память, чтобы она попала в RSS */
    return p;
}

static void a_free(void *p)
{
    if (use_glibc)
        free(p);
    else
        my_free(p);
}

static void take_sample(void)
{
    if (sample) {
        frag_sum += my_fragmentation();
        frag_n++;
    }
}

static void run_small(void)
{
    enum { N = 200000 };
    static void *p[N];
    for (int i = 0; i < N; i++)
        p[i] = a_malloc(between(16, 64));
    for (int i = 0; i < N; i += 2) {        /* сначала чётные: остаются дыры между занятыми */
        a_free(p[i]);
        if (i % 20000 == 0)
            take_sample();
    }
    for (int i = 1; i < N; i += 2) {
        a_free(p[i]);
        if (i % 20001 == 0)
            take_sample();
    }
}

static void run_cells(int slots, long steps, size_t small_lo, size_t small_hi,
                      size_t big_lo, size_t big_hi, int big_percent, long sample_every)
{
    void **p = calloc((size_t)slots, sizeof *p);
    if (!p)
        exit(1);
    for (long step = 0; step < steps; step++) {
        int i = (int)(rnd() % (uint64_t)slots);
        if (p[i]) {
            a_free(p[i]);
            p[i] = NULL;
        } else {
            size_t n = (int)(rnd() % 100) < big_percent ? between(big_lo, big_hi)
                                                        : between(small_lo, small_hi);
            p[i] = a_malloc(n);
        }
        if (step % sample_every == 0)
            take_sample();
    }
    for (int i = 0; i < slots; i++)
        a_free(p[i]);
    free(p);
}

static void run(const char *scenario)
{
    rng_state = 0x9E3779B97F4A7C15ull;
    if (strcmp(scenario, "small") == 0)
        run_small();
    else if (strcmp(scenario, "mixed") == 0)
        run_cells(1000, 300000, 16, 256, 256, 8192, 20, 1000);
    else
        run_cells(64, 4000, 64 << 10, 256 << 10, 256 << 10, 2 << 20, 50, 20);
}

int main(int argc, char **argv)
{
    if (argc != 3 || (strcmp(argv[1], "small") && strcmp(argv[1], "mixed") && strcmp(argv[1], "large"))
        || (strcmp(argv[2], "first") && strcmp(argv[2], "best") && strcmp(argv[2], "glibc"))) {
        fprintf(stderr, "использование: %s <small|mixed|large> <first|best|glibc>\n", argv[0]);
        return 2;
    }
    use_glibc = strcmp(argv[2], "glibc") == 0;
    my_set_strategy(strcmp(argv[2], "best") == 0 ? MY_BEST_FIT : MY_FIRST_FIT);

    enum { RUNS = 5 };
    double times[RUNS];
    long timed_fails = 0;
    for (int r = 0; r < RUNS; r++) {          /* 5 прогонов, берём медиану времени */
        struct timespec t0, t1;
        fails = 0;
        clock_gettime(CLOCK_MONOTONIC, &t0);
        run(argv[1]);
        clock_gettime(CLOCK_MONOTONIC, &t1);
        times[r] = (double)(t1.tv_sec - t0.tv_sec) * 1000.0 + (double)(t1.tv_nsec - t0.tv_nsec) / 1e6;
        timed_fails = fails;
        if (!use_glibc && r < RUNS - 1) {
            if (my_check_heap()) {
                fprintf(stderr, "куча испорчена\n");
                return 1;
            }
            my_destroy();
        }
    }
    for (int i = 0; i < RUNS; i++)            /* сортировка вставками для медианы */
        for (int j = i; j > 0 && times[j - 1] > times[j]; j--) {
            double t = times[j];
            times[j] = times[j - 1];
            times[j - 1] = t;
        }
    double ms = times[RUNS / 2];

    char frag[32] = "-";
    if (!use_glibc) {
        int leftover = my_check_heap();
        my_destroy();
        sample = 1;
        run(argv[1]);
        snprintf(frag, sizeof frag, "%.2f", frag_n ? frag_sum / (double)frag_n : 0.0);
        if (leftover) {
            fprintf(stderr, "куча испорчена: %d проблем\n", leftover);
            return 1;
        }
    }

    struct rusage ru;
    getrusage(RUSAGE_SELF, &ru);
    printf("%s %s %.1f %ld %s %ld\n", argv[1], argv[2], ms, ru.ru_maxrss, frag, timed_fails);
    return 0;
}
