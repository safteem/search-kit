"""Заголовок авторизации для подключения MCP (Keenable, Tavily, Firecrawl), ключ — из файла ключей search-kit.

python -I mcp_header.py keenable|tavily|firecrawl
Печатает {"Authorization": "Bearer <ключ>"}. Запускает его сама оболочка (в Claude Code — поле headersHelper
подключения), а не агент: так ключ попадает в запрос, но не в разговор и не в файл настроек. Ошибки — без значения ключа.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "social-capture" / "scripts"))
import keys  # noqa: E402

SERVICES = {"keenable": "KEENABLE_API_KEY", "tavily": "TAVILY_API_KEY", "firecrawl": "FIRECRAWL_API_KEY"}

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    if len(sys.argv) != 2 or sys.argv[1] not in SERVICES:
        sys.exit("python -I mcp_header.py " + "|".join(SERVICES))
    value, _ = keys.find(SERVICES[sys.argv[1]])
    if not value:
        sys.exit(f"нет ключа {SERVICES[sys.argv[1]]} в файле ключей")
    print(json.dumps({"Authorization": f"Bearer {value}"}))
