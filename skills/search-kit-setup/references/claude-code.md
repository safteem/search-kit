# Путь установки: Claude Code

Читать, если пакет ставится в Claude Code (приложение Claude, вкладка Code, или `claude` в терминале) без BB.

## Установка пакета
Пакет ставится плагином, обычно это уже сделано до запуска search-kit-setup:
`claude plugin marketplace add <владелец>/search-kit`, затем `claude plugin install search-kit@search-kit-marketplace`.
Плагин приносит сразу всё: скилы, помощников `search-kit:researcher` и `search-kit:social-researcher` и охранник
(`hooks/guard.py`: не даёт командам агента открыть файл ключей). Проверка: в списке скилов есть `search-kit:search-kit-setup`.
Если такие же скилы лежат ещё и в `~/.claude/skills` (старая ручная копия): сказать человеку, что будут дубли,
и предложить убрать старую копию в резервную папку (только после «да»).

## Ключи: файл
1. `python -I "{скилы}/social-capture/scripts/keys.py" check`: что уже есть (без значений).
2. Недостающее: `python -I "{скилы}/social-capture/scripts/keys.py" add-missing` (и через пробел `tavily firecrawl`, если эти подключения будут с ключом из
   файла). Скрипт сам найдёт или создаст файл ключей (`~/.search-kit/credentials.md`), допишет пустые строки и
   напечатает путь. Существующее не трогает.
3. Человек сам открывает файл: Windows: Win+R, `notepad <путь, который напечатал скрипт>`, Enter; Mac:
   `open -e <путь>`. Вставляет ключи после «=» без пробелов и кавычек, сохраняет. Агент файл не открывает и
   не запускает для него редактор (охранник это и не даст): только говорит, что сделать.
4. `python -I "{скилы}/social-capture/scripts/keys.py" test`: живая проверка каждого ключа бесплатным запросом.

## Подключения поиска (MCP)
Сначала посмотреть, что уже есть: `claude mcp list`. Есть под именами `keenable`, `tavily`, `firecrawl`: не дублировать.
- Статус «Connected» ещё не значит, что ключ верный (Firecrawl показывает его и без ключа): проверка в конце.
- Помощники пакета видят инструменты только под этими тремя именами. Подключены через claude.ai под другими
  именами: основному чату это не мешает, а помощники их не увидят; предложить добавить и под стандартным именем
  (а лишнее подключение потом убрать, чтобы не было дублей: каждое тратит токены на описания инструментов).
- Скопировать в постоянную папку `~/.search-kit/bin/` два файла: `{скилы}/search-kit-setup/scripts/mcp_header.py` и
  `{скилы}/social-capture/scripts/keys.py` (путь в плагине меняется при обновлениях, а этот нет).
- По одной команде на сервис, ключ читает сама оболочка, а не агент:
  `claude mcp add-json --scope user tavily '{"type":"http","url":"https://mcp.tavily.com/mcp/","headersHelper":"python -I \"<домашняя папка>/.search-kit/bin/mcp_header.py\" tavily"}'`
  Firecrawl: адрес `https://mcp.firecrawl.dev/v2/mcp`, имя `firecrawl`. Keenable без ключа:
  `claude mcp add --scope user --transport http keenable https://api.keenable.ai/mcp`; с ключом: как Tavily, адрес
  `https://api.keenable.ai/mcp`, имя `keenable`.
- Подключения появятся в следующей сессии. Там по одному пробному вызову каждого (поиск одного слова). 401: ключ неверный.

## Обновление
«обнови search-kit» → `claude plugin marketplace update search-kit-marketplace`, затем
`claude plugin update search-kit@search-kit-marketplace`, перезапуск сессии. Если `mcp_header.py` или `keys.py`
поменялись: снова скопировать их в `~/.search-kit/bin/`.
