"""Сводка по репозиториям GitHub через бесплатный API, экономно к лимиту.

Без ключа: 60 запросов в час на обычные вызовы и 10 в минуту на поиск. Если в окружении есть GITHUB_TOKEN,
он используется (5000 в час); сам скрипт ключей не хранит.

Режимы:
  python -I gh_repos.py find "<слова>" [--n 15] [--min-stars 100]
      поиск репозиториев по словам (название, описание, README-темы), по убыванию звёзд; 1 запрос.
  python -I gh_repos.py check owner/repo owner/repo ... [--deep]
      таблица по списку: звёзды, последнее изменение кода, лицензия, архив, открытые задачи;
      ~1 запрос поиска на 10 репозиториев (лимит поиска, обычный не тратит). --deep добавляет на каждый: последний релиз, коммиты за 90 дней,
      число участников (3 запроса на репозиторий — брать для короткого списка).
  python -I gh_repos.py issues owner/repo "<слово>"
      сколько задач и запросов про функцию (например whatsapp), открытых и закрытых; 2 поисковых запроса.
"""
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

API = "https://api.github.com"
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def get(path, want_headers=False):
    req = urllib.request.Request(API + path, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "search-skill-gh-repos",
        **({"Authorization": "Bearer " + os.environ["GITHUB_TOKEN"]} if os.environ.get("GITHUB_TOKEN") else {}),
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read() or b"null")
            return (data, r.headers) if want_headers else data
    except urllib.error.HTTPError as e:
        msg = e.read().decode("utf-8", "replace")[:200]
        if e.code in (403, 429):
            sys.exit(f"Лимит GitHub API исчерпан или доступ закрыт ({e.code}): {msg}")
        return (None, e.headers) if want_headers else None


def last_page_count(path):
    """Число элементов через per_page=1 и номер последней страницы в заголовке Link."""
    data, h = get(path + ("&" if "?" in path else "?") + "per_page=1", want_headers=True)
    if data is None:
        return None
    link = (h or {}).get("Link", "") or ""
    m = re.search(r'[?&]page=(\d+)>; rel="last"', link)
    return int(m.group(1)) if m else len(data) if isinstance(data, list) else None


def short_date(s):
    return (s or "")[:10]


def row(it):
    lic = (it.get("license") or {}).get("spdx_id") or "нет"
    if lic == "NOASSERTION":
        lic = "свой текст: читать LICENSE"
    return {
        "repo": it["full_name"], "stars": it["stargazers_count"], "pushed": short_date(it["pushed_at"]),
        "created": short_date(it["created_at"]), "license": lic, "archived": it["archived"],
        "issues": it["open_issues_count"], "desc": (it.get("description") or "")[:90],
    }


def print_table(rows, deep=False):
    cols = ["repo", "stars", "pushed", "created", "license", "archived", "issues"]
    if deep:
        cols += ["release", "commits90", "contributors"]
    print("| " + " | ".join(cols) + " | описание |")
    print("|" + "---|" * (len(cols) + 1))
    for r in rows:
        print("| " + " | ".join(str(r.get(c, "")) for c in cols) + f" | {r['desc']} |")


def find(words, n=15, min_stars=0):
    q = words + (f" stars:>={min_stars}" if min_stars else "")
    d = get("/search/repositories?" + urllib.parse.urlencode({"q": q, "sort": "stars", "per_page": n}))
    print(f"Найдено всего: {d['total_count']}; показаны топ-{n} по звёздам")
    print_table([row(i) for i in d["items"]])


def check(repos, deep=False):
    rows = []
    for i in range(0, len(repos), 10):
        chunk = repos[i:i + 10]
        q = " ".join("repo:" + r for r in chunk)
        d = get("/search/repositories?" + urllib.parse.urlencode({"q": q, "per_page": 30}))
        found = {it["full_name"].lower(): row(it) for it in (d or {}).get("items", [])}
        for r in chunk:
            if r.lower() not in found:  # поиск иногда не отдаёт репозиторий: добираем прямым запросом
                it = get(f"/repos/{r}")
                if it:
                    found[r.lower()] = row(it)
            rows.append(found.get(r.lower(), {"repo": r, "desc": "не найден (переименован, приватный или опечатка)"}))
    if deep:
        since = (datetime.now(timezone.utc) - timedelta(days=90)).strftime("%Y-%m-%dT%H:%M:%SZ")
        for r in rows:
            if "stars" not in r:
                continue
            rel = get(f"/repos/{r['repo']}/releases/latest")
            r["release"] = f"{rel['tag_name']} {short_date(rel['published_at'])}" if rel else "нет релизов"
            r["commits90"] = last_page_count(f"/repos/{r['repo']}/commits?since={since}")
            r["contributors"] = last_page_count(f"/repos/{r['repo']}/contributors?anon=1")
    print_table(rows, deep)


def issues(repo, word):
    for state in ("open", "closed"):
        q = f"repo:{repo} {word} in:title,body state:{state}"
        d = get("/search/issues?" + urllib.parse.urlencode({"q": q, "per_page": 3, "sort": "reactions"}))
        print(f"{state}: {d['total_count']}")
        for it in d["items"]:
            print(f"  - {it['title'][:100]} ({it['html_url']}, реакций {it['reactions']['total_count']})")


def main():
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    flag = lambda name, default: int(a[a.index(name) + 1]) if name in a else default
    if a[0] == "find":
        find(a[1], flag("--n", 15), flag("--min-stars", 0))
    elif a[0] == "check":
        check([x for x in a[1:] if "/" in x], "--deep" in a)
    elif a[0] == "issues":
        issues(a[1], a[2])
    else:
        sys.exit(__doc__)
    rl = get("/rate_limit")["resources"]
    print(f"\nОстаток лимита: обычные {rl['core']['remaining']}/{rl['core']['limit']}, "
          f"поиск {rl['search']['remaining']}/{rl['search']['limit']} в минуту")


if __name__ == "__main__":
    main()
