"""Охранник search-kit: проверка вызова инструмента до того, как он выполнится.

Скил — это текст: он может попросить модель, но не может ей физически запретить. Запрещает программа-оболочка,
которая запускает инструменты: перед каждым вызовом она передаёт этому скрипту описание вызова (JSON на вход),
а скрипт отвечает «нельзя» с причиной. Ядро ниже не зависит от оболочки; формат входа и ответа — у Claude Code
(и Claude Code внутри BB) и у Codex одинаковый: PreToolUse, hookSpecificOutput.permissionDecision.

Два слоя:
1. Для всех (и основной чат, и помощники): файл ключей нельзя читать и упоминать в командах; переменные с ключами
   нельзя выводить. Запись заметок, где встречается слово, не запрещается.
2. Только для помощников ресерча `researcher` и `social-researcher` (поле agent_type входа; в Claude Code плагин
   добавляет приставку `search-kit:`): писать — только в папку исследования или временную папку; читать — только
   скилы пакета, личные настройки пакета и папку исследования; из команд — только скрипты пакета (и ffmpeg/ffprobe
   у social-researcher), по одной, без связок; инструменты подключений с «отправкой» — нельзя.
Ошибка внутри проверки для помощника = запрет (защита не отключается молча).

python -I guard.py          — режим хука (вход на stdin)
python -I guard_samples.py  — проверка образцами
"""
import json
import os
import re
import shlex
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # корень пакета: skills/, agents/, hooks/
HELPERS = {"researcher", "social-researcher"}
SKILLS = ("search-and-read-web", "social-capture", "deep-research", "telegram-search", "setup")
RESEARCH_DIRS = {"research", "research_notes", "reports"}
APIFY_LIMIT_USD = 0.5

# --- слой 1: секреты ---------------------------------------------------------------------------------------------
SECRET_FILES = re.compile(r"credentials\.md|\.encryption-key|\.agent-reach|\.agent-browser", re.I)
SECRET_FILES_CASE = re.compile(r"\.session(-journal)?\b|(?<![\w.$])\.env\b(?!\.example)")  # requests.Session, os.environ — можно
KEY_VARS = re.compile(r"\b(SCRAPECREATORS_API_KEY|APIFY_TOKEN|GROQ_API_KEY|TAVILY_API_KEY|FIRECRAWL_API_KEY|"
                      r"KEENABLE_API_KEY|GITHUB_TOKEN|TELEGRAM_API_HASH|TELEGRAM_SESSION_STRING)\b")
# вывод всех переменных окружения разом (там могут быть ключи); отдельные переменные с ключами ловит KEY_VARS
PRINT_ENV = re.compile(r"(^|[;&|(]\s*)(env|printenv|set|export\s+-p|declare\s+-x)\s*($|[;&|)])|"
                       r"\b(gci|ls|dir|get-childitem)\s+env:", re.I)

# --- слой 2: помощники -------------------------------------------------------------------------------------------
TOOLS_WRITE = {"Write", "Edit", "MultiEdit", "NotebookEdit", "apply_patch"}
TOOLS_READ = {"Read", "Glob", "Grep", "LS"}
SEND_VERBS = re.compile(r"(^|[_\-])(send|post|publish|forward|reply|comment|share|upload|submit|broadcast|tweet|"
                        r"create|delete|update|write|push|edit|remove|join|leave)", re.I)
FORBIDDEN_CHARS = set(";&|`$<>\n\r")
PYTHON = re.compile(r"^(.*/)?(python3?|py)(\.exe)?$", re.I)
COMMON_SCRIPTS = {"sc.py", "apify.py", "summary.py", "post.py", "maps.py", "gh_repos.py", "yt_live.py", "keys.py"}
SOCIAL_SCRIPTS = COMMON_SCRIPTS | {"groq.py", "get_video.py", "tg_search.py"}
FFMPEG_FLAGS = {"-y", "-n", "-hide_banner", "-an", "-vn", "-sn", "-dn", "-nostdin"}


def norm(path, cwd=""):
    """Абсолютный путь с прямыми косыми, без изменения регистра; относительный — от cwd."""
    path = str(path or "").strip().strip("'\"").replace("\\", "/")
    if path.startswith("~"):
        path = str(Path.home()).replace("\\", "/") + path[1:]
    if re.match(r"^/[a-zA-Z]/", path):  # Git Bash: /c/dir -> C:/dir
        path = path[1].upper() + ":" + path[2:]
    if not (path.startswith("/") or re.match(r"^[a-zA-Z]:/", path)):
        path = (str(cwd).replace("\\", "/").rstrip("/") + "/" + path) if cwd else path
    return path


def parts(path):
    return [p.lower() for p in path.split("/") if p]


def temp_dirs():
    dirs = {"/tmp", norm(tempfile.gettempdir())}
    for var in ("TEMP", "TMP", "TMPDIR"):
        if os.environ.get(var):
            dirs.add(norm(os.environ[var]))
    return {d.lower().rstrip("/") for d in dirs}


def is_temp(path):
    low = path.lower()
    return any(low.startswith(d + "/") for d in temp_dirs())


def write_ok(path, cwd):
    """Помощник пишет только в папку исследования или временную папку; не в служебные папки и без «..»."""
    if not path or "\x00" in path:
        return False
    p = norm(path, cwd)
    ps = parts(p)
    if ".." in ps or ".claude" in ps or ".search-kit" in ps or ".codex" in ps or SECRET_FILES.search(p):
        return False
    return bool(RESEARCH_DIRS & set(ps[:-1])) or is_temp(p)


def in_skills(p):
    low = p.lower()
    root = str(ROOT).replace("\\", "/").lower()
    if low == root or low.startswith(root + "/"):
        return True
    # копия скилов пакета в другой папке (например общая папка скилов оболочки): …/skills/<скил пакета>/…
    return re.search(r"/skills/(" + "|".join(SKILLS) + r")(/|$)", low) is not None


def read_ok(path, cwd):
    if not path:
        return False
    p = norm(path, cwd)
    ps = parts(p)
    if ".." in ps or SECRET_FILES.search(p) or SECRET_FILES_CASE.search(p):
        return False
    if in_skills(p) or bool(RESEARCH_DIRS & set(ps)):
        return True
    home_kit = (str(Path.home()).replace("\\", "/") + "/.search-kit/").lower()
    return p.lower().startswith(home_kit) and ps[-1].endswith(".md")  # личные настройки и карта чатов, не JSON


def trusted_script(token, cwd):
    """Имя скрипта, если путь ведёт к скрипту пакета (…/skills/<скил>/scripts/<имя>.py вне папок исследования
    и временных), иначе None. Помощник не может подложить свой скрипт: писать он может только туда, откуда запуск запрещён."""
    p = norm(token, cwd)
    ps = parts(p)
    if ".." in ps or RESEARCH_DIRS & set(ps) or is_temp(p):
        return None
    m = re.search(r"/skills/(" + "|".join(SKILLS) + r")/scripts/([a-z_]+\.py)$", p, re.I)
    return m.group(2).lower() if m else None


def https(url):
    return url.startswith("https://") and not any(c.isspace() for c in url)


def outfile(arg, cwd, what):
    return None if write_ok(arg, cwd) else f"{what}: файл результата только в папке исследования research/… или во временной папке"


def check_script(agent, name, args, cwd):
    allowed = SOCIAL_SCRIPTS if agent == "social-researcher" else COMMON_SCRIPTS
    if name not in allowed:
        return f"скрипт {name} помощнику {agent} не разрешён"
    if name == "keys.py":
        return None if args == ["check"] else "keys.py: только check"
    if name == "sc.py":
        if args == ["balance"]:
            return None
        if len(args) < 2:
            return "sc.py: нужны адрес сервиса и файл ответа"
        if not re.fullmatch(r"v\d/[a-z0-9_/\-]+", args[0]) or "download" in args[0]:
            return f"sc.py: адрес сервиса {args[0]!r} не разрешён"
        if any("=" not in a for a in args[2:]):
            return "sc.py: параметры только в виде ключ=значение"
        return outfile(args[1], cwd, "sc.py")
    if name == "apify.py":
        if args == ["usage"] or (len(args) == 2 and args[0] in ("store", "schema")):
            return None
        if len(args) == 5 and args[0] == "run":
            _, actor, inp, out, limit = args
            if not re.fullmatch(r"[\w.\-]+/[\w.\-]+", actor):
                return "apify.py: имя сборщика владелец/имя"
            if not (read_ok(inp, cwd) or write_ok(inp, cwd)):
                return "apify.py: вход только из папки исследования, временной папки или примеров пакета"
            try:
                if not 0 < float(limit) <= APIFY_LIMIT_USD:
                    return f"apify.py: лимит больше {APIFY_LIMIT_USD} долл. — только с вопросом в основном чате"
            except ValueError:
                return "apify.py: последний аргумент — лимит в долларах"
            return outfile(out, cwd, "apify.py")
        return "apify.py: разрешены usage, store, schema и run с лимитом последним аргументом"
    if name == "summary.py":
        if len(args) < 3:
            return "summary.py: <вопрос> <выход.md> <файл>::<площадка>::..."
        bad = [a for a in args[2:] if not (read_ok(a.split("::")[0], cwd) or write_ok(a.split("::")[0], cwd))]
        return f"summary.py: входные файлы только из папки исследования или временной: {bad[0]!r}" if bad else \
            outfile(args[1], cwd, "summary.py")
    if name == "post.py":
        files = [a for a in args if not a.startswith("--") and not re.fullmatch(r"[\w\-]+", a)]
        bad = [a for a in files if not (read_ok(a, cwd) or write_ok(a, cwd))]
        return f"post.py: файлы только из папки исследования или временной: {bad[0]!r}" if bad else None
    if name == "maps.py":
        if len(args) < 3 or args[0] not in ("places", "reviews"):
            return "maps.py: places|reviews <выход.md> <файл.json> ..."
        return outfile(args[1], cwd, "maps.py")
    if name == "gh_repos.py":
        return None if args and args[0] in ("find", "check", "issues") else "gh_repos.py: find|check|issues ..."
    if name == "yt_live.py":
        return None if args and all(re.fullmatch(r"[\w\-]{6,20}", a) for a in args) else "yt_live.py: только id роликов"
    if name == "groq.py":
        if len(args) not in (3, 4) or args[0] not in ("file", "url"):
            return "groq.py: file|url <источник> <выход.json> [язык]"
        if args[0] == "url" and not https(args[1]):
            return "groq.py: ссылка только https"
        if args[0] == "file" and not write_ok(args[1], cwd):
            return "groq.py: файл только из папки исследования или временной"
        return outfile(args[2], cwd, "groq.py")
    if name == "get_video.py":
        if len(args) not in (2, 3) or not https(args[0]):
            return "get_video.py: <https-ссылка> <файл> [referer]"
        return outfile(args[1], cwd, "get_video.py")
    if name == "tg_search.py":
        if len(args) < 2 or args[0] not in ("find", "recent", "post", "global"):
            return "tg_search.py: find|recent|post|global ПАПКА ..."
        return outfile(args[1] + "/x", cwd, "tg_search.py")
    return f"скрипт {name} не разрешён"


def check_ffmpeg(prog, args, cwd):
    if prog == "ffprobe":
        bad = [t for t in args if not t.startswith("-") and "/" in t.replace("\\", "/") and not write_ok(t, cwd)]
        return f"ffprobe: файл только из папки исследования или временной, не {bad[0]!r}" if bad else None
    i, outputs = 0, 0
    while i < len(args):
        t = args[i]
        if t.startswith("-") and t not in FFMPEG_FLAGS:
            if i + 1 >= len(args):
                return f"ffmpeg: у параметра {t} нет значения"
            if t == "-i" and not write_ok(args[i + 1], cwd):
                return f"ffmpeg: вход только из папки исследования или временной, не {args[i + 1]!r}"
            i += 2
            continue
        if not t.startswith("-"):
            outputs += 1
            if not write_ok(t, cwd):
                return f"ffmpeg: результат только в папку исследования или временную, не {t!r}"
        i += 1
    return None if outputs else "ffmpeg: не указан файл результата"


def check_bash_helper(agent, command, cwd):
    if not command or any(c in FORBIDDEN_CHARS for c in command):
        return "одна команда, без ; & | ` $ < > и переносов строк"
    try:
        tokens = shlex.split(command.replace("\\", "/"))
    except ValueError:
        return "не удалось разобрать команду"
    if not tokens:
        return "пустая команда"
    if any(".." in t.split("/") for t in tokens):
        return "пути с «..» запрещены"
    prog = tokens[0].split("/")[-1].lower().removesuffix(".exe")
    if PYTHON.match(tokens[0]) and len(tokens) >= 3 and tokens[1] == "-I":
        name = trusted_script(tokens[2], cwd)
        if not name:
            return "запускать можно только скрипты пакета search-kit (…/skills/<скил>/scripts/…)"
        return check_script(agent, name, tokens[3:], cwd)
    if agent == "social-researcher" and prog in ("ffmpeg", "ffprobe"):
        return check_ffmpeg(prog, tokens[1:], cwd)
    return "разрешены только: python -I <скрипт пакета> ..." + (" и ffmpeg/ffprobe" if agent == "social-researcher" else "")


def patch_paths(patch):
    return re.findall(r"^\*\*\* (?:Add|Update|Delete) File: (.+)$", str(patch or ""), re.M)


def decide(data):
    """None — можно; строка — причина запрета."""
    tool = str(data.get("tool_name") or "")
    inp = data.get("tool_input") or {}
    if not isinstance(inp, dict):
        inp = {"command": str(inp)}
    cwd = data.get("cwd") or os.getcwd()
    agent = str(data.get("agent_type") or "").split(":")[-1]

    # слой 1 — для всех
    if tool == "Bash" or "command" in inp and tool in ("shell", "exec", "PowerShell"):
        command = str(inp.get("command", ""))
        if isinstance(inp.get("command"), list):
            command = " ".join(map(str, inp["command"]))
        if SECRET_FILES.search(command) or SECRET_FILES_CASE.search(command):
            return ("команда упоминает файл с секретами (credentials.md, .env, сессии). Ключи читают только "
                    "скрипты и подключения сами; если это нужно человеку — пусть выполнит сам.")
        if KEY_VARS.search(command) or PRINT_ENV.search(command):
            return "команда выводит переменные окружения или ключи; значения ключей в разговор не попадают."
    paths = [inp.get(k) for k in ("file_path", "path", "notebook_path", "pattern") if inp.get(k)]
    paths += patch_paths(inp.get("input") or inp.get("patch") or (inp.get("command") if tool == "apply_patch" else ""))
    if tool in TOOLS_READ | TOOLS_WRITE and any(SECRET_FILES.search(str(p)) or SECRET_FILES_CASE.search(str(p))
                                                for p in paths):
        return "файл с секретами читать и править нельзя: его заполняет человек в текстовом редакторе."

    # слой 2 — только помощники ресерча
    if agent not in HELPERS:
        return None
    if tool == "Bash":
        return check_bash_helper(agent, str(inp.get("command", "")), cwd)
    if tool in TOOLS_WRITE:
        bad = [p for p in paths if not write_ok(p, cwd)] or ([] if paths else ["<нет пути>"])
        return f"помощник пишет только в папку исследования research/… или временную папку, не {bad[0]!r}" if bad else None
    if tool in TOOLS_READ:
        targets = [inp.get("file_path") or inp.get("path") or cwd]
        pattern = str(inp.get("pattern") or "")
        if tool == "Glob" and (pattern.startswith(("/", "~")) or re.match(r"^[a-zA-Z]:", pattern)):
            targets.append(pattern)
        bad = [p for p in targets if not read_ok(p, cwd)]
        return (f"помощник читает только скилы пакета, личные настройки (~/.search-kit/*.md) и папку исследования, "
                f"не {bad[0]!r}; нужен другой файл — пусть его прочитает основной чат") if bad else None
    if tool.startswith("mcp__") and SEND_VERBS.search(tool.split("__")[-1]):
        return f"инструмент {tool} может что-то отправить или изменить — помощнику запрещён"
    return None


def main():
    raw = sys.stdin.buffer.read().decode("utf-8", errors="replace")
    try:
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError
    except ValueError:
        if any(f'"agent_type": "{a}' in raw or f'"agent_type":"{a}' in raw or f':{a}"' in raw for a in HELPERS):
            reason = "не удалось прочитать входные данные хука"
        else:
            return
    else:
        try:
            reason = decide(data)
        except Exception as e:  # защита не отключается молча
            agent = str(data.get("agent_type") or "").split(":")[-1]
            reason = f"ошибка проверки ({type(e).__name__})" if agent in HELPERS else None
    if reason:
        sys.stdout.write(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse", "permissionDecision": "deny",
            "permissionDecisionReason": "search-kit guard: " + reason}}))  # \u-экранирование: консоль Windows не в UTF-8


if __name__ == "__main__":
    main()
