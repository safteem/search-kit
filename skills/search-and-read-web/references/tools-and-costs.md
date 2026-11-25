# Инструменты, цены и ограничения

## Чем что делать

| Задача | Инструмент | Цена |
|---|---|---|
| Поиск в любом вопросе вместе с Google: обзор, новости, найти адрес официальной страницы | Keenable `search_web_pages`, всегда `snippet_max_length: 400` (без него ~63 тыс. символов, ~16 тыс. токенов); сузить: `site`, свежее: `published_after` (например `14d`) | 1 кредит Keenable за запрос, 100 тыс. в месяц бесплатно; хранит запросы у себя: без личных данных (имена, адреса, данные клиентов) |
| Запасной поиск: Keenable недоступен, облачная сессия | `WebSearch` (standard; поисковик Brave, не Google) | 0 кредитов, ~700 токенов; ответ — пересказ другой моделью: ссылки настоящие, цифры могут быть искажены |
| Более тщательный и свежий обзор | `WebSearch` (extended) | 0 кредитов, но в несколько раз дороже по лимиту Claude — только если standard дал мало |
| Выдача Google: в любом поиске вместе с Keenable, глубокий ресерч (шаг 3a), рилсы Instagram, `site:threads.com`, `site:x.com`, `site:reddit.com` | `python -I {скилы}/social-capture/scripts/sc.py v1/google/search <файл> query=...` | 1 кредит ScrapeCreators (~0,002 долл.), 10 результатов |
| Поиск по домену: запасной путь, если Google и ScrapeCreators ничего не нашли (помощники `researcher` и `social-researcher` ищут через ScrapeCreators и Google сами) | `tavily_search`, `basic`, `include_domains`, 3–5 результатов | 1 кредит |
| Текст страницы для факта (дословно) | `tavily_extract` с `query`; до 5 ссылок одним вызовом | 1 кредит за 5 страниц |
| Полный текст страницы | `tavily_extract` без `query` | 1 кредит за 5 страниц |
| **YouTube и Reddit**: поиск, сводка, расшифровка, комментарии | по `references/youtube-reddit.md`: `sc.py v1/youtube/search ... includeExtras=true`, `v1/reddit/search`, `v1/youtube/video/transcript`, `v1/youtube/video/comments`, `v1/reddit/post/comments`; сводка — `scripts/summary.py` | 1 кредит ScrapeCreators за вызов; расшифровка 1 часа ~17 тыс. токенов — в файл, читать нужные места |
| **X и Threads**: поиск, сводка, цепочки, ответы | по `references/x-threads.md`: X — Apify `scrape.badger/twitter-tweets-scraper` (поиск, цепочка, ответы) + 1 запрос Google `site:x.com`; Threads — Google `site:threads.com` (SC) и Tavily (`include_domains` threads.com) вместе, пост `sc.py v1/threads/post`, ответы Apify `s_actors/threads-replies-scraper` , `scripts/post.py`; сводка — `scripts/summary.py` | X: $0,00015 за твит (поиск 40 ≈ $0,006); Threads: 1 кредит SC за поиск и пост, ответы ≈ $0,011 за 40, ~10 с; 1 кредит Tavily за формулировку; Apify — из бесплатных $5 в месяц |
| **Карты**: места, рейтинг, число отзывов, срез отзывов, расстояния | по `references/maps.md`: Google — Apify `kaix/google-maps-places-scraper` (места) и `kaix/google-maps-reviews-scraper` (отзывы), сводка `scripts/maps.py`; Яндекс (по просьбе) — Apify `dami_studio/yandex-maps-scraper`; точное время в пути и запасной путь — Firecrawl Maps (`alexandria_library_read`, `firecrawl-maps`) | Google: $0,00008 за место, $0,00004 за отзыв (выбор целиком ~$0,02–0,03); Яндекс: $0,0004 за место, $0,0003 за отзыв; Firecrawl Maps: 10 кредитов за поиск или отзывы, 5 за маршрут |
| **Площадки**: отели, билеты, магазины, объявления | по `references/platforms.md`: метапоиск (Google Hotels, Flights, Shopping) во встроенном браузере `mcp__Claude_Browser__*` (в bb — его браузер), площадка там же; чтение карточек WebFetch → `firecrawl_scrape`; запасной браузер `agent-browser --profile ... --headed`; рецепты `data/platforms.md` | браузер бесплатно (токены: 150–250 тыс. на задачу); Firecrawl 1 кредит за карточку |
| YouTube: SC не отдал расшифровку | `firecrawl_scrape`, `maxAge: 0`, `onlyMainContent: true` (текст тот же — субтитры YouTube, но в разговор идёт ~5 тыс. символов служебных данных); субтитров нет совсем — `social-capture`, «YouTube без субтитров» | 1 кредит |
| Страница не открылась, пустая, сайт на скриптах (часто госсайты) | `firecrawl_scrape`, `markdown`, `onlyMainContent: true` | 1 кредит |
| Сайт не открылся обычным режимом (403, пусто, защита от роботов: TripAdvisor, Booking и т. п.) | повторить `firecrawl_scrape` с `proxy: "auto"` (сначала обычный прокси, при отказе усиленный; 1 кредит, повтор бесплатный). В режиме Auto проверка Claude Code может такой запрос запретить — тогда не обходить, сказать пользователю и взять рейтинг, число отзывов и цитаты из выдачи Google (`sc.py v1/google/search`) и `tavily_search` | 1 кредит |
| Сервис отказывает по своим правилам («we do not support this site»: Reddit, Instagram) | режим прокси не поможет: Reddit, соцсети — ScrapeCreators | 1 кредит |
| GitHub: подбор и проверка проектов | `python -I {скилы}/search-and-read-web/scripts/gh_repos.py find "<категория>"` / `check a/b c/d [--deep]` / `issues a/b <слово>`, правила — `references/github.md` | бесплатно; без ключа 60 обычных запросов в час и 10 поисковых в минуту (`check` ~1 поисковый на 10 проектов, `--deep` 3 обычных на проект) |
| Живая цифра | бесплатный API (GitHub — `scripts/gh_repos.py`, `scripts/yt_live.py` для YouTube на компьютере; в облаке youtube.com закрыт сетью — `firecrawl_scrape` с `maxAge: 0`, 1 кредит), иначе `firecrawl_scrape` с `maxAge: 0` | 0–1 кредит |
| Научные статьи | `firecrawl_research_search_papers` | бесплатно |
| Цвета, шрифты, логотип сайта | `firecrawl_scrape`, формат `branding` | 1 кредит |
| Пересказ страницы, если остальное не сработало | `WebFetch` | бесплатно; помечать «пересказ» |
| Свои Telegram-чаты и каналы | скил `telegram-search` (карта тегов, ветки ответов, скрипт `tg_search.py`); только где Telegram подключён (личный файл), не в облачной среде | бесплатно |
| Пост, видео, комментарии из соцсетей | скил `social-capture` | ScrapeCreators, Apify, Groq |

## Дорогие операции — только с согласия и названной ценой

`tavily_research` (4–250 кредитов), `tavily_crawl`, `firecrawl_crawl`, `firecrawl_agent`; форматы Firecrawl
`json`, `query`, `highlight` (+4 кредита за страницу — дешевле прочитать `markdown` и разобрать самому);
живые цифры больше ~5 страниц через Firecrawl; платная расшифровка и `download_media` ScrapeCreators;
запуски Apify дороже лимита из настроек (`config.md`, личный файл).

## Экономия памяти сессии

- выжимка WebSearch (~700 токенов) вместо кусков Tavily (3–5 тыс.), где хватает обзора;
- `tavily_extract` с `query`, а не вся страница, до 5 ссылок одним вызовом; `onlyMainContent: true`;
- полный текст — только у ценных страниц; одну страницу дважды не читать;
- большие данные (комментарии, расшифровки, ответы сервисов) — в файл, в разговор — только нужные строки;
- большой ресерч — через помощников `deep-research`: страницы остаются в их памяти;
- одна тема — один чат; выводы — в файлы проекта.

## Технические ограничения

- Tavily: рабочий ключ держит параллельные запросы; при отказе 429 — повторить один раз, потом Firecrawl или WebSearch.
- WebSearch не открывает Reddit (`allowed_domains: ["reddit.com"]` — ошибка): Reddit — через Tavily или `social-capture`.
- Неудачные чтения кредиты не списывают (Tavily, Firecrawl, ScrapeCreators).
- Счётчик «осталось» у `sc.py` общий для всех сессий и помощников: «Расход» считать по своим вызовам, а не по разнице счётчика.
- Tavily и поисковики отдают сохранённые копии: у популярной страницы отставание ~день, у малоизвестной — месяцы.
- В сессии с подключениями высокого уровня риска (почта, личные соцсети, банк) чужие сайты не читаем.
