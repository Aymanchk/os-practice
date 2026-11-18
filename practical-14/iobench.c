// ПР-14: запись файла тремя способами и запись в обход страничного кэша.
//
//   ./iobench byte   ФАЙЛ МБ   write() по одному байту (без буфера)
//   ./iobench block  ФАЙЛ МБ   write() буферами по 64 КБ
//   ./iobench fwrite ФАЙЛ МБ   fwrite() по одному байту, буферизует stdio
//   ./iobench cached ФАЙЛ МБ   write() по 64 КБ + fsync (данные доходят до диска)
//   ./iobench direct ФАЙЛ МБ   O_DIRECT по 64 КБ в обход кэша (+ fsync для метаданных)
//
// Печатает: способ, объём, время, скорость.
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

#define BLOCK (64 * 1024)

static double now(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec + ts.tv_nsec / 1e9;
}

static void die(const char *what) {
    fprintf(stderr, "%s: %s\n", what, strerror(errno));
    exit(1);
}

static void write_all(int fd, const char *buf, size_t n) {
    while (n > 0) {
        ssize_t w = write(fd, buf, n);
        if (w < 0) {
            if (errno == EINTR) continue;
            die("write");
        }
        buf += w;
        n -= (size_t)w;
    }
}

int main(int argc, char **argv) {
    if (argc != 4) {
        fprintf(stderr, "использование: %s byte|block|fwrite|cached|direct ФАЙЛ МБ\n", argv[0]);
        return 2;
    }
    const char *mode = argv[1], *path = argv[2];
    long mb = strtol(argv[3], NULL, 10);
    if (mb <= 0) {
        fprintf(stderr, "объём должен быть больше 0 МБ\n");
        return 2;
    }
    size_t total = (size_t)mb * 1024 * 1024;

    char *buf = NULL;
    if (posix_memalign((void **)&buf, 4096, BLOCK) != 0) die("posix_memalign");
    memset(buf, 'x', BLOCK);

    double t0 = now();
    if (strcmp(mode, "byte") == 0) {
        int fd = open(path, O_WRONLY | O_CREAT | O_TRUNC, 0644);
        if (fd < 0) die("open");
        for (size_t i = 0; i < total; i++) write_all(fd, buf, 1);
        close(fd);
    } else if (strcmp(mode, "block") == 0 || strcmp(mode, "cached") == 0) {
        int fd = open(path, O_WRONLY | O_CREAT | O_TRUNC, 0644);
        if (fd < 0) die("open");
        for (size_t done = 0; done < total; done += BLOCK) write_all(fd, buf, BLOCK);
        if (strcmp(mode, "cached") == 0 && fsync(fd) != 0) die("fsync");
        close(fd);
    } else if (strcmp(mode, "fwrite") == 0) {
        FILE *f = fopen(path, "w");
        if (!f) die("fopen");
        for (size_t i = 0; i < total; i++)
            if (fwrite(buf, 1, 1, f) != 1) die("fwrite");
        if (fclose(f) != 0) die("fclose");
    } else if (strcmp(mode, "direct") == 0) {
        int fd = open(path, O_WRONLY | O_CREAT | O_TRUNC | O_DIRECT, 0644);
        if (fd < 0) die("open O_DIRECT");
        for (size_t done = 0; done < total; done += BLOCK) write_all(fd, buf, BLOCK);
        if (fsync(fd) != 0) die("fsync");
        close(fd);
    } else {
        fprintf(stderr, "неизвестный способ: %s\n", mode);
        return 2;
    }
    double dt = now() - t0;
    printf("%-7s %5ld МБ  %9.3f с  %9.1f МБ/с\n", mode, mb, dt, mb / dt);
    free(buf);
    return 0;
}
