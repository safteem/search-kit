"""Запуск сервера telegram-mcp с ключами из файла ключей search-kit: модель их не видит.

python -I tg_launch.py login        — вход по QR-коду; человек запускает САМ в своём терминале. Печатает строку
                                      сессии; на вопрос про файл настроек сервера ответить «n».
python -I tg_launch.py login-phone  — то же по номеру и коду (код приходит в Telegram на открытом устройстве)
python -I tg_launch.py read         — для агента: только чтение, без лишних инструментов (экономия контекста)
python -I tg_launch.py join         — для агента: чтение + вступление в каналы и чаты по ссылке

Где что: папка сервера telegram-mcp — поле "repo" в my/telegram.json. Ключи (вписывает человек) — в файле ключей
search-kit (keys.py where): TELEGRAM_API_ID, TELEGRAM_API_HASH (с my.telegram.org, общие для всех устройств)
и строка сессии.

**Одна сессия — одно устройство.** Если одну строку сессии запустить одновременно с двух IP (компьютер и сервер),
Telegram её сбросит («AuthKeyDuplicated»: used under two different IP addresses simultaneously). Поэтому на каждом
устройстве свой вход (`login`), и строка сессии записывается с именем устройства:
TELEGRAM_SESSION_STRING_<ИМЯ_КОМПЬЮТЕРА> (имя печатает `tg_launch.py login`). Файл ключей можно синхронизировать
между устройствами: каждое возьмёт свою строку. Простое имя TELEGRAM_SESSION_STRING — только если устройство одно.
"""
import json
import os
import re
import socket
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "social-capture" / "scripts"))
import keys  # noqa: E402

HOME = keys.kit_home(Path(__file__).absolute().parents[1])
DEVICE = re.sub(r"\W", "_", socket.gethostname()).upper()
SESSION_KEY = f"TELEGRAM_SESSION_STRING_{DEVICE}"

# Режим read: инструменты чтения, которые для ресерча не нужны (контакты, админка, стикеры, эмодзи, гифки,
# приватность, черновики, отложенные, реакции, кто прочитал, ожидание событий, расшифровка). Меньше описаний
# инструментов в контексте каждой сессии и меньше личных данных на виду. Вернуть инструмент — убрать имя отсюда.
READ_HIDDEN = (
    "export_contacts,get_contact_chats,get_contact_ids,get_direct_chat_by_contact,list_contacts,"
    "list_contact_aliases,search_contacts,get_common_chats,get_last_interaction,get_full_user,get_user_photos,"
    "get_user_status,get_privacy_settings,get_blocked_users,"
    "get_admins,get_banned_users,get_member_admin_status,get_recent_actions,get_participants,get_send_as,"
    "get_custom_emoji_pack,get_custom_emoji_packs,preview_custom_emoji,get_gif_search,get_sticker_sets,"
    "list_forum_topic_icons,get_drafts,get_scheduled_messages,get_message_reactions,get_message_read_by,"
    "get_bot_info,list_inline_buttons,get_chatlist_invite,incoming_feed_status,wait_for_events,"
    "wait_for_new_message,wait_for_settled_message,list_accounts,transcribe_voice,get_chats,get_messages,"
    "get_folder_limits,get_folder_snapshot"
)
JOIN_TOOLS = "join_chat_by_link,subscribe_public_channel,import_chat_invite"
SETTINGS = {
    "TELEGRAM_TRANSCRIBE": "off",       # расшифровка голосовых выключена
    "TELEGRAM_ALLOWED_ROOTS": "",       # файлы с диска не отправлять и не скачивать
    "TELEGRAM_SESSION_LOCK": "shared",  # одна сессия на несколько сессий агента — только на этом устройстве
}


def repo():
    try:
        r = json.loads((HOME / "telegram.json").read_text(encoding="utf-8")).get("repo")
    except (OSError, ValueError):
        r = None
    if not r or not Path(r).is_dir():
        sys.exit(f"Не указана папка telegram-mcp: поле \"repo\" в {HOME / 'telegram.json'} (скил search-kit-setup, шаг Telegram).")
    return Path(r)


def need(names):
    found, missing = {}, []
    for n in names:
        value, _ = keys.find(n)
        (found.__setitem__(n, value) if value else missing.append(n))
    if missing:
        sys.exit(f"Нет ключей: {', '.join(missing)}. Впишите их в файл ключей (keys.py where).")
    return found


def session():
    for name in (SESSION_KEY, "TELEGRAM_SESSION_STRING"):
        value, _ = keys.find(name)
        if value:
            return value
    sys.exit(f"Нет строки сессии для этого устройства. Войдите здесь (`tg_launch.py login`) и впишите строку "
             f"в файл ключей как {SESSION_KEY}=...")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    mode = sys.argv[1] if len(sys.argv) == 2 else ""
    folder = repo()
    python = folder / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    env = dict(os.environ, **SETTINGS)
    env.update(need(["TELEGRAM_API_ID", "TELEGRAM_API_HASH"]))
    if mode in ("login", "login-phone"):
        print(f"Устройство: {DEVICE}. Строку сессии впишите в файл ключей как {SESSION_KEY}=...", file=sys.stderr)
        script, args = "session_string_generator.py", ["--qr" if mode == "login" else "--phone"]
    elif mode in ("read", "join"):
        env["TELEGRAM_SESSION_STRING"] = session()
        env["TELEGRAM_EXPOSED_TOOLS"] = f"read-only+{JOIN_TOOLS}" if mode == "join" else f"read-only-{READ_HIDDEN}"
        script, args = "main.py", []
    else:
        sys.exit("python -I tg_launch.py login|login-phone|read|join")
    # stdin/stdout наследуются: оболочка общается с сервером через них (MCP stdio)
    sys.exit(subprocess.call([str(python), script, *args], cwd=folder, env=env))


if __name__ == "__main__":
    main()
