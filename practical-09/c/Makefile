# Сборка и проверка аллокатора уровня C.
# Строки команд начинаются с ">" вместо табуляции (так их не испортит копирование).
.RECIPEPREFIX := >
CC = gcc
CFLAGS = -std=c11 -O2 -g -Wall -Wextra
VALGRIND = valgrind --tool=memcheck --leak-check=full --error-exitcode=1

all: test_myalloc bench bugs_my bugs_glibc

test_myalloc: test_myalloc.c myalloc.c myalloc.h
> $(CC) $(CFLAGS) -o $@ test_myalloc.c myalloc.c

bench: bench.c myalloc.c myalloc.h
> $(CC) $(CFLAGS) -o $@ bench.c myalloc.c

bugs_my: bugs.c myalloc.c myalloc.h
> $(CC) $(CFLAGS) -o $@ bugs.c myalloc.c

bugs_glibc: bugs.c
> $(CC) $(CFLAGS) -DUSE_GLIBC -o $@ bugs.c

test: test_myalloc
> ./test_myalloc

valgrind: test_myalloc bench
> $(VALGRIND) ./test_myalloc
> $(VALGRIND) ./bench mixed first
> $(VALGRIND) ./bench mixed best

clean:
> rm -f test_myalloc bench bugs_my bugs_glibc

.PHONY: all test valgrind clean
