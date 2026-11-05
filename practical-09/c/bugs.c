/* Программа с намеренными ошибками работы с памятью.
 *
 * Сборка без USE_GLIBC (bugs_my): свой аллокатор с включённым детектором.
 * Сборка с -DUSE_GLIBC (bugs_glibc): обычный malloc, её проверяем valgrind.
 * Ошибки одни и те же, поэтому можно сравнить, что находит каждый инструмент.
 */
#include <stdio.h>
#include <stdlib.h>

#ifdef USE_GLIBC
#define ALLOC(n) malloc(n)
#define FREE(p) free((void *)(p))
#else
#include "myalloc.h"
#define ALLOC(n) my_malloc(n)
#define FREE(p) my_free((void *)(p))
#endif

int main(void)
{
#ifndef USE_GLIBC
    my_set_debug(1);
#endif
    /* volatile, чтобы компилятор не выбросил ошибочные чтения и записи при -O2 */
    volatile char *volatile leak1 = ALLOC(100);        /* 1. утечка 100 байт */
    volatile char *volatile leak2 = ALLOC(200);        /* 2. утечка 200 байт */
    leak1[0] = leak2[0] = 1;

    volatile char *volatile w = ALLOC(32);
    FREE(w);
    w[5] = 'x';                               /* 3. запись после free */

    volatile char *volatile r = ALLOC(32);
    r[0] = 7;
    FREE(r);
    int value = r[0];                         /* 4. чтение после free */

    volatile char *volatile d = ALLOC(16);
    FREE(d);
    FREE(d);                                  /* 5. двойной free */

    printf("программа дошла до конца, прочитано после free: %d\n", value != 0);
#ifndef USE_GLIBC
    int uaf = my_check_freed();
    int leaks = my_report_leaks();
    printf("детектор: запись после free %d, утечек %d, всего ошибок free/записи %d\n",
           uaf, leaks, my_errors());
#endif
    return 0;
}
