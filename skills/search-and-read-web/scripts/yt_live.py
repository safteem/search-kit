"""Print live YouTube numbers (views, likes, publish date, subscribers) for given video ids."""
import re
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")
PATTERNS = {
    "views": r'"viewCount":"(\d+)"',
    "published": r'"publishDate":"([^"]+)"',
    "likes": r'"likeCount":"?(\d+)',
    "subscribers": r'"subscriberCountText".{0,300}?"simpleText":"([^"]+)"',
    "comments": r'"commentCount".{0,120}?"(\d[\d,.KMkm ]*)',
}
for vid in sys.argv[1:]:
    req = urllib.request.Request(f"https://www.youtube.com/watch?v={vid}",
                                 headers={"User-Agent": "Mozilla/5.0", "Accept-Language": "en-US"})
    html = urllib.request.urlopen(req, timeout=25).read().decode("utf-8", "replace")
    found = {k: (m.group(1) if (m := re.search(p, html)) else "not found") for k, p in PATTERNS.items()}
    print(vid, found)
