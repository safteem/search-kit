# Claude Code: что особенного

Установка: `python -I "{пакет}/tools/install.py" claude` (шаг 3 скила). Пакет ставится плагином из папки пакета:
скилы, помощники `search-kit:researcher` и `search-kit:social-researcher` и охранник (`hooks/guard.py`: не даёт
командам агента открыть файл ключей и ограничивает помощников). Проверка: `claude plugin list` показывает `search-kit`.
Если такие же скилы лежат ещё и в `~/.claude/skills` (старая ручная копия): будут дубли, предложить убрать старую
копию в резервную папку (только после «да»).

## Подключения поиска
Сначала посмотреть, что уже есть: `claude mcp list`. Есть под именами `keenable`, `tavily`, `firecrawl`: не дублировать.
- Статус «Connected» ещё не значит, что ключ верный (Firecrawl показывает его и без ключа): проверка в конце.
- Помощники пакета видят инструменты только под этими тремя именами. Подключены под другими именами (например
  коннекторами claude.ai): основному чату это не мешает, а помощники их не увидят; предложить добавить под
  стандартным именем, а лишнее убрать (каждое подключение тратит токены на описания инструментов).
- Ключ читает сама оболочка через `headersHelper`, а не агент, и не хранится в настройках:
  `claude mcp add-json --scope user tavily '{"type":"http","url":"https://mcp.tavily.com/mcp/","headersHelper":"python -I \"{пакет}/skills/search-kit-setup/scripts/mcp_header.py\" tavily"}'`
  Firecrawl: адрес `https://mcp.firecrawl.dev/v2/mcp`, имя `firecrawl`. Keenable без ключа:
  `claude mcp add --scope user --transport http keenable https://api.keenable.ai/mcp`; с ключом: как Tavily, адрес
  `https://api.keenable.ai/mcp`, имя `keenable`. На Mac и Linux в `headersHelper` — `python3`.
- Подключения появятся в следующей сессии: там по одному пробному вызову каждого (поиск одного слова). 401: ключ неверный.

## Обновление
`git -C "{пакет}" pull`, затем `python -I "{пакет}/tools/install.py" claude` (обновит маркетплейс и плагин),
перезапуск сессии.
