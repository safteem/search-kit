"""Где скрипты search-kit берут ключи сервисов. Значения ключей никогда не печатаются.

Порядок поиска для каждого ключа:
1. файл ключей — первый существующий из списка: путь в переменной SEARCH_KIT_CREDENTIALS,
   ~/.search-kit/credentials.md, ~/.search-kit/.env (сюда пишет хранилище секретов BB:
   `bb secret request ИМЯ --write-env ~/.search-kit/.env`), ~/.claude/credentials.md; строка вида ИМЯ=значение;
2. переменная окружения с тем же именем (запасной путь для оболочек без файла ключей).
Облачная сессия Claude Code (CLAUDE_CODE_REMOTE=true) без ключа: запрос уходит без ключа, его добавляет прокси.

python -I keys.py check        — какие ключи найдены и где (без значений)
python -I keys.py test         — работают ли ключи (бесплатные запросы, без значений)
python -I keys.py add-missing [keenable tavily firecrawl]
                               — дописать пустые строки для недостающих ключей (и ключей этих подключений)
"""
import os
import re
import sys
from pathlib import Path

NAMES = {
    "SCRAPECREATORS_API_KEY": "ScrapeCreators (Google, Reddit, YouTube, Threads, посты соцсетей)",
    "APIFY_TOKEN": "Apify (X, ответы Threads, карты)",
    "GROQ_API_KEY": "Groq (расшифровка речи)",
}
# ключи подключений MCP — только если подключение ставит скил setup (по имени сервиса, не ключа)
OPTIONAL = {"keenable": "KEENABLE_API_KEY", "tavily": "TAVILY_API_KEY", "firecrawl": "FIRECRAWL_API_KEY"}


def files():
    found = []
    custom = os.environ.get("SEARCH_KIT_CREDENTIALS")
    for p in ([Path(custom).expanduser()] if custom else []) + [
            Path.home() / ".search-kit" / "credentials.md", Path.home() / ".search-kit" / ".env",
            Path.home() / ".claude" / "credentials.md"]:
        if p.is_file() and p not in found:
            found.append(p)
    return found


def _from_text(name, text):
    m = re.search(rf"^\s*{name}\s*=\s*['\"`]?([^\s'\"`]+)", text, re.M)
    if m:
        return m.group(1)
    if name == "APIFY_TOKEN":  # токен Apify узнаётся по началу apify_api_, как бы ни была подписана строка
        tokens = set(re.findall(r"apify_api_[A-Za-z0-9]+", text))
        if len(tokens) == 1:
            return tokens.pop()
    return None


def find(name):
    """(значение, откуда) или (None, None)."""
    for p in files():
        value = _from_text(name, p.read_text(encoding="utf-8-sig", errors="replace"))
        if value:
            return value, str(p)
    value = os.environ.get(name)
    if value:
        return value, "переменная окружения"
    return None, None


def remote():
    return os.environ.get("CLAUDE_CODE_REMOTE") == "true"


def require(name):
    """Значение ключа или None в облаке Claude Code (ключ добавит прокси); иначе понятная ошибка."""
    value, _ = find(name)
    if value or remote():
        return value
    sys.exit(f"Нет ключа {name} ({NAMES.get(name, name)}). Впишите строку {name}=... в файл ключей "
             f"(~/.claude/credentials.md или ~/.search-kit/credentials.md) или задайте переменную окружения. "
             f"Настройка по шагам — скил setup.")


def add_missing(extra=()):
    """Дописать пустые строки ИМЯ= для недостающих ключей в файл ключей (создать файл, если его нет). Значения не читает
    вслух и не трогает существующие строки."""
    existing = files()
    target = existing[0] if existing else (
        Path.home() / ".claude" / "credentials.md" if (Path.home() / ".claude").is_dir()
        else Path.home() / ".search-kit" / "credentials.md")
    missing = [n for n in NAMES if not find(n)[0]] + [
        OPTIONAL[s] for s in extra if s in OPTIONAL and not find(OPTIONAL[s])[0]]
    if not missing:
        print("Все ключи на месте, файл не менялся:", target)
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    text = target.read_text(encoding="utf-8-sig") if target.exists() else (
        "# Ключи сервисов. Вписывайте значения сами, в текстовом редакторе; агенту их не показывайте.\n")
    lines = "".join(f"{n}=\n" for n in missing if not re.search(rf"^\s*{n}\s*=", text, re.M))
    if lines:
        target.write_text(text.rstrip("\n") + "\n\n# search-kit\n" + lines, encoding="utf-8")
    print(f"Файл ключей: {target}\nДописаны пустые строки: {', '.join(missing)}. Откройте файл в редакторе и вставьте ключи после «=».")


def test():
    """Живая проверка ключей бесплатными запросами; значения не печатаются."""
    import json
    import urllib.request
    checks = {
        "SCRAPECREATORS_API_KEY": ("https://api.scrapecreators.com/v1/account/credit-balance", "x-api-key", "{}"),
        "APIFY_TOKEN": ("https://api.apify.com/v2/users/me", "Authorization", "Bearer {}"),
        "GROQ_API_KEY": ("https://api.groq.com/openai/v1/models", "Authorization", "Bearer {}"),
    }
    for name, (url, header, fmt) in checks.items():
        value, _ = find(name)
        if not value:
            print(f"{name}: НЕТ ключа")
            continue
        req = urllib.request.Request(url, headers={header: fmt.format(value), "User-Agent": "search-kit/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.loads(r.read() or b"{}")
            extra = f", кредитов: {data.get('creditCount')}" if "creditCount" in data else ""
            print(f"{name}: работает{extra}")
        except Exception as e:  # noqa: BLE001 — показываем только код ошибки, без ключа
            print(f"{name}: НЕ работает ({getattr(e, 'code', type(e).__name__)})")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    cmd = sys.argv[1:]
    if cmd[:1] == ["add-missing"]:
        add_missing(cmd[1:])
    elif cmd == ["test"]:
        test()
    elif cmd == ["check"]:
        print("Файлы ключей:", ", ".join(str(p) for p in files()) or "не найдены")
        for name, what in NAMES.items():
            _, where = find(name)
            print(f"{name}: {'есть, ' + where if where else 'НЕТ'} — {what}")
    else:
        sys.exit("python -I keys.py check | test | add-missing [keenable tavily firecrawl]")
