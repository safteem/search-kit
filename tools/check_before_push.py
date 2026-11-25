"""Проверка перед пушем: нет ли в пакете ключей, личных путей и имён. Пустой результат = можно пушить.

python -I tools/check_before_push.py          — проверить все файлы под git (и новые, ещё не добавленные)
Код выхода 1, если что-то нашлось. Совпадения печатаются с маской, без значения ключа.
Свои личные слова (имя, город) можно добавить в файл ~/.search-kit/private-words.txt, по одному в строке.
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SELF = Path(__file__).resolve()
SECRETS = re.compile(
    r"(apify_api_[A-Za-z0-9]{10,}|sk-[A-Za-z0-9_\-]{20,}|gsk_[A-Za-z0-9]{20,}|tvly-[A-Za-z0-9\-]{10,}|"
    r"fc-[a-f0-9]{20,}|ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|xox[bp]-[A-Za-z0-9\-]{10,}|"
    r"(?:API_KEY|TOKEN|SECRET|API_HASH)\s*=\s*['\"]?[A-Za-z0-9_\-]{16,})")
PERSONAL = [r"[A-Za-z]:[/\\]Users[/\\]", r"\b[A-Z]:[/\\](?:labs|Life|Projects)\b", r"/home/[a-z]{3,}/", r"(?-i:/Users/)[A-Za-z]{3,}/",
            r"[\w.\-]+@(?:gmail|yandex|mail|outlook|icloud)\.\w+", r"\.claude/skills/"]


def files():
    out = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard"], cwd=ROOT,
                         capture_output=True, text=True, encoding="utf-8").stdout.split("\n")
    return [ROOT / f for f in out if f]


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    words = PERSONAL[:]
    extra = Path.home() / ".search-kit" / "private-words.txt"
    if extra.is_file():
        words += [re.escape(w.strip()) for w in extra.read_text(encoding="utf-8").splitlines() if w.strip()]
    personal = re.compile("|".join(words), re.I)
    found = 0
    for f in files():
        if f.resolve() == SELF or not f.is_file() or f.suffix.lower() in (".png", ".jpg", ".pyc"):
            continue
        for n, line in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            for m in list(SECRETS.finditer(line)) + list(personal.finditer(line)):
                s = m.group(0)
                shown = s if personal.fullmatch(s) else s[:4] + "…" + s[-2:]
                print(f"{f.relative_to(ROOT)}:{n}: {shown}")
                found += 1
    print("Чисто: можно пушить." if not found else f"Найдено {found}: убрать перед пушем.")
    sys.exit(1 if found else 0)


if __name__ == "__main__":
    main()
