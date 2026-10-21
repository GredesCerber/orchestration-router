# orchestration-router

Навык (skill) для ИИ-агентов, который распределяет большую работу между доступными исполнителями: собственными субагентами, Claude Code, Codex и подключёнными API. Навык не зависит от среды: его загружает Codex, Claude Code или другой агент, и загрузивший становится координатором, а остальные CLI — исполнителями.

*English: a host-neutral agent skill for orchestrating work across native subagents, Claude Code CLI, Codex CLI and authorized APIs — executor discovery, capability routing (e.g. image generation via Codex), model/effort choice, usage-limit checks, file ownership, and acceptance. Format: `SKILL.md` with YAML front matter, compatible with Codex and Claude Code skills.*

## Что умеет

- **Находит исполнителей** без запуска моделей: `scripts/discover.py` показывает агентские CLI на машине, версии и видимые возможности (например, генерацию картинок у Codex).
- **Направляет задачу туда, где есть нужный инструмент**: картинки и приложения Codex через `codex exec`, навыки и субагенты Claude через `claude -p`. Модель и уровень рассуждения выбираются уже внутри исполнителя.
- **Следит за лимитами**: `scripts/claude_usage_statusline.py` (по желанию) сохраняет проценты 5-часового и недельного окна Claude. `scripts/codex_usage.py` читает последние известные лимиты Codex из локальных логов.
- **Планирует волну задач**: `scripts/plan_wave.py` учитывает зависимости, владение файлами, порты и базы, общий пул квот. Сам ничего не запускает.
- **Даёт шаблоны**: задание исполнителю, его отчёт, журнал задач.
- **Описывает рецепты запуска** Claude Code и Codex в фоне на Windows и macOS/Linux, с правами только-чтение или запись в своей зоне и с логами.

## Установка

Codex:

```bash
git clone https://github.com/GredesCerber/orchestration-router ~/.codex/skills/orchestration-router
```

Claude Code:

```bash
git clone https://github.com/GredesCerber/orchestration-router ~/.claude/skills/orchestration-router
```

Если нужны обе среды, держите одну копию и подключите вторую ссылкой. В Windows это делается через junction: `New-Item -ItemType Junction -Path $HOME\.claude\skills\orchestration-router -Target $HOME\.codex\skills\orchestration-router`.

Другой агент: дайте ему прочитать `SKILL.md`. Пути внутри навыка относительные.

Нужен Python 3.10+ без сторонних пакетов.

### Лимиты Claude в статус-строке (по желанию)

Этот шаг меняет глобальные настройки Claude Code. Добавьте в `~/.claude/settings.json`:

```json
"statusLine": {"type": "command", "command": "python -B <путь-к-навыку>/scripts/claude_usage_statusline.py"}
```

Скрипт выводит строку вида `Opus | 5h 24% | 7d 41%` и записывает `~/.claude/usage-snapshot.json`. В файл попадают только проценты и время сброса.

## Проверка

```bash
cd scripts
python -B -m unittest test_plan_wave test_usage_scripts
python -B discover.py
```

## Состав

| Файл | Назначение |
|---|---|
| `SKILL.md` | Основной порядок работы координатора |
| `references/executors.md` | Как запускать субагентов, Claude Code и Codex; маршрутизация по возможностям |
| `references/routing.md` | Выбор модели и уровня рассуждения |
| `references/usage-limits.md` | Как узнавать оставшиеся лимиты, не нарушая доступов |
| `references/planner.md` | Формат манифеста для `plan_wave.py` |
| `references/sources.md` | Документация, на которую опирается навык |
| `assets/` | Шаблоны задания, отчёта, журнала и пример манифеста |
| `scripts/` | Обнаружение, планировщик, чтение лимитов, тесты |
| `agents/openai.yaml` | Карточка навыка для интерфейса Codex |

## Ограничения

- Навык — это инструкции и офлайн-скрипты, а не сервис. Он не держит блокировки и не контролирует расходы сам.
- Генерация картинки через `codex exec` проверена одним пробным запуском 21.10.2026. Приложения Codex вроде Canva через `codex exec` не проверялись.
- Полный запуск `claude -p` по рецепту не проверялся, потому что это платный прогон. Проверены флаги из `--help` и передача аргументов в PowerShell.
- Формат логов Codex, который читает `codex_usage.py`, не документирован и может измениться. Тогда скрипт сообщит «не найдено».

Лицензия: MIT.
