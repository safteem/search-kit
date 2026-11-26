"""Установка и обновление search-kit в любую оболочку, на Windows, Mac и Linux. Повторный запуск после
`git pull` — это и есть обновление.

python -I tools/install.py bb        — BB: ярлыки скилов в ~/.bb/skills (их видят все агенты BB)
python -I tools/install.py claude    — Claude Code: плагин из этой папки (скилы, помощники, охранник)
python -I tools/install.py <папка>   — любая другая оболочка: ярлыки скилов в её папку скилов
                                       (Codex — ~/.codex/skills, общая для агентов — ~/.agents/skills)
python -I tools/install.py prepare   — только подготовить папку пакета (без установки в оболочку)
python -I tools/install.py keys-file <путь> — брать ключи из своего общего файла ключей на все сервисы
Флаги: --dry-run (показать, что будет сделано, ничего не меняя), --force (заменить чужой скил с тем же именем;
он уйдёт в резервную папку).

Что делает всегда (подготовка папки пакета):
1. my/ из образца my.example/ (только недостающие файлы; существующие не трогает). Образец ключей ложится
   в my/ под именем файла ключей.
2. В каждый скил кладёт kit-home.txt с адресом пакета: так скрипты находят my/, даже когда оболочка работает
   с копией скилов (BB и плагин Claude Code копируют их в свои служебные папки).
3. Правила помощников (agents/*.md) — в skills/deep-research/agents/ (для оболочек без именованных помощников).

Установка ярлыками (BB и другие оболочки): в папке скилов оболочки появляется ярлык на папку скила в пакете
(Windows — junction, без прав администратора; Mac и Linux — symlink). Обновление пакета сразу видно оболочке.
Если в папке скилов уже лежит наш скил (старая копия), он уходит в my/backups/<дата-время>/; чужой скил
с тем же именем пропускается (заменить — только с --force).
"""
import datetime as dt
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"
MY, EXAMPLE = ROOT / "my", ROOT / "my.example"
KEYS_NAME = "." + "env"
DRY = "--dry-run" in sys.argv
FORCE = "--force" in sys.argv


def say(text):
    print(("[пробный прогон] " if DRY else "") + text)


def prepare():
    if not DRY:
        MY.mkdir(exist_ok=True)
    for src in sorted(EXAMPLE.iterdir()):
        if src.name == "README.md":
            continue
        dest = MY / (KEYS_NAME if src.name == "keys-template.txt" else src.name)
        if not dest.exists():
            say(f"my/{dest.name}: создаю из образца")
            if not DRY:
                shutil.copy2(src, dest)
    for skill in skills():
        marker = skill / "kit-home.txt"
        if not marker.is_file() or marker.read_text(encoding="utf-8").strip() != str(ROOT):
            say(f"{skill.name}: записываю адрес пакета в kit-home.txt")
            if not DRY:
                marker.write_text(str(ROOT) + "\n", encoding="utf-8")
    agents_src, agents_dst = ROOT / "agents", SKILLS / "deep-research" / "agents"
    if agents_src.is_dir() and not DRY:
        shutil.rmtree(agents_dst, ignore_errors=True)
        shutil.copytree(agents_src, agents_dst)
    say(f"Папка пакета готова: {ROOT}\nЛичная папка (ключи, настройки): {MY}")


def skills():
    return sorted(p for p in SKILLS.iterdir() if (p / "SKILL.md").is_file())


def is_link(p):
    return p.is_symlink() or (hasattr(os.path, "isjunction") and os.path.isjunction(p))


def make_link(dest, src):
    if os.name == "nt":
        import _winapi
        _winapi.CreateJunction(str(src), str(dest))
    else:
        dest.symlink_to(src, target_is_directory=True)


def link_into(target):
    target = Path(target).expanduser()
    if not target.is_dir():
        sys.exit(f"Нет папки {target}. Папку скилов создаёт сама оболочка: запустите её один раз и повторите.")
    backup = MY / "backups" / dt.datetime.now().strftime("%Y-%m-%d-%H%M%S")
    old = target / "setup"  # так скил установки назывался до 26.11.2026
    if (old / "SKILL.md").is_file() and "search-kit" in (old / "SKILL.md").read_text(encoding="utf-8", errors="ignore"):
        say(f"setup: старое имя скила установки -> {backup / 'setup'}")
        if not DRY:
            backup.mkdir(parents=True, exist_ok=True)
            shutil.move(str(old), str(backup / "setup"))
    for skill in skills():
        dest = target / skill.name
        if is_link(dest):
            if dest.resolve() == skill.resolve():
                say(f"{skill.name}: ярлык уже стоит")
                continue
            say(f"{skill.name}: старый ярлык заменяю")
            if not DRY:
                os.rmdir(dest) if os.name == "nt" else dest.unlink()
        elif dest.exists():
            ours = (dest / "SKILL.md").is_file() and "search-kit" in (dest / "SKILL.md").read_text(encoding="utf-8", errors="ignore")
            if not ours and not FORCE:
                say(f"{skill.name}: ПРОПУЩЕН. В {dest} лежит чужой скил с тем же именем. Переименуйте его или "
                    "запустите с --force: тогда он уйдёт в резервную папку.")
                continue
            say(f"{skill.name}: старая копия -> {backup / skill.name}")
            if not DRY:
                backup.mkdir(parents=True, exist_ok=True)
                shutil.move(str(dest), str(backup / skill.name))
        say(f"{skill.name}: ярлык {dest} -> {skill}")
        if not DRY:
            make_link(dest, skill)
    say("Готово. Начните новый тред или сессию, чтобы оболочка увидела скилы.")


def claude():
    exe = shutil.which("claude")
    if not exe:
        sys.exit("Не нашёл программу claude. Установите Claude Code (claude.com/code) и повторите.")
    cmds = [[exe, "plugin", "marketplace", "add", str(ROOT)],
            [exe, "plugin", "install", "search-kit@search-kit-marketplace"],
            [exe, "plugin", "marketplace", "update", "search-kit-marketplace"],
            [exe, "plugin", "update", "search-kit@search-kit-marketplace"]]
    for cmd in cmds:
        say(" ".join(cmd[1:]))
        if not DRY:
            r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
            out = (r.stdout + r.stderr).strip().splitlines()
            print("   ", out[-1] if out else ("готово" if r.returncode == 0 else f"код {r.returncode}"))
    say("Готово. Перезапустите сессию Claude Code, чтобы плагин подхватился.")


def keys_file(path):
    """Записать в файл ключей my/ строку KEYS_FILE=<путь>: скрипты возьмут ключи из вашего общего файла.
    Значения ключей не читает и не печатает; остальные строки не трогает."""
    import re
    target = Path(path.strip().strip('"')).expanduser()
    own = MY / KEYS_NAME
    if not own.exists():
        prepare()
    text = own.read_text(encoding="utf-8-sig") if own.exists() else ""
    line = f"KEYS_FILE={target}"
    text, n = re.subn(r"^[ \t#]*KEYS_FILE[ \t]*=.*$", line.replace("\\", "\\\\"), text, count=1, flags=re.M)
    if not n:
        text = line + "\n" + text
    say(f"Общий файл ключей: {target}" + ("" if target.is_file() else " (файла пока нет: создайте его, ключи впишете туда)"))
    if not DRY:
        own.write_text(text, encoding="utf-8")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args or (len(args) != 1 and args[0] != "keys-file"):
        sys.exit(__doc__)
    if args[:1] == ["keys-file"] and len(sys.argv) >= 3:  # указать свой общий файл ключей (строка KEYS_FILE в my/)
        keys_file(" ".join(a for a in sys.argv[2:] if not a.startswith("--")))
        return
    prepare()
    where = args[0]
    if where == "prepare":
        return
    if where == "bb":
        link_into(Path.home() / ".bb" / "skills")
    elif where == "claude":
        claude()
    else:
        link_into(where)


main()
