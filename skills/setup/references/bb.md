# Путь установки: BB (getbb.app)

Читать, если setup запущен внутри BB (есть переменная окружения `BB_THREAD_ID` или команда `bb`). Пакет живёт в BB
сам по себе: скилы, ключи и личный файл лежат в местах BB и `~/.search-kit`, а не в настройках одного агента.

## Как BB устроен (сказать человеку коротко)
- **Скилы общие для всех агентов.** BB сам подставляет свои скилы в любой тред: Claude Code, Codex, Pi, агенты
  из реестра ACP (Gemini CLI, Antigravity и другие). Поставил один раз: видят все, в том числе новый агент.
- **Подключения (MCP) у каждого агента свои.** Общего списка подключений, который BB раздаёт всем агентам, нет.
  Плагин `mcp-manager` (по желанию: `bb plugin install git:https://github.com/sankalpaacharya/bb-mcp-manager.git`)
  показывает подключения всех агентов одним списком и умеет их переподключать и удалять, но не копирует из одного
  агента в другой. Поэтому подключения ставятся отдельно для каждого агента, которым человек пользуется.
- **Пакет работает и без подключений:** Google, YouTube, Reddit, X, Threads, карты идут скриптами пакета по ключам,
  а им всё равно, какой агент их запускает. Без Keenable, Tavily и Firecrawl агент берёт свой встроенный поиск.

## Установка скилов
Скилы BB лежат по папке на скил в `~/.bb/skills` (так же ставит `bb skill install`). Если `~/.bb/skills` у человека
ярлык на свою папку скилов (например, `D:\labs\60-tools\skills`), скилы лягут туда: это нормально, остальные скилы
никто не трогает.
1. Пакет есть в каталоге skills.sh: `bb skill search search-kit`, затем `bb skill install <id>` для каждого скила.
2. Иначе: `git clone https://github.com/<владелец>/search-kit` в любую папку, затем
   `python -I "<папка пакета>/tools/install.py" "<домашняя папка>/.bb/skills"` (сначала можно с `--dry-run`: покажет,
   что сделает). Старые версии тех же скилов скрипт уберёт в `~/.search-kit/backups/<дата>/`.
3. Проверка: `bb skill list` показывает `search-and-read-web`, `social-capture`, `deep-research`, `telegram-search`,
   `setup` без дублей. Дубль (такой же скил ещё в `~/.claude/skills` или в плагине): BB покажет оба, если текст
   разный; предложить убрать старую копию в резервную папку (только после «да»).

## Ключи: хранилище секретов BB
1. `python -I "{скилы}/social-capture/scripts/keys.py" check`: что уже есть (без значений).
2. Недостающее спросить формой BB, одной командой на все ключи:
   `bb secret request SCRAPECREATORS_API_KEY APIFY_TOKEN GROQ_API_KEY --write-env "<домашняя папка>/.search-kit/.env" --purpose "Ключи для поиска search-kit" --describe "SCRAPECREATORS_API_KEY=Google, YouTube, Reddit, соцсети" --describe "APIFY_TOKEN=X, ответы Threads, карты" --describe "GROQ_API_KEY=расшифровка речи"`
   (добавить `TAVILY_API_KEY`, `FIRECRAWL_API_KEY`, `KEENABLE_API_KEY`, если эти подключения будут с ключом).
   Человек вставляет ключи в форму BB, агент значений не видит. BB пишет файл с правами только для владельца и
   не трогает уже вписанные строки. Скрипты пакета сами читают этот файл.
3. `keys.py test`: живая проверка каждого ключа бесплатным запросом.
Честно про защиту: охранник пакета (запрет агенту открывать файл ключей) работает только как хук Claude Code. Если
плагин в Claude Code не стоит, файл `.env` защищает только правило в скилах: агент его не открывает и не выводит.

## Подключения поиска (MCP): для каждого агента
Сначала посмотреть, что уже есть: `bb mcp-manager list` (если плагин стоит) или команда списка самого агента.
Есть под именами `keenable`, `tavily`, `firecrawl`: не дублировать. Ключ всегда читает оболочка, а не текст конфига.
- Скопировать в постоянную папку `~/.search-kit/bin/` два файла: `{скилы}/setup/scripts/mcp_header.py` и
  `{скилы}/social-capture/scripts/keys.py`.
- **Claude Code в BB:** те же команды `claude mcp add-json ...` и `claude mcp add ...`, что в `references/claude-code.md`,
  раздел «Подключения поиска».
- **Codex:** в `~/.codex/config.toml` раздел `[mcp_servers.tavily]`, `url = "https://mcp.tavily.com/mcp/"`,
  `bearer_token_env_var = "TAVILY_API_KEY"` (так же Firecrawl и Keenable). Переменную окружения человек задаёт сам
  в настройках системы.
- **Агенты из реестра ACP** (`bb acp registry`, `bb acp add <id>`: Gemini CLI, Antigravity и другие): подключения
  по инструкции к MCP этого агента, ключ так же через переменную окружения. Для Keenable без ключа хватает адреса
  `https://api.keenable.ai/mcp`.
- Проверка в новом треде этого агента: по одному пробному вызову каждого (поиск одного слова). 401: ключ неверный.

## Помощники для deep-research
Именованные помощники `search-kit:researcher` и `search-kit:social-researcher` есть только в плагине Claude Code.
В BB deep-research сам запускает обычного помощника и вставляет правила из `agents/researcher.md` в его задание:
ставить ничего не нужно.

## Обновление
`git pull` в папке пакета, затем снова `tools/install.py` в `~/.bb/skills` (старая версия уйдёт в
`~/.search-kit/backups/`). Если ставили из skills.sh: `bb skill install <id>` заново. Если поменялись
`mcp_header.py` или `keys.py`: снова скопировать их в `~/.search-kit/bin/`.
