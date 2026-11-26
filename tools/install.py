"""Установка и обновление скилов search-kit в папку скилов любой оболочки (BB, Codex, Pi, Cursor и т. п.).

python -I tools/install.py <папка скилов> [--dry-run]

Примеры папок: BB — ~/.bb/skills; Codex — ~/.codex/skills; общая для агентов — ~/.agents/skills.
Claude Code ставит пакет плагином (README), этот скрипт для него не нужен.

Что делает: копирует каждую папку из skills/ пакета в <папку скилов>/<имя>. Если там уже есть папка с таким
именем, сначала переносит её в ~/.search-kit/backups/<дата-время>/<имя> (откат: вернуть папку обратно).
Чужие скилы в папке не трогает. Кэш Python и папки прогонов research не копирует.
Правила помощников (agents/*.md) кладёт в <папку скилов>/deep-research/agents/: в оболочках без плагина
deep-research вставляет их в задание обычного помощника.
Повторный запуск после `git pull` — это и есть обновление.
"""
import datetime as dt
import shutil
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")
SRC = Path(__file__).resolve().parent.parent / "skills"
SKIP = shutil.ignore_patterns("__pycache__", "*.pyc", "research")
AGENTS = SRC.parent / "agents"


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        sys.exit(__doc__)
    dry = "--dry-run" in sys.argv
    target = Path(args[0]).expanduser()
    if not target.is_dir():
        sys.exit(f"Нет папки {target}. Проверьте путь: папку скилов создаёт сама оболочка.")
    backup = Path.home() / ".search-kit" / "backups" / dt.datetime.now().strftime("%Y-%m-%d-%H%M%S")
    for skill in sorted(p for p in SRC.iterdir() if (p / "SKILL.md").is_file()):
        dest = target / skill.name
        if dest.exists() or dest.is_symlink():
            ours = (dest / "SKILL.md").is_file() and "search-kit" in (dest / "SKILL.md").read_text(encoding="utf-8", errors="ignore")
            if not ours:
                print(f"{skill.name}: ВНИМАНИЕ, в {dest} лежит чужой скил с тем же именем (в нём нет упоминания search-kit). "
                      "Он тоже уйдёт в резервную папку; если он нужен, переименуйте его до установки.")
            print(f"{skill.name}: старая версия → {backup / skill.name}")
            if not dry:
                backup.mkdir(parents=True, exist_ok=True)
                shutil.move(str(dest), str(backup / skill.name))
        print(f"{skill.name}: ставлю в {dest}")
        if not dry:
            shutil.copytree(skill, dest, ignore=SKIP)
            if skill.name == "deep-research" and AGENTS.is_dir():
                shutil.copytree(AGENTS, dest / "agents")
    print("Готово (пробный прогон, ничего не менял)." if dry else
          "Готово. Перезапустите треды оболочки, чтобы она увидела новые скилы.")


main()
