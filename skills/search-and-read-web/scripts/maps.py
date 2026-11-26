"""Сводка карт (Google через Apify kaix, Яндекс через Apify dami_studio) в файл для отбора.

Места:
  python -I maps.py places <выход.md> <места.json> [ещё.json ...] [--center ШИР,ДОЛ[::название]]
                    [--near <файл.json>::<что>] [--min 10] [--sort rating|count] [--top 40]
Отзывы:
  python -I maps.py reviews <выход.md> <файл.json>::fresh|low|deep [...] [--places <места.json>[,ещё.json]]
                    [--grep "слово|слово"]

Места: склеивает файлы, убирает дубли и закрытые, таблица по рейтингу (при равенстве до 0,1 выше тот, у кого больше
отзывов); места с числом отзывов меньше --min не отсекаются, а идут отдельным блоком «мало отзывов». --sort count —
режим списка (лиды): по числу отзывов. --center — расстояние по прямой до точки и ≈ минут пешком (×1,3 на петли
улиц, 80 м/мин). --near — для каждого места ближайший объект из другого поиска (метро, парк, спортзал) и расстояние.
У Google столбец «рядом» — ближайший ориентир, у Яндекса — ближайшее метро.

Отзывы: по каждому месту общая оценка против свежего среза (тренд: от 0,5 значимо, 0,3–0,4 «возможно»), звёзды среза,
разброс дат и всплеск (больше всего отзывов за 3 дня), худшие (≤3★) с датой и ответом владельца, свежие коротко,
строки с --grep (критерии из вопроса). Яндекс: файл мест с reviewsPerPlace, метка любая.
"""
import collections
import datetime as dt
import json
import math
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")


def load(path):
    data = json.load(open(path, encoding="utf-8"))
    return [r for r in data if isinstance(r, dict) and not r.get("_diagnostic")]


def short(text, n):
    text = re.sub(r"\s+", " ", (text or "").replace("<br>", " ")).strip()
    return (text[:n] + "…") if len(text) > n else text


def dist(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 6371000 * 2 * math.asin(math.sqrt(h))


def place(r):
    """Единый вид места: Google (kaix) или Яндекс (dami_studio)."""
    yandex = "ratingCount" in r or "nearestMetro" in r
    if yandex:
        near = r.get("nearestMetro") or {}
        near = f"м. {near.get('name')} {near.get('distanceMeters')} м" if near.get("name") else ""
        cats = r.get("categories") or []
        return dict(id=str(r.get("placeId")), name=r.get("name") or "", rating=r.get("rating"),
                    count=r.get("ratingCount") or 0, cats=cats, area=r.get("city") or "",
                    site=r.get("website"), phone=r.get("phone"), lat=r.get("latitude"), lon=r.get("longitude"),
                    url=r.get("url"), near=near, closed=r.get("status") not in (None, "open", "OPEN", "active"),
                    hours=hours_of(r),
                    reviews=r.get("reviews") or [])
    lm = ((r.get("addressDescriptor") or {}).get("landmarks") or [])
    near = ""
    if lm:
        near = f"{(lm[0].get('displayName') or {}).get('text', '')} {int(lm[0].get('straightLineDistanceMeters') or 0)} м"
    status = (r.get("businessStatus") or "").upper()
    return dict(id=r.get("placeId"), name=r.get("title") or "", rating=r.get("rating"),
                count=r.get("reviewCount") or 0, cats=r.get("categories") or [],
                area=r.get("neighborhood") or r.get("city") or ("выезд" if r.get("pureServiceAreaBusiness") else ""),
                site=r.get("website"), phone=r.get("phone"), lat=r.get("latitude"), lon=r.get("longitude"),
                url=(r.get("googleMapsUri") or "").split("&g_mp=")[0] or None, near=near, closed=bool(status) and status != "OPERATIONAL",
                hours=hours_of(r), price=r.get("priceRange") or r.get("priceLabel") or "",
                reviews=[])


def hours_of(r):
    """Часы коротко: 24/7, будни/сб/вс (Google) или текст Яндекса."""
    h = r.get("hours")
    if isinstance(h, list) and h:
        by = {x.get("day", "")[:3]: (x.get("hours") or "").replace("Open 24 hours", "24 ч").replace("Closed", "закрыто")
              for x in h if isinstance(x, dict)}
        vals = list(by.values())
        if vals and all(v == "24 ч" for v in vals):
            return "24/7"
        wd, sat, sun = by.get("Mon", "?"), by.get("Sat", "?"), by.get("Sun", "?")
        return wd if wd == sat == sun else f"пн {wd}; сб {sat}; вс {sun}"
    return short(r.get("openingHoursText") or "", 40)


def domain(url):
    if not url:
        return "нет"
    return re.sub(r"^https?://(www\.)?", "", url).split("/")[0].split("?")[0]


def args_of(argv):
    pos, opt = [], {}
    i = 0
    while i < len(argv):
        if argv[i].startswith("--"):
            opt.setdefault(argv[i][2:], []).append(argv[i + 1])
            i += 2
        else:
            pos.append(argv[i])
            i += 1
    return pos, opt


def places_cmd(out, files, opt):
    seen, rows = set(), []
    for f in files:
        for r in load(f):
            p = place(r)
            if p["id"] in seen or p["rating"] is None and not p["name"]:
                continue
            seen.add(p["id"])
            rows.append(p)
    closed = [p for p in rows if p["closed"]]
    rows = [p for p in rows if not p["closed"]]
    center = None
    if "center" in opt:
        c, _, cname = opt["center"][0].partition("::")
        center = (tuple(map(float, c.split(","))), cname or "точка")
    nears = []
    for spec in opt.get("near", []):
        f, _, what = spec.partition("::")
        pts = [place(r) for r in load(f)]
        nears.append((what or f, [p for p in pts if p["lat"] is not None]))
    for p in rows:
        p["extra"] = []
        if center and p["lat"] is not None:
            d = dist((p["lat"], p["lon"]), center[0])
            p["extra"].append(f"{int(d)} м ≈ {math.ceil(d * 1.3 / 80)} мин")
        for what, pts in nears:
            if p["lat"] is None or not pts:
                p["extra"].append("—")
                continue
            best = min(pts, key=lambda q: dist((p["lat"], p["lon"]), (q["lat"], q["lon"])))
            p["extra"].append(f"{short(best['name'], 30)} {int(dist((p['lat'], p['lon']), (best['lat'], best['lon'])))} м")
    minimum = int((opt.get("min") or ["10"])[0])
    top = int((opt.get("top") or ["40"])[0])
    mode = (opt.get("sort") or ["rating"])[0]
    if mode == "count":
        main, few = sorted(rows, key=lambda p: -(p["count"] or 0)), []
    else:
        main = [p for p in rows if (p["count"] or 0) >= minimum]
        few = [p for p in rows if (p["count"] or 0) < minimum]
        main.sort(key=lambda p: (-round(p["rating"] or 0, 1), -(p["count"] or 0)))
        few.sort(key=lambda p: (-(p["rating"] or 0), -(p["count"] or 0)))
    head = ["#", "Место", "★", "Отзывов", "Цена", "Категории", "Район", "Сайт", "Телефон", "Часы", "Рядом"]
    if center:
        head.append(f"До «{center[1]}» по прямой")
    head += [f"До ближ.: {w}" for w, _ in nears]

    def line(i, p):
        cells = [str(i), f"[{short(p['name'], 45)}]({p['url']})" if p["url"] else short(p["name"], 45),
                 str(p["rating"] if p["rating"] is not None else "—"), str(p["count"]), short(p.get("price") or "—", 15),
                 short(", ".join(p["cats"][:3]), 50), short(p["area"], 20), domain(p["site"]), p.get("phone") or "—", p.get("hours") or "—", short(p["near"], 40)]
        return "| " + " | ".join(c.replace("|", "/") for c in cells + p["extra"]) + " |"

    out_lines = [f"# Сводка карт: {len(rows)} мест", "",
                 f"Файлы: {', '.join(files)}. Закрытых убрано: {len(closed)}. Порядок: "
                 + ("по числу отзывов (режим списка)." if mode == "count"
                    else f"рейтинг, при равенстве до 0,1 — больше отзывов; меньше {minimum} отзывов — блок ниже."), "",
                 "| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    out_lines += [line(i, p) for i, p in enumerate(main[:top], 1)]
    if len(main) > top:
        out_lines.append(f"\n…ещё {len(main) - top} мест в файлах (--top больше, чтобы увидеть).")
    if few:
        out_lines += ["", f"## Мало отзывов (меньше {minimum}): не отсекаются, смотреть по смыслу", "",
                      "| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
        out_lines += [line(i, p) for i, p in enumerate(few[:20], 1)]
    ids = [p["id"] for p in main[:top] + few[:20] if p["id"] and p["id"] != "None"]
    out_lines += ["", "## placeId мест из таблиц (для отзывов, шаг 4: взять только короткий список)", "",
                  "`" + json.dumps(ids) + "`"]
    open(out, "w", encoding="utf-8").write("\n".join(out_lines) + "\n")
    print(f"{len(rows)} мест ({len(main)} в основной таблице, {len(few)} с малым числом отзывов) -> {out}")


def review(r):
    """Единый вид отзыва: kaix или Яндекс."""
    if "publishedAt" in r or "place" in r:
        owner = r.get("ownerResponse") or {}
        return dict(pid=(r.get("place") or {}).get("placeId"), pname=(r.get("place") or {}).get("name", ""),
                    id=r.get("reviewId"), stars=r.get("rating"), date=(r.get("publishedAt") or "")[:10],
                    text=r.get("textTranslated") or r.get("text") or "", lang=r.get("originalLanguage") or "",
                    owner=owner.get("text") if isinstance(owner, dict) else str(owner or ""))
    owner = r.get("ownerReply") or r.get("ownerResponse") or r.get("businessReply") or ""
    if isinstance(owner, dict):
        owner = owner.get("text", "")
    return dict(pid=None, pname="", id=r.get("reviewId") or (r.get("reviewerName", "") + (r.get("date") or "")),
                stars=r.get("rating"), date=(r.get("date") or "")[:10], text=r.get("text") or "", lang="", owner=owner)


def reviews_cmd(out, specs, opt):
    info, groups = {}, collections.defaultdict(lambda: collections.defaultdict(dict))
    for f in [x for spec in opt.get("places", []) for x in spec.split(",")]:
        for r in load(f):
            p = place(r)
            info[p["id"]] = p
    for spec in specs:
        f, _, tag = spec.partition("::")
        for r in load(f):
            if "reviews" in r and ("ratingCount" in r or "nearestMetro" in r):  # Яндекс: отзывы внутри места
                p = place(r)
                info[p["id"]] = p
                for x in p["reviews"]:
                    v = review(x)
                    groups[p["id"]]["fresh"][v["id"]] = v
                continue
            v = review(r)
            if v["pid"] and v["pid"] not in info:
                info[v["pid"]] = dict(name=v["pname"], rating=None, count=None, url=None)
            groups[v["pid"]][tag or "fresh"][v["id"]] = v
    grep = re.compile(opt["grep"][0], re.I) if "grep" in opt else None
    lines = [f"# Срезы отзывов: {len(groups)} мест", ""]
    for pid, tags in groups.items():
        p = info.get(pid, {})
        fresh = sorted(list(tags.get("fresh", {}).values()) + list(tags.get("deep", {}).values()),
                       key=lambda v: v["date"], reverse=True)
        fresh = list({v["id"]: v for v in fresh}.values())
        low = sorted(tags.get("low", {}).values(), key=lambda v: v["date"], reverse=True)
        stars = [v["stars"] for v in fresh if v["stars"]]
        avg = sum(stars) / len(stars) if stars else None
        overall = p.get("rating")
        lines.append(f"## {short(p.get('name', ''), 80)}")
        lines.append(f"Общая оценка {overall} ({p.get('count')} отзывов) · {p.get('url') or ''}")
        if avg is not None:
            trend = ""
            if overall and len(stars) < 15:
                trend = " · срез меньше 15, тренд не оцениваем"
            elif overall:
                diff = avg - overall
                trend = f" · разница {diff:+.1f}" + (" — значимо" if abs(diff) >= 0.5 else " — возможно" if abs(diff) >= 0.3 else " — в пределах разброса")
            dates = sorted(v["date"] for v in fresh if v["date"])
            burst = ""
            if dates:
                ds = [dt.date.fromisoformat(d) for d in dates]
                best = max(sum(1 for y in ds if 0 <= (y - x).days <= 2) for x in ds)
                burst = f" · больше всего за 3 дня: {best}"
            cnt = collections.Counter(stars)
            lines.append(f"Свежий срез: {len(fresh)} отзывов, средняя {avg:.2f}{trend} · звёзды "
                         + " ".join(f"{s}★×{cnt[s]}" for s in sorted(cnt, reverse=True))
                         + (f" · даты {dates[0]} … {dates[-1]}" if dates else "") + burst)
        langs = collections.Counter(v["lang"] or "?" for v in fresh if v["text"])
        if langs and set(langs) != {"?"}:
            lines.append("Языки отзывов с текстом (оригинал; «?» — не указан, у kaix так бывает с русскими): "
                         + ", ".join(f"{k} {n}" for k, n in langs.most_common(6)))
        worst = [v for v in list(low) + fresh if v["stars"] and v["stars"] <= 3]
        worst = list({v["id"]: v for v in worst}.values())
        if worst:
            lines.append(f"\n**Худшие (≤3★): {len(worst)}**")
            for v in worst[:15]:
                o = f" ⟶ владелец: {short(v['owner'], 150)}" if v["owner"] else ""
                lines.append(f"- {v['stars']}★ {v['date']}: {short(v['text'], 300) or '(без текста)'}{o}")
        elif tags.get("low"):
            lines.append("\nХудших (≤3★) нет.")
        if fresh:
            lines.append("\n**Свежие:**")
            for v in fresh[:25]:
                if v["text"]:
                    lines.append(f"- {v['stars']}★ {v['date']}: {short(v['text'], 150)}")
        if grep:
            hits = [v for v in {**tags.get("fresh", {}), **tags.get("low", {}), **tags.get("deep", {})}.values()
                    if grep.search(v["text"])]
            lines.append(f"\n**По словам «{opt['grep'][0]}»: {len(hits)}**")
            for v in hits[:10]:
                lines.append(f"- {v['stars']}★ {v['date']}: {short(v['text'], 250)}")
        lines.append("")
    open(out, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print(f"{len(groups)} мест -> {out}")


if __name__ == "__main__":
    pos, opt = args_of(sys.argv[1:])
    if len(pos) < 3 or pos[0] not in ("places", "reviews"):
        sys.exit(__doc__)
    (places_cmd if pos[0] == "places" else reviews_cmd)(pos[1], pos[2:], opt)
