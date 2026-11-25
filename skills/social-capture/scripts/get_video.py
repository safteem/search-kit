"""Скачать видео или картинку по прямой ссылке, которую вернул сборщик (ScrapeCreators, Apify).
python -I get_video.py <https-ссылка> <файл> [referer]
Только https, только адреса площадок (список HOSTS), только video/* или image/*, не больше 300 МБ.
Файл ничем не открывает и не запускает. Ссылки временные — качать сразу после получения данных."""
import sys
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

HOSTS = ("cdninstagram.com", "fbcdn.net", "tiktokcdn.com", "tiktokcdn-us.com", "tiktokcdn-eu.com",
         "tiktokv.com", "byteoversea.com", "twimg.com", "redd.it", "redditmedia.com", "googleusercontent.com")
LIMIT = 300 * 1024 * 1024
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0 Safari/537.36"

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    url, out, *ref = sys.argv[1:]
    host = urlparse(url).hostname or ""
    if urlparse(url).scheme != "https" or not any(host == h or host.endswith("." + h) for h in HOSTS):
        sys.exit(f"отказ: {host} не из списка площадок (HOSTS в скрипте)")
    headers = {"User-Agent": UA}
    if ref:
        headers["Referer"] = ref[0]
    t0 = time.time()
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=90) as r:
        ctype = r.headers.get("Content-Type", "")
        if not ctype.startswith(("video/", "image/")):
            sys.exit(f"отказ: тип {ctype!r}")
        data = r.read(LIMIT + 1)
    if len(data) > LIMIT:
        sys.exit("больше 300 МБ — не сохраняю")
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_bytes(data)
    print(f"OK {len(data) / 1024 / 1024:.1f} МБ за {time.time() - t0:.1f} с ({ctype}) -> {out}")
