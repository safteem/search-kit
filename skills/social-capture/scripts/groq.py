"""Мини-клиент Groq Whisper. Ключ GROQ_API_KEY ищет keys.py (файл ключей, потом переменная окружения) и не печатает.

python -I groq.py file <видео или аудио> <выход.json> [язык]   — отправить файл (до 25 МБ на бесплатном тарифе)
python -I groq.py url <https-ссылка> <выход.json> [язык]        — Groq сам скачивает файл по ссылке
Модель — whisper-large-v3 (полная: редкие языки вроде грузинского понимает, turbo — нет; лимиты Groq у них одинаковые).
Другая модель — переменная GROQ_WHISPER_MODEL. Язык лучше не указывать: Groq определит его по звуку.
Ответ verbose_json (текст + фразы с отметками времени).
"""
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

API = "https://api.groq.com/openai/v1/audio/transcriptions"
MODEL = os.environ.get("GROQ_WHISPER_MODEL", "whisper-large-v3")
sys.path.insert(0, str(Path(__file__).resolve().parent))  # соседний keys.py: python -I не добавляет папку скрипта
import keys  # noqa: E402


def multipart(fields, file_path=None):
    boundary = uuid.uuid4().hex
    parts = []
    for name, value in fields.items():
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
    if file_path:
        p = Path(file_path)
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{p.name}"\r\n'
                     f'Content-Type: application/octet-stream\r\n\r\n'.encode() + p.read_bytes() + b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    mode, src, out, *lang = sys.argv[1:]
    fields = {"model": MODEL, "response_format": "verbose_json"}
    if lang:
        fields["language"] = lang[0]
    if mode == "url":
        fields["url"] = src
        body, ctype = multipart(fields)
    else:
        body, ctype = multipart(fields, src)
    req = urllib.request.Request(API, data=body, method="POST",
                                 headers={**({"Authorization": f"Bearer {key}"} if (key := keys.require("GROQ_API_KEY")) else {}),
                                          "Content-Type": ctype, "User-Agent": "groq-mini/1.0"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            data = json.loads(r.read())
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code}: {e.read()[:400].decode(errors='replace')}")
    Path(out).write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8", errors="replace")
    print(f"OK за {time.time() - t0:.1f} с, аудио {data.get('duration')} с, язык {data.get('language')}, "
          f"фраз {len(data.get('segments') or [])} -> {out}")
