# ПР-1. Пользователи и права доступа в Ubuntu

**Автор:** Эркинбеков Айман · **Дисциплина:** Операционные системы · **Вариант:** B

## Тема и цель

Развернуть Ubuntu, научиться управлять пользователями и группами и настроить
общий каталог с правами доступа. Отдельно: понять разницу между `su` и `sudo`
и настроить `~/.bashrc`.

## Что сделано и как это работает

1. Создана группа `developers` и второй пользователь `student2`, он добавлен в эту группу.
2. Создан общий каталог `/srv/shared`: владелец `root`, группа `developers`, права `2775`.
   - `7` для владельца и `7` для группы: читать, писать, заходить в каталог;
   - `5` для остальных: только читать и заходить, писать нельзя;
   - `2` в начале означает бит SGID: новые файлы в каталоге сразу получают группу `developers`.
   Права `777` («всем всё можно») не используются, методичка считает это ошибкой.
3. `student2` создал файл в `/srv/shared`. Основной пользователь `student` в группу
   не входит: файл он прочитать может, а удалить нет.
4. В `~/.bashrc` добавлены два alias и переменная окружения, проверено в новой сессии.

**Почему удалить файл нельзя.** Удаление файла это изменение каталога (из него
убирается запись о файле). Поэтому решают права на каталог, а не на сам файл.
У `student` на `/srv/shared` есть только `r-x` (группа «остальные»), права записи нет,
и `rm` завершается с `Permission denied`. Член группы `developers` имеет право записи
и удалить файл может (sticky bit на каталоге не установлен).

## Файлы

| Файл | За что отвечает |
| --- | --- |
| `README.md` | Отчёт: что сделано, ответы на вопросы, вывод команд |
| `run.sh` | Проверка всех настроек одной командой (ничего не меняет в системе) |
| `evidence/01-environment.txt` | Версия Ubuntu и установленные инструменты (python3, gcc, make, gdb, strace, valgrind, htop) |
| `evidence/02-users.txt` | Группа `developers` и пользователи `student2`, `student` |
| `evidence/03-permissions.txt` | Права каталога и файла, попытка удаления |
| `evidence/04-bashrc.txt` | Проверка alias и переменной в новом терминале |

## Как запустить

Программы в этой работе нет, проверяются настройки системы. Под основным
пользователем:

```bash
./run.sh
```

### Как повторить настройку

Сами команды настройки при выполнении не сохранялись (в `evidence/` лежит только
результат). Чтобы получить то же состояние на чистой Ubuntu:

```bash
sudo groupadd developers
sudo adduser student2                    # задать пароль
sudo usermod -aG developers student2
sudo mkdir -p /srv/shared
sudo chown root:developers /srv/shared
sudo chmod 2775 /srv/shared
sudo -u student2 bash -c 'echo "Created by student2" > /srv/shared/student2.txt'
cat >> ~/.bashrc <<'EOF'
alias ll='ls -lah'
alias cshared='cd /srv/shared'
export OS_PRACTICE='practice1'
EOF
```

## Пример вывода

Вывод снят в Ubuntu Desktop 26.04.1 LTS ARM64 (виртуальная машина UTM на MacBook M4).

`evidence/02-users.txt`:

```text
$ getent group developers
developers:x:1001:student2
$ id student2
uid=1002(student2) gid=1002(student2) groups=1002(student2),100(users),1001(developers)
$ id
uid=1000(student) gid=1000(student) groups=1000(student),4(adm),24(cdrom),27(sudo),30(dip),46(plugdev),100(users),111(lpadmin),114(lxd)
```

`student2` входит в `developers`, а `student` нет (зато входит в `sudo`).

`evidence/03-permissions.txt`:

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

`drwxrwsr-x` это `2775` (буква `s` на месте `x` группы и есть SGID). Файл
получил группу `developers` автоматически. `student` прочитал файл, но удалить
не смог, и файл остался на месте.

`evidence/04-bashrc.txt` (в новом окне терминала):

```text
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
```

Alias работают, переменная видна и в дочернем процессе `bash`, это и есть
отличие `export` от обычной переменной.

Полный вывод, включая версии инструментов, в папке `evidence/`.

## Ответы на вопросы

**Чем `su` отличается от `sudo`?** `su` переключает на другого пользователя
(по умолчанию на `root`) и спрашивает пароль **целевого** пользователя:
`su - student2` открывает сессию `student2`. `sudo` выполняет одну разрешённую
команду с правами другого пользователя (обычно `root`) и спрашивает пароль
**текущего** пользователя; кому что разрешено, задаётся в `/etc/sudoers`.
Например, `sudo apt update`.

**Почему в Ubuntu по умолчанию заблокирован вход под root?** У `root` нет пароля
(он заблокирован), поэтому войти под ним напрямую нельзя. Администрирование идёт
через `sudo` из личной учётной записи: человек не работает постоянно с полными
правами, а каждое действие записывается в журнал от имени конкретного
пользователя. Сам `root` в системе остаётся, и `sudo` продолжает работать.

## Выводы

- Пользователи и группы настроены так, что члены `developers` могут создавать
  файлы в `/srv/shared`, а остальные могут только читать.
- Право удалить файл определяется правом записи в каталог, а не правами файла.
- Бит SGID на общем каталоге удобен для совместной работы: файлы сразу получают
  нужную группу.
- `sudo` безопаснее постоянной работы под `root`: права выдаются на одну команду,
  а действия привязаны к пользователю.
