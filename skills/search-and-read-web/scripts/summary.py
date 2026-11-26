"""Сводка выдачи соцсетей (YouTube, Reddit, Google по X и Threads, X и ответы через Apify) в один файл для отбора.
Обычную выдачу Google читают как есть, без сводки.

python -I summary.py <вопрос> <выход.md> <файл.json>::<площадка>::<формулировка>::<цель> [...]

Площадки: yt — YouTube (SC), rd — Reddit (SC), gs — любая выдача Google (SC), в том числе `site:x.com`, `site:threads.com`,
xs — поиск X (Apify scrape.badger), xr — ответы X (scrape.badger `Get Replies`), tr — ответы Threads (Apify nice_dev).

Склеивает выдачи нескольких формулировок, убирает дубли, сортирует (Reddit по комментариям, YouTube и X по лайкам,
шортсы по просмотрам, топ-15; ответы X и Threads по лайкам, топ-20), режет текст: пост Reddit и X 250 символов, ответ 200, описание YouTube 120 без эмодзи.
Ссылки из постов Reddit, X, ответов Threads и отрывков Google не считает в лимит: после текста до 2 целиком и рабочими
и «и ещё N» (все — в полном посте, `post.py`). У X пост с цитатой помечен «ЦИТИРУЕТ: <ссылка>», внизу список цитат, которые надо открыть.
В описаниях YouTube ссылки не выводятся (почти всегда реклама и соцсети автора). У X не больше 3 постов одного автора в таблице, остальные
короткими строками под ней. Сверху таблица запросов с целью и числом новых уникальных.
"""
import datetime as dt
import html
import json
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
NOW = dt.datetime.now(dt.timezone.utc)
EMOJI = re.compile("[\U0001F000-\U0001FFFF☀-➿⬀-⯿️‍]")


URL = re.compile(r"https?://[^\s<>\"'\]\[]+")


def links_of(text):
    """Все ссылки из текста целиком, рабочими, без дублей. Ссылки бывают самым ценным в посте: не резать и не считать в лимит."""
    out = []
    for u in URL.findall(html.unescape(text or "")):
        u = u.rstrip(".,;:!?")
        while u.endswith(")") and u.count(")") > u.count("("):
            u = u[:-1]  # хвост markdown-ссылки [текст](адрес)
        if u not in out and not u.startswith("https://t.co/"):
            out.append(u)
    return out


def clean(text, n):
    """Текст без ссылок (они идут отдельным списком), без эмодзи, обрезан до n символов."""
    text = html.unescape(text or "")
    text = re.sub(r"\[([^\]]*)\]\(https?://[^)]*\)", r"\1", text)  # markdown-ссылка: оставить подпись
    text = URL.sub("", text)
    text = EMOJI.sub("", text)
    lines = [l.strip(" -•|►▬=_*") for l in text.splitlines()]
    text = " ".join(l for l in lines if len(l) > 2)
    text = re.sub(r"\s+", " ", text).strip()
    return (text[:n] + "…") if len(text) > n else text


def with_links(text, links):
    """До 2 ссылок целиком и счётчик остальных: все ссылки видны в полном посте (`post.py`)."""
    if not links:
        return text
    more = f" и ещё {len(links) - 2} (открыть пост)" if len(links) > 2 else ""
    return text + " Ссылки: " + " ".join(links[:2]) + more


def age_days(iso):
    if not iso:
        return ""
    try:
        d = dt.datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        if d.tzinfo is None:
            d = d.replace(tzinfo=dt.timezone.utc)
        return (NOW - d).days
    except ValueError:
        return ""


def num(x):
    try:
        return int(str(x).replace(",", ""))
    except (TypeError, ValueError):
        return 0


def cell(s):
    return str(s).replace("|", "/").replace("\n", " ")


def short_num(n):
    return f"{n / 1000:.0f}K" if n >= 1000 else n


MONTHS = {m: i for i, m in enumerate("Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split(), 1)}


def google_social(x):
    """Результат Google: для X и Threads автор и тип (пост, профиль), для остального сайт; возраст из начала описания."""
    url, desc = x.get("url", ""), x.get("description") or x.get("snippet") or ""  # обычный режим: description; pro: snippet
    m = re.search(r"(?:x|twitter)\.com/([^/?#]+)/(?:status|article)/(\d+)", url) or re.search(r"threads\.(?:com|net)/@([^/?#]+)/post/([^/?#]+)", url)
    social = re.search(r"//(www\.)?(x|twitter|threads)\.(com|net)/", url)
    if m:
        author, key, kind = m.group(1), m.group(2), "пост"
    elif social:  # профиль X или Threads: зацепка, а не пост
        author, key, kind = re.sub(r"^https?://(www\.)?[^/]+/@?", "", url).split("/")[0], url, "профиль"
    else:  # обычная страница из выдачи Google
        author, key, kind = re.sub(r"^https?://(www\.)?", "", url).split("/")[0], url, "страница"
    age = ""
    pub = re.match(r"(\d{4})-(\d{2})-(\d{2})", x.get("published_at") or "")  # режим pro: дата отдельным полем
    d = re.match(r"\s*([A-Z][a-z]{2}) (\d{1,2}), (\d{4})", desc)
    if pub:
        age = (NOW.date() - dt.date(*map(int, pub.groups()))).days
    elif d and d.group(1) in MONTHS:
        age = (NOW.date() - dt.date(int(d.group(3)), MONTHS[d.group(1)], int(d.group(2)))).days
    else:
        d = re.match(r"\s*(\d+) (hour|day|week)s? ago", desc)
        if d:
            age = {"hour": 0, "day": 1, "week": 7}[d.group(2)] * int(d.group(1))
    text = re.sub(r"^\s*([A-Z][a-z]{2} \d{1,2}, \d{4}|\d+ \w+ ago)\s*\.\.\.\s*", "", desc)
    return key, dict(title=x.get("title", ""), where=("" if kind == "страница" else "@") + author, kind=kind, age=age, text=with_links(clean(text, 250), links_of(text)), url=url)


def x_tweet(x, n):
    """Твит из Apify scrape.badger (поиск, ответы, цепочка)."""
    created = x.get("created_at")
    age = (NOW - dt.datetime.strptime(created, "%a %b %d %H:%M:%S %z %Y")).days if created else ""
    quoted = str(x.get("quoted_status_id") or "")
    links = []
    for u in x.get("urls") or []:
        u = u.get("expanded_url") if isinstance(u, dict) else None
        if not u or u in links or (quoted and re.search(rf"/status/{quoted}\b", u)):
            continue  # ссылка на цитируемый пост идёт отдельной пометкой
        links.append(u)
    extra = with_links("", links).strip()
    if quoted:  # цитата — ответ на чужой пост: без него контекст непонятен
        extra += f" ЦИТИРУЕТ: https://x.com/i/status/{quoted}"
    return dict(title=clean(x.get("full_text") or x.get("text"), n), extra=extra.strip(), quoted=quoted, where="@" + (x.get("username") or ""),
                sort=num(x.get("favorite_count")), replies=num(x.get("reply_count")), rts=num(x.get("retweet_count")),
                marks=num(x.get("bookmark_count")), views=num(x.get("view_count")),
                fol=short_num(num(x.get("user_followers_count"))), bio=clean(x.get("user_description"), 60), age=age,
                url=f"https://x.com/{x.get('username')}/status/{x.get('id')}")


question, out_path, specs = sys.argv[1], sys.argv[2], sys.argv[3:]
items = {"rd": {}, "yt": {}, "sh": {}, "gs": {}, "xs": {}, "xr": {}, "tr": {}}
queries = []
for spec in specs:
    path, plat, query, goal = spec.split("::")
    data = json.load(open(path, encoding="utf-8"))
    if isinstance(data, list):  # выдача Apify — список
        data = {"items": data}
    found, new = 0, 0
    if plat in ("xs", "xr", "tr"):
        groups = [(plat, data.get("items", []))]
    else:
        groups = {"rd": [("rd", data.get("posts", []))], "gs": [("gs", data.get("results", []))]}.get(
            plat, [("yt", data.get("videos", [])), ("sh", data.get("shorts", []))])
    for kind, rows in groups:
        for x in rows:
            if kind == "xr" and not x.get("in_reply_to_screen_name"):
                continue  # в ответы X подмешана реклама: у неё нет «в ответ кому»
            if kind == "tr" and (x.get("source") or ("replies" if x.get("isReply") else "")) != "replies":
                continue  # сам пост Threads открывается через SC, здесь только ответы
            found += 1
            if kind == "gs":
                key, rec = google_social(x)
            else:
                key = str(x.get("id") or x.get("postId"))
            if key in items[kind]:
                items[kind][key]["q"] += f", {len(queries) + 1}"
                continue
            new += 1
            if kind == "gs":
                rec["sort"] = -len(items["gs"])  # без цифр: порядок выдачи Google
            elif kind in ("xs", "xr"):
                rec = x_tweet(x, 250 if kind == "xs" else 200)
            elif kind == "tr":
                rec = dict(title=clean(x.get("text"), 200), extra=with_links("", links_of(x.get("text"))).strip(), where="@" + (x.get("authorUsername") or ""),
                           sort=num(x.get("likeCount")), replies=num(x.get("replyCount")), age=age_days(x.get("createdAt")),
                           url=x.get("url") or x.get("postUrl", ""))
            elif kind == "rd":
                rec = dict(title=x["title"], where="r/" + x.get("subreddit", ""), sort=num(x.get("num_comments")),
                           ups=num(x.get("score")), age=age_days(x.get("created_at_iso")),
                           text=with_links(clean(x.get("selftext"), 250), links_of(x.get("selftext"))), url=x.get("url") or ("https://www.reddit.com" + x["permalink"] if x.get("permalink") else "https://redd.it/" + x["id"]))
            else:
                views, likes = num(x.get("viewCountInt")), num(x.get("likeCountInt"))
                rec = dict(title=x["title"], where=(x.get("channel") or {}).get("title", ""), views=views, likes=likes,
                           comments=num(x.get("commentCountInt")), rate=(f"{likes / views:.1%}" if views and likes else ""),
                           length=x.get("lengthText", ""), age=age_days(x.get("publishDate") or x.get("publishedTime")),
                           text=clean(x.get("description"), 120), url="https://youtu.be/" + x["id"])
                rec["sort"] = likes if kind == "yt" else views
            rec["q"] = str(len(queries) + 1)
            items[kind][key] = rec
    queries.append((plat, query, goal, found, new))

PLAT = dict(rd="Reddit", yt="YouTube", gs="Google", xs="X (Apify)", xr="Ответы X (Apify)", tr="Ответы Threads (Apify)")
out = [f"# Сводка: {question}", "", f"Собрано {NOW:%Y-%m-%d}. Сортировка: Reddit по комментариям, YouTube и X по лайкам, "
       "шортсы по просмотрам, ответы по лайкам, Google в своём порядке.", "",
       "## Запросы", "", "| # | Площадка | Формулировка | Цель | Нашлось | Новых |", "|---|---|---|---|---|---|"]
for i, (plat, query, goal, found, new) in enumerate(queries, 1):
    out.append(f"| {i} | {PLAT[plat]} | {cell(query)} | {cell(goal)} | {found} | {new} |")

X_HEAD = "| # | Запрос | Текст | Автор | Подписч. | О себе | Лайки | Ответы | Репосты | Закладки | Просм. | Дней |\n|---|---|---|---|---|---|---|---|---|---|---|---|"
X_ROW = lambda i, r: (f"| {i} | {r['q']} | [{cell(r['title'])}]({r['url']}) {cell(r['extra'])} | {r['where']} | {r['fol']} | {cell(r['bio'])} | "
                      f"{r['sort']} | {r['replies']} | {r['rts']} | {r['marks']} | {r['views']} | {r['age']} |")
sections = [
    ("rd", "Reddit", "| # | Запрос | Заголовок | Сабреддит | Комм. | Апвоуты | Дней | Начало поста |\n|---|---|---|---|---|---|---|---|",
     lambda i, r: f"| {i} | {r['q']} | [{cell(r['title'][:90])}]({r['url']}) | {r['where']} | {r['sort']} | {r['ups']} | {r['age']} | {cell(r['text'])} |"),
    ("yt", "YouTube, видео", "| # | Запрос | Название | Канал | Лайки | Просм. | Лайки/просм. | Комм. | Длина | Дней | Описание |\n|---|---|---|---|---|---|---|---|---|---|---|",
     lambda i, r: f"| {i} | {r['q']} | [{cell(r['title'][:90])}]({r['url']}) | {cell(r['where'])} | {r['likes']} | {r['views']} | {r['rate']} | {r['comments']} | {r['length']} | {r['age']} | {cell(r['text'])} |"),
    ("xs", "X (по лайкам; не больше 3 постов одного автора)", X_HEAD, X_ROW),
    ("xr", "Ответы X (по лайкам, топ-20)", X_HEAD, X_ROW),
    ("tr", "Ответы Threads (по лайкам, топ-20)", "| # | Текст | Автор | Лайки | Ответы | Дней |\n|---|---|---|---|---|---|",
     lambda i, r: f"| {i} | [{cell(r['title'])}]({r['url']}) {cell(r['extra'])} | {r['where']} | {r['sort']} | {r['replies']} | {r['age']} |"),
    ("gs", "Выдача Google (цифр нет, порядок Google)", "| # | Запрос | Заголовок | Автор | Тип | Дней | Отрывок |\n|---|---|---|---|---|---|---|",
     lambda i, r: f"| {i} | {r['q']} | [{cell(r['title'][:80])}]({r['url']}) | {r['where']} | {r['kind']} | {r['age']} | {cell(r['text'])} |"),
    ("sh", "YouTube, шортсы", "| # | Запрос | Название | Просм. | Описание |\n|---|---|---|---|---|",
     lambda i, r: f"| {i} | {r['q']} | [{cell(r['title'][:90])}]({r['url']}) | {r['views']} | {cell(r['text'])} |"),
]
profiles = [r for r in items["gs"].values() if r["kind"] == "профиль"]
items["gs"] = {k: r for k, r in items["gs"].items() if r["kind"] != "профиль"}
for kind, name, head, row in sections:
    rows = sorted(items[kind].values(), key=lambda r: r["sort"], reverse=True)
    hidden = []
    if kind == "xs":  # выдачу Top забивает один крупный аккаунт: 3 его лучших в таблице, остальные строками ниже
        cnt, keep = {}, []
        for r in rows:
            cnt[r["where"]] = cnt.get(r["where"], 0) + 1
            (keep if cnt[r["where"]] <= 3 else hidden).append(r)
        rows = keep
    elif kind in ("xr", "tr"):
        rows = rows[:20]  # остальные ответы — в файле, искать по словам
    elif kind == "sh":
        rows = rows[:15]  # шортсов много: в сводку топ-15 по просмотрам
    if not rows:
        continue
    out += ["", f"## {name}: {len(rows)} уникальных", "", head]
    out += [row(i, r) for i, r in enumerate(rows, 1)]
    if hidden:
        out += ["", "Ещё посты тех же авторов (не в таблице, но могут быть ценны):", ""]
        out += [f"- {r['where']}, {r['sort']} лайков, {r['age']} дн.: [{cell(r['title'][:100])}]({r['url']}) {cell(r['extra'])}" for r in hidden]
quotes = [r for k in ("xs", "xr") for r in items[k].values() if r.get("quoted")]
if quotes:
    out += ["", f"## Цитируемые посты: {len(quotes)}. Открыть до выводов (`sc.py v1/twitter/tweet url=...`, 1 кредит)", "",
            "Пост с цитатой отвечает на чужой пост: без него смысл неясен. Открывать каждый, который рассматриваешь.", ""]
    out += [f"- {r['where']} ({r['sort']} лайков, [пост]({r['url']})) цитирует https://x.com/i/status/{r['quoted']}" for r in quotes]
if profiles:  # профиль открыть как пост нельзя; это зацепки, не посты
    out += ["", f"## Профили авторов: {len(profiles)} (зацепки, не посты)", ""]
    out += [f"- {r['where']} ({r['q']}): {cell(r['text'][:120])}" for r in profiles]
open(out_path, "w", encoding="utf-8").write("\n".join(out) + "\n")
print(out_path, {k: len(v) for k, v in items.items() if v}, "символов:", sum(len(l) for l in out))
