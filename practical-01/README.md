# ПР-1: пользователи и права доступа в Ubuntu

**ФИО:** Эркинбеков Айман

**Дисциплина:** Проектирование операционных систем

**Вариант:** B

## Задание

Установить Ubuntu Desktop, создать пользователя `student2` и группу `developers`, настроить общий каталог `/srv/shared` и проверить права на файл. Затем объяснить разницу между `su` и `sudo`, а также проверить два alias и переменную окружения в новой сессии Bash.

## Файлы

- `README.md`: описание работы, ответы на вопросы и вывод команд.
- `evidence/01-environment.txt`: версия Ubuntu и установленные программы.
- `evidence/02-users.txt`: пользователи и группа.
- `evidence/03-permissions.txt`: права каталога и попытка удалить файл.
- `evidence/04-bashrc.txt`: проверка alias и переменной.

## Как проверить

Отдельной программы для запуска нет. Открой терминал в Ubuntu под пользователем `student` и выполни:

```bash
id student2
ls -ld /srv/shared
cat /srv/shared/student2.txt
rm -f /srv/shared/student2.txt
```

Последняя команда должна выдать `Permission denied`: пользователь `student` может прочитать файл, но не может удалить его. Сохранённый вывод всех проверок есть ниже и в папке `evidence`.

## Результат

`student2` добавлен в `developers` и создал файл в `/srv/shared`. У каталога владелец `root`, группа `developers` и права `2775`. Основной пользователь прочитал файл, но удалить его не смог. Два alias и переменная `OS_PRACTICE` сработали в новом терминале.

## Среда

Ubuntu Desktop 26.04.1 LTS ARM64 в UTM на MacBook M4.
Основной пользователь: student.
Дополнительный пользователь: student2.

## Вариант B

Создана группа developers и пользователь student2, добавленный в эту группу.
Создан каталог /srv/shared с владельцем root, группой developers и правами 2775.
Пользователь student2 создал файл /srv/shared/student2.txt.
Основной пользователь student прочитал файл и попытался удалить его.
В ~/.bashrc добавлены два alias и переменная окружения.
Настройки проверены в новом окне терминала.

## Почему удаление запрещено

Каталог /srv/shared принадлежит root:developers и имеет права 2775.
Пользователь student не входит в developers. Для остальных пользователей
каталог доступен на чтение и проход, но не на запись.

Удаление файла определяется правами на содержащий его каталог.
Поэтому student может прочитать файл с подходящими правами самого файла,
но не может удалить запись о нём из каталога. Команда rm завершается
с Permission denied. Член developers имеет право записи в каталог и
может удалять файлы; sticky bit на каталоге не установлен.

## Чем su отличается от sudo

su запускает оболочку или команду от имени другого пользователя.
При переходе на другого пользователя обычно требуется пароль целевого
пользователя. Например, su - student2 открывает сессию student2.

sudo запускает разрешённую команду с правами другого пользователя,
обычно root. Обычно запрашивается пароль текущего пользователя;
доступ определяется настройкой sudo. Например, sudo apt update
запускает обновление с административными правами.

## Почему вход под root заблокирован

В Ubuntu пароль пользователя root по умолчанию заблокирован, поэтому
обычно нельзя войти в систему напрямую по паролю root. Административные
команды запускаются через sudo из личной учётной записи. Это уменьшает
необходимость постоянно работать с полными правами и позволяет связать
действия с конкретным пользователем. Пользователь root при этом остаётся
в системе; его парольная блокировка не отменяет разрешённое использование sudo.

## Настройка ~/.bashrc

alias ll='ls -lah'
alias cshared='cd /srv/shared'
export OS_PRACTICE='practice1'

В новом терминале проверено, что ll выводит подробный список файлов,
cshared переходит в /srv/shared, а переменная OS_PRACTICE имеет значение
practice1 и доступна дочернему процессу Bash.

## Вывод команд

Фактический вывод команд приложен ниже текстом.

### evidence/01-environment.txt

```text
$ cat /etc/os-release
PRETTY_NAME="Ubuntu 26.04.1 LTS"
NAME="Ubuntu"
VERSION_ID="26.04"
VERSION="26.04.1 LTS (Resolute Raccoon)"
VERSION_CODENAME=resolute
ID=ubuntu
ID_LIKE=debian
HOME_URL="https://www.ubuntu.com/"
SUPPORT_URL="https://help.ubuntu.com/"
BUG_REPORT_URL="https://bugs.launchpad.net/ubuntu/"
PRIVACY_POLICY_URL="https://www.ubuntu.com/legal/terms-and-policies/privacy-policy"
UBUNTU_CODENAME=resolute
LOGO=ubuntu-logo
$ uname -m
aarch64
$ python3 --version
Python 3.14.4
$ gcc --version
gcc (Ubuntu 15.2.0-16ubuntu1) 15.2.0
Copyright (C) 2025 Free Software Foundation, Inc.
This is free software; see the source for copying conditions.  There is NO
warranty; not even for MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.

$ make --version
GNU Make 4.4.1
Built for aarch64-unknown-linux-gnu
Copyright (C) 1988-2023 Free Software Foundation, Inc.
License GPLv3+: GNU GPL version 3 or later <https://gnu.org/licenses/gpl.html>
This is free software: you are free to change and redistribute it.
There is NO WARRANTY, to the extent permitted by law.
$ gdb --version
GNU gdb (Ubuntu 17.1-2ubuntu1) 17.1
Copyright (C) 2025 Free Software Foundation, Inc.
License GPLv3+: GNU GPL version 3 or later <http://gnu.org/licenses/gpl.html>
This is free software: you are free to change and redistribute it.
There is NO WARRANTY, to the extent permitted by law.
$ strace --version
strace -- version 6.19
Copyright (c) 1991-2026 The strace developers <https://strace.io>.
This is free software; see the source for copying conditions.  There is NO
warranty; not even for MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.

Optional features enabled: no-m32-mpers
$ valgrind --version
valgrind-3.26.0
$ htop --version
htop 3.4.1

```

### evidence/02-users.txt

```text
$ getent group developers
developers:x:1001:student2
$ id student2
uid=1002(student2) gid=1002(student2) groups=1002(student2),100(users),1001(developers)
$ id
uid=1000(student) gid=1000(student) groups=1000(student),4(adm),24(cdrom),27(sudo),30(dip),46(plugdev),100(users),111(lpadmin),114(lxd)

```

### evidence/03-permissions.txt

```text
$ whoami
student
$ ls -ld /srv/shared
drwxrwsr-x 2 root developers 4096 Sep 23 18:08 /srv/shared
$ stat -c "%U %G %a %n" /srv/shared/student2.txt
student2 developers 644 /srv/shared/student2.txt
$ cat /srv/shared/student2.txt
Created by student2
$ rm -f /srv/shared/student2.txt
rm: cannot remove '/srv/shared/student2.txt': Permission denied
rm exit status: 1
$ ls -l /srv/shared/student2.txt
-rw-r--r-- 1 student2 developers 20 Sep 23 18:08 /srv/shared/student2.txt

```

### evidence/04-bashrc.txt

```text
$ whoami
student
$ alias ll
alias ll='ls -lah'
$ alias cshared
alias cshared='cd /srv/shared'
$ printenv OS_PRACTICE
practice1
$ bash -c 'echo "$OS_PRACTICE"'
practice1
$ cshared
$ pwd
/srv/shared
$ ll
total 12K
drwxrwsr-x 2 root     developers 4.0K Sep 23 18:08 .
drwxr-xr-x 3 root     root       4.0K Sep 23 18:07 ..
-rw-r--r-- 1 student2 developers   20 Sep 23 18:08 student2.txt

```
