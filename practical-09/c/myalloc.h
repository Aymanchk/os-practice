/* Свой аллокатор поверх одного mmap-региона.
 * Список свободных блоков, разбиение и слияние, две стратегии (first fit и best fit).
 * В отладочном режиме: детектор утечек, двойного free и записи после free. */
#ifndef MYALLOC_H
#define MYALLOC_H

#include <stddef.h>

typedef enum { MY_FIRST_FIT = 0, MY_BEST_FIT = 1 } my_strategy_t;

typedef struct {
    size_t region;        /* размер всего региона */
    size_t used;          /* сколько байт выдано (полезная нагрузка) */
    size_t free_total;    /* сколько байт свободно в свободных блоках */
    size_t largest_free;  /* самый большой свободный блок */
    size_t free_blocks;   /* число свободных блоков */
    size_t used_blocks;   /* число занятых блоков */
    size_t tail_free;     /* свободный хвост региона (последний блок, если он свободен) */
} my_stats_t;

void   my_set_strategy(my_strategy_t s);
void   my_set_debug(int on);          /* включить детектор (до первого my_malloc) */

void  *my_malloc_at(size_t size, const char *file, int line);
void   my_free_at(void *ptr, const char *file, int line);
void  *my_realloc_at(void *ptr, size_t size, const char *file, int line);

/* Обычные имена: место вызова (файл и строка) запоминается для отчётов детектора. */
#define my_malloc(n)      my_malloc_at((n), __FILE__, __LINE__)
#define my_free(p)        my_free_at((p), __FILE__, __LINE__)
#define my_realloc(p, n)  my_realloc_at((p), (n), __FILE__, __LINE__)

void   my_stats(my_stats_t *st);
double my_fragmentation(void);        /* доля дыр в используемой части: дыры / (занято + дыры) */
int    my_check_heap(void);           /* целостность списков; 0 - всё в порядке */
int    my_check_freed(void);          /* сколько освобождённых блоков испорчено (запись после free) */
int    my_report_leaks(void);         /* печатает неосвобождённые блоки, возвращает их число */
int    my_errors(void);               /* сколько ошибок нашёл детектор (двойной free и т.п.) */
void   my_destroy(void);              /* вернуть регион системе (munmap) */

#endif
