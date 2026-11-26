"""Где скрипты search-kit берут личные данные и ключи сервисов. Значения ключей никогда не печатаются.

Личные данные пакета (настройки, карта чатов, ключи) — в папке my/ внутри папки пакета (копия репозитория);
my/ в git не попадает, образец — my.example/. Как скрипт находит my/:
1. переменная окружения SEARCH_KIT_HOME;
2. файл kit-home.txt в папке скила (адрес пакета; его кладёт tools/install.py, копии скилов в BB и в плагине
   Claude Code везут его с собой);
3. скрипт запущен прямо из папки пакета: <пакет>/my;
4. иначе ~/.search-kit (старые установки).

Ключ ищется так (как у last30days): переменная окружения с тем же именем -> my/.env -> общий файл ключей,
указанный в my/.env строкой KEYS_FILE=<путь> (или в переменной SEARCH_KIT_KEYS_FILE). Строки вида ИМЯ=значение.
Уже настроенные ключи (переменные среды, свой общий файл) вводить заново не нужно.
Облачная сессия Claude Code (CLAUDE_CODE_REMOTE=true) без ключа: запрос уходит без ключа, его добавляет прокси.

python -I keys.py where        — где папка личных данных и файлы ключей
python -I keys.py check        — какие ключи найдены и где (без значений)
python -I keys.py test         — работают ли ключи (бесплатные запросы, без значений)
python -I keys.py add-missing [keenable tavily firecrawl]
                               — дописать пустые строки для недостающих ключей
"""
import os
import re
import sys
from pathlib import Path

ENV = "." + "env"
NAMES = {
    "SCRAPECREATORS_API_KEY": "ScrapeCreators (Google, Reddit, YouTube, Threads, посты соцсетей)",
    "APIFY_TOKEN": "Apify (X, ответы Threads, карты)",
    "GROQ_API_KEY": "Groq (расшифровка речи)",
    "KEENABLE_API_KEY": "Keenable (быстрый поиск; подключение агента)",
    "TAVILY_API_KEY": "Tavily (чтение страниц; подключение агента)",
    "FIRECRAWL_API_KEY": "Firecrawl (живые цифры, защищённые сайты; подключение агента)",
}
# ключи подключений MCP — только если подключение ставит скил search-kit-setup (по имени сервиса, не ключа)
OPTIONAL = {"keenable": "KEENABLE_API_KEY", "tavily": "TAVILY_API_KEY", "firecrawl": "FIRECRAWL_API_KEY"}


def kit_home(skill_dir=None):
    """Папка личных данных пакета (my/)."""
    if os.environ.get("SEARCH_KIT_HOME"):
        return Path(os.environ["SEARCH_KIT_HOME"]).expanduser()
    here = Path(__file__).resolve()
    dirs = [Path(skill_dir)] if skill_dir else []
    dirs += [Path(__file__).absolute().parents[1], here.parents[1]]
    for d in dirs:
        marker = d / "kit-home.txt"
        if marker.is_file():
            root = Path(marker.read_text(encoding="utf-8-sig").strip()).expanduser()
            if root.is_dir():
                return root / "my"
    root = here.parents[3]
    if (root / "my.example").is_dir():
        return root / "my"
    return Path.home() / ".search-kit"


def common_file():
    """Общий файл ключей: переменная SEARCH_KIT_KEYS_FILE или строка KEYS_FILE=<путь> в my/.env."""
    common = os.environ.get("SEARCH_KIT_KEYS_FILE")
    own = kit_home() / ENV
    if not common and own.is_file():
        m = re.search(r"^[ \t]*KEYS_FILE[ \t]*=[ \t]*['\"]?([^'\"\r\n]+?)['\"]?[ \t]*$",
                      own.read_text(encoding="utf-8-sig", errors="replace"), re.M)
        common = m.group(1) if m else None
    return Path(common).expanduser() if common else None


def files():
    """Файлы ключей по порядку: my/.env, затем общий файл (KEYS_FILE)."""
    found = []
    own = kit_home() / ENV
    if own.is_file():
        found.append(own)
    common = common_file()
    if common and common.is_file() and common not in found:
        found.append(common)
    if not found:  # старая установка без my/
        for p in (Path.home() / ".search-kit" / ENV, Path.home() / ".search-kit" / "credentials.md"):
            if p.is_file():
                found.append(p)
    return found


def _from_text(name, text):
    m = re.search(rf"^[ \t]*{name}[ \t]*=[ \t]*['\"`]?([^\s'\"`]+)", text, re.M)
    if m:
        return m.group(1)
    if name == "APIFY_TOKEN":  # токен Apify узнаётся по началу apify_api_, как бы ни была подписана строка
        tokens = set(re.findall(r"apify_api_[A-Za-z0-9]+", text))
        if len(tokens) == 1:
            return tokens.pop()
    return None


def find(name):
    """(значение, откуда) или (None, None). Переменная окружения первой: уже настроенный ключ не вводить заново."""
    value = os.environ.get(name)
    if value:
        return value, "переменная окружения"
    for p in files():
        value = _from_text(name, p.read_text(encoding="utf-8-sig", errors="replace"))
        if value:
            return value, str(p)
    return None, None


def remote():
    return os.environ.get("CLAUDE_CODE_REMOTE") == "true"


def require(name):
    """Значение ключа или None в облаке Claude Code (ключ добавит прокси); иначе понятная ошибка."""
    value, _ = find(name)
    if value or remote():
        return value
    sys.exit(f"Нет ключа {name} ({NAMES.get(name, name)}). Впишите строку {name}=... в файл ключей "
             f"{common_file() or kit_home() / ENV} или задайте переменную окружения. "
             f"Настройка по шагам — скил search-kit-setup.")


def add_missing(extra=()):
    """Дописать пустые строки ИМЯ= для недостающих ключей в файл ключей (создать файл, если его нет). Значения не читает
    вслух и не трогает существующие строки."""
    target = common_file() or kit_home() / ENV  # общий файл, если указан, иначе my/env
    missing = [n for n in NAMES if not find(n)[0]] + [
        OPTIONAL[s] for s in extra if s in OPTIONAL and not find(OPTIONAL[s])[0]]
    if not missing:
        print("Все ключи на месте, файл не менялся:", target)
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    text = target.read_text(encoding="utf-8-sig") if target.exists() else (
        "# Ключи сервисов. Вписывайте значения сами, в текстовом редакторе; агенту их не показывайте.\n")
    lines = "".join(f"{n}=\n" for n in missing if not re.search(rf"^[ \t]*{n}[ \t]*=", text, re.M))
    if lines:
        target.write_text(text.rstrip("\n") + "\n\n# search-kit\n" + lines, encoding="utf-8")
        print(f"Файл ключей: {target}\nДописаны пустые строки: {', '.join(missing)}.")
    else:
        print(f"Файл ключей: {target}\nСтроки уже есть, но пустые: {', '.join(missing)}.")
    print("Откройте файл сами в Блокноте (Win+R, затем: notepad <путь выше>; на Mac: open -e <путь>), вставьте ключи "
          "после «=» и сохраните. Агенту файл не показывайте: охранник ему это и не даст. Есть свой общий файл ключей — вместо этого впишите в my/.env строку KEYS_FILE=<путь к нему>.")


def test():
    """Живая проверка ключей бесплатными запросами; значения не печатаются."""
    import json
    import urllib.request
    checks = {
        "SCRAPECREATORS_API_KEY": ("https://api.scrapecreators.com/v1/account/credit-balance", "x-api-key", "{}"),
        "APIFY_TOKEN": ("https://api.apify.com/v2/users/me", "Authorization", "Bearer {}"),
        "GROQ_API_KEY": ("https://api.groq.com/openai/v1/models", "Authorization", "Bearer {}"),
        "TAVILY_API_KEY": ("https://api.tavily.com/usage", "Authorization", "Bearer {}"),
        "FIRECRAWL_API_KEY": ("https://api.firecrawl.dev/v1/team/credit-usage", "Authorization", "Bearer {}"),
    }
    optional = set()
    print("KEENABLE_API_KEY: отдельной бесплатной проверки нет; Keenable работает и без ключа (с лимитом), "
          "проверяется пробным поиском")
    for name, (url, header, fmt) in checks.items():
        value, _ = find(name)
        if not value:
            print(f"{name}: НЕТ ключа" + (" (нужен, только если подключение ставили с ключом из файла)" if name in optional else ""))
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
    elif cmd == ["where"]:
        print("Папка личных данных:", kit_home())
        print("Общий файл ключей:", common_file() or "не указан")
        print("Файлы ключей:", ", ".join(str(p) for p in files()) or "не найдены")
    elif cmd == ["check"]:
        print("Файлы ключей:", ", ".join(str(p) for p in files()) or "не найдены")
        for name, what in NAMES.items():
            _, where = find(name)
            print(f"{name}: {'есть, ' + where if where else 'НЕТ'} — {what}")
    else:
        sys.exit("python -I keys.py where | check | test | add-missing [keenable tavily firecrawl]")
