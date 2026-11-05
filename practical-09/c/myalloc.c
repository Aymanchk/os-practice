/* Свой аллокатор поверх одного mmap-региона.
 *
 * Память - один большой регион, который берётся у системы через mmap один раз.
 * Регион разрезан на блоки, у каждого блока впереди заголовок (block_t).
 * Блоки лежат подряд, каждый знает физически предыдущий блок (prev), а следующий
 * считается по размеру. Свободные блоки дополнительно связаны в двусвязный список.
 *
 * my_malloc: ищет свободный блок по стратегии (first fit или best fit), отрезает
 *            от него ровно нужный кусок, остаток снова кладёт в список (разбиение).
 * my_free:   помечает блок свободным и склеивает его с соседями, если они свободны (слияние).
 * my_realloc: уменьшает блок на месте, растёт на месте за счёт свободного соседа,
 *             иначе выделяет новый блок, копирует данные и освобождает старый.
 *
 * Отладочный режим (my_set_debug(1)): освобождённый блок заливается байтом 0xDD и
 * сначала попадает в карантин. Если потом "яд" испорчен, значит была запись после free.
 * Ещё ловятся двойной free и free чужого указателя, а my_report_leaks печатает утечки.
 */
#define _DEFAULT_SOURCE
#include "myalloc.h"

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>

#define ALIGN 16
#define REGION_DEFAULT_MB 256
#define MAGIC_USED 0xA110CA7Eu   /* блок выдан */
#define MAGIC_FREE 0xF4EEB10Cu   /* блок в списке свободных */
#define MAGIC_QUAR 0xDEADF4EEu   /* блок освобождён, но лежит в карантине */
#define POISON 0xDD
#define QUARANTINE_MAX 1024

typedef struct block {
    size_t size;               /* полезная нагрузка в байтах, кратна ALIGN */
    size_t asked;              /* сколько просили (для отчёта об утечках) */
    struct block *prev;        /* физически предыдущий блок или NULL */
    struct block *next_free;   /* двусвязный список свободных блоков */
    struct block *prev_free;
    const char *alloc_file;    /* где выделен */
    const char *free_file;     /* где освобождён */
    int alloc_line;
    int free_line;
    unsigned magic;
} block_t;

#define HDR ((sizeof(block_t) + ALIGN - 1) & ~(size_t)(ALIGN - 1))
#define MIN_SPLIT ALIGN          /* остаток меньше этого не отрезаем */

static char *region_start = NULL;
static char *region_end = NULL;
static block_t *free_head = NULL;
static my_strategy_t strategy = MY_FIRST_FIT;
static int debug = 0;
static int errors = 0;
static block_t *quarantine[QUARANTINE_MAX];
static size_t q_count = 0, q_first = 0;

/* ---------- вспомогательные функции ---------- */

static void *payload(block_t *b) { return (char *)b + HDR; }

static block_t *next_phys(block_t *b)
{
    char *n = (char *)b + HDR + b->size;
    return n < region_end ? (block_t *)n : NULL;
}

static void list_push(block_t *b)
{
    b->magic = MAGIC_FREE;
    b->prev_free = NULL;
    b->next_free = free_head;
    if (free_head)
        free_head->prev_free = b;
    free_head = b;
}

static void list_remove(block_t *b)
{
    if (b->prev_free)
        b->prev_free->next_free = b->next_free;
    else
        free_head = b->next_free;
    if (b->next_free)
        b->next_free->prev_free = b->prev_free;
    b->next_free = b->prev_free = NULL;
}

static size_t round_up(size_t n)
{
    if (n == 0)
        n = 1;
    if (n > SIZE_MAX - ALIGN)
        return 0;
    return (n + ALIGN - 1) & ~(size_t)(ALIGN - 1);
}

static int init(void)
{
    if (region_start)
        return 1;
    size_t mb = REGION_DEFAULT_MB;
    const char *env = getenv("MYALLOC_REGION_MB");
    if (env && atoi(env) > 0)
        mb = (size_t)atoi(env);
    size_t size = mb << 20;
    void *p = mmap(NULL, size, PROT_READ | PROT_WRITE,
                   MAP_PRIVATE | MAP_ANONYMOUS | MAP_NORESERVE, -1, 0);
    if (p == MAP_FAILED)
        return 0;
    region_start = p;
    region_end = region_start + size;
    block_t *b = (block_t *)p;
    memset(b, 0, HDR);
    b->size = size - HDR;
    list_push(b);
    return 1;
}

/* Поиск свободного блока размером не меньше need по текущей стратегии. */
static block_t *find(size_t need)
{
    block_t *best = NULL;
    for (block_t *b = free_head; b; b = b->next_free) {
        if (b->size < need)
            continue;
        if (strategy == MY_FIRST_FIT)
            return b;                       /* первый подходящий */
        if (!best || b->size < best->size) {
            best = b;                       /* самый маленький из подходящих */
            if (b->size == need)
                break;
        }
    }
    return best;
}

/* Делает блок b свободным: склеивает с соседями и кладёт в список. */
static void make_free(block_t *b)
{
    block_t *n = next_phys(b);
    if (n && n->magic == MAGIC_FREE) {      /* сосед справа свободен */
        list_remove(n);
        n->magic = 0;
        b->size += HDR + n->size;
        block_t *nn = next_phys(b);
        if (nn)
            nn->prev = b;
    }
    block_t *p = b->prev;
    if (p && p->magic == MAGIC_FREE) {      /* сосед слева свободен */
        list_remove(p);
        b->magic = 0;
        p->size += HDR + b->size;
        block_t *nn = next_phys(p);
        if (nn)
            nn->prev = p;
        b = p;
    }
    list_push(b);
}

/* Отрезает от занятого блока b всё, что больше need, и возвращает остаток в список. */
static void split(block_t *b, size_t need)
{
    if (b->size < need + HDR + MIN_SPLIT)
        return;
    block_t *rest = (block_t *)((char *)b + HDR + need);
    memset(rest, 0, HDR);
    rest->size = b->size - need - HDR;
    rest->prev = b;
    block_t *n = next_phys(rest);
    if (n)
        n->prev = rest;
    b->size = need;
    make_free(rest);
}

/* Проверяет, что ptr - начало выданного блока. Иначе печатает ошибку и возвращает NULL. */
static block_t *used_block(void *ptr, const char *what, const char *file, int line)
{
    char *c = ptr;
    if (!region_start || c < region_start + HDR || c >= region_end
        || ((uintptr_t)(c - region_start) % ALIGN) != 0) {
        fprintf(stderr, "myalloc: %s чужого указателя %p (%s:%d)\n", what, ptr, file, line);
        errors++;
        return NULL;
    }
    block_t *b = (block_t *)(c - HDR);
    if (b->magic == MAGIC_FREE || b->magic == MAGIC_QUAR) {
        fprintf(stderr, "myalloc: %s уже освобождённого блока (выделен %s:%d, освобождён %s:%d, "
                "повторно %s:%d)\n", what, b->alloc_file ? b->alloc_file : "?", b->alloc_line,
                b->free_file ? b->free_file : "?", b->free_line, file, line);
        errors++;
        return NULL;
    }
    if (b->magic != MAGIC_USED) {
        fprintf(stderr, "myalloc: %s указателя, который не выдавался (%s:%d)\n", what, file, line);
        errors++;
        return NULL;
    }
    return b;
}

static int poison_intact(block_t *b)
{
    const unsigned char *p = payload(b);
    for (size_t i = 0; i < b->size; i++)
        if (p[i] != POISON)
            return 0;
    return 1;
}

static void report_uaf(block_t *b)
{
    fprintf(stderr, "myalloc: запись после free в блок %zu байт (выделен %s:%d, освобождён %s:%d)\n",
            b->asked, b->alloc_file ? b->alloc_file : "?", b->alloc_line,
            b->free_file ? b->free_file : "?", b->free_line);
}

/* Достаёт самый старый блок из карантина: проверяет яд и по-настоящему освобождает. */
static void quarantine_evict(void)
{
    block_t *b = quarantine[q_first];
    q_first = (q_first + 1) % QUARANTINE_MAX;
    q_count--;
    if (!poison_intact(b)) {
        report_uaf(b);
        errors++;
    }
    b->magic = 0;
    make_free(b);
}

/* ---------- внешний интерфейс ---------- */

void my_set_strategy(my_strategy_t s) { strategy = s; }

void my_set_debug(int on) { debug = on; }

void *my_malloc_at(size_t size, const char *file, int line)
{
    if (!init())
        return NULL;
    size_t need = round_up(size);
    if (need == 0)
        return NULL;
    block_t *b = find(need);
    if (!b && debug) {                      /* памяти нет - сначала опустошаем карантин */
        while (q_count)
            quarantine_evict();
        b = find(need);
    }
    if (!b)
        return NULL;
    list_remove(b);
    b->magic = MAGIC_USED;
    split(b, need);
    b->asked = size;
    b->alloc_file = file;
    b->alloc_line = line;
    b->free_file = NULL;
    b->free_line = 0;
    return payload(b);
}

void my_free_at(void *ptr, const char *file, int line)
{
    if (!ptr)
        return;
    block_t *b = used_block(ptr, "free", file, line);
    if (!b)
        return;
    b->free_file = file;
    b->free_line = line;
    if (debug) {
        b->magic = MAGIC_QUAR;
        memset(payload(b), POISON, b->size);
        if (q_count == QUARANTINE_MAX)
            quarantine_evict();
        quarantine[(q_first + q_count) % QUARANTINE_MAX] = b;
        q_count++;
        return;
    }
    make_free(b);
}

void *my_realloc_at(void *ptr, size_t size, const char *file, int line)
{
    if (!ptr)
        return my_malloc_at(size, file, line);
    if (size == 0) {
        my_free_at(ptr, file, line);
        return NULL;
    }
    block_t *b = used_block(ptr, "realloc", file, line);
    if (!b)
        return NULL;
    size_t need = round_up(size);
    if (need == 0)
        return NULL;
    if (need <= b->size) {                  /* уменьшение на месте */
        split(b, need);
        b->asked = size;
        return ptr;
    }
    block_t *n = next_phys(b);
    if (n && n->magic == MAGIC_FREE && b->size + HDR + n->size >= need) {
        list_remove(n);                     /* рост на месте за счёт свободного соседа */
        n->magic = 0;
        b->size += HDR + n->size;
        block_t *nn = next_phys(b);
        if (nn)
            nn->prev = b;
        split(b, need);
        b->asked = size;
        return ptr;
    }
    void *q = my_malloc_at(size, file, line);
    if (!q)
        return NULL;
    memcpy(q, ptr, b->asked < size ? b->asked : size);
    my_free_at(ptr, file, line);
    return q;
}

void my_stats(my_stats_t *st)
{
    memset(st, 0, sizeof *st);
    if (!region_start)
        return;
    st->region = (size_t)(region_end - region_start);
    for (block_t *b = (block_t *)region_start; b; b = next_phys(b)) {
        if (b->magic == MAGIC_FREE) {
            st->free_total += b->size;
            st->free_blocks++;
            if (b->size > st->largest_free)
                st->largest_free = b->size;
            if (!next_phys(b))
                st->tail_free = b->size;
        } else if (b->magic == MAGIC_USED) {
            st->used += b->size;
            st->used_blocks++;
        }
    }
}

/* Фрагментация - какая доля используемой части региона ушла в дыры.
 * Используемая часть - всё до свободного хвоста региона: его система ещё не выдавала,
 * и он не "дыра". 0 - дыр нет, 0.5 - половина занятого пространства пустует. */
double my_fragmentation(void)
{
    my_stats_t st;
    my_stats(&st);
    size_t holes = st.free_total - st.tail_free;
    if (st.used + holes == 0)
        return 0.0;
    return (double)holes / (double)(st.used + holes);
}

int my_check_heap(void)
{
    if (!region_start)
        return 0;
    int problems = 0;
    size_t total = 0, free_in_heap = 0, free_in_list = 0;
    block_t *prev = NULL;
    int prev_free = 0;
    for (block_t *b = (block_t *)region_start; b; b = next_phys(b)) {
        if (b->prev != prev || b->size % ALIGN != 0)
            problems++;
        int is_free = b->magic == MAGIC_FREE;
        if (is_free && prev_free)
            problems++;                     /* два свободных подряд: слияние не сработало */
        if (b->magic != MAGIC_FREE && b->magic != MAGIC_USED && b->magic != MAGIC_QUAR)
            problems++;
        free_in_heap += is_free;
        total += HDR + b->size;
        prev = b;
        prev_free = is_free;
    }
    if (total != (size_t)(region_end - region_start))
        problems++;
    for (block_t *b = free_head; b; b = b->next_free) {
        if (b->magic != MAGIC_FREE || (b->next_free && b->next_free->prev_free != b))
            problems++;
        free_in_list++;
    }
    if (free_in_list != free_in_heap)
        problems++;
    return problems;
}

int my_check_freed(void)
{
    int bad = 0;
    for (size_t i = 0; i < q_count; i++) {
        block_t *b = quarantine[(q_first + i) % QUARANTINE_MAX];
        if (!poison_intact(b)) {
            report_uaf(b);
            memset(payload(b), POISON, b->size);   /* чтобы не сообщать дважды */
            errors++;
            bad++;
        }
    }
    return bad;
}

int my_report_leaks(void)
{
    if (!region_start)
        return 0;
    int count = 0;
    size_t bytes = 0;
    for (block_t *b = (block_t *)region_start; b; b = next_phys(b)) {
        if (b->magic == MAGIC_USED) {
            fprintf(stderr, "myalloc: утечка %zu байт, выделено в %s:%d\n", b->asked,
                    b->alloc_file ? b->alloc_file : "?", b->alloc_line);
            count++;
            bytes += b->asked;
        }
    }
    if (count)
        fprintf(stderr, "myalloc: всего утечек %d, %zu байт\n", count, bytes);
    return count;
}

int my_errors(void) { return errors; }

void my_destroy(void)
{
    if (region_start)
        munmap(region_start, (size_t)(region_end - region_start));
    region_start = region_end = NULL;
    free_head = NULL;
    q_count = q_first = 0;
    errors = 0;
}
