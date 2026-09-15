"""Public-page parser/downloader for hentaihaven.co.

The parser reads genre pages and watch pages, then extracts the public player
parameters exposed by nhplayer.com. It does not log in, solve CAPTCHAs, or
attempt to bypass access controls.

Examples:
    python hentaihaven_parser.py genres
    python hentaihaven_parser.py list --genre anal --pages 2
    python hentaihaven_parser.py download --genre anal --pages 1 --limit 10
"""

from __future__ import annotations
import sys

import argparse
import base64
import json
import logging
import re
import time
import random

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable, Iterator
from urllib.parse import parse_qs, urlencode, urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

try:
    # curl_cffi can impersonate Chrome's TLS/HTTP2 fingerprint. This is useful
    # for ordinary hotlink protection; it is not a CAPTCHA or access-control
    # bypass.
    from curl_cffi import requests as curl_requests
except ImportError:  # optional dependency; requests remains the fallback
    curl_requests = None

NETWORK_ERRORS = (requests.RequestException,)
if curl_requests is not None:
    NETWORK_ERRORS += (curl_requests.exceptions.RequestException,)


BASE_URL = "https://hentaihaven.co/"
PLAYER_HOSTS = {"nhplayer.com", "www.nhplayer.com"}

# Explicitly excluded because the labels describe minors or age-ambiguous
# characters. The list is checked against both the requested genre and page
# URLs/titles before any media URL is downloaded.
BLOCKED_GENRES = {'loli', 'shota', 'lolicon', 'shotacon'}

GENRE_RU = {
    "3d": "3D-анимация",
    "ahegao": "Ахэгао",
    "anal": "Анальный секс",
    "bdsm": "БДСМ",
    "big-boobs": "Большая грудь",
    "blow-job": "Минет",
    "bondage": "Бондаж",
    "boob-job": "Титфак",
    "censored": "С цензурой",
    "comedy": "Комедия",
    "cosplay": "Косплей",
    "creampie": "Кремпай",
    "dark-skin": "Тёмная кожа",
    "facial": "Эякуляция на лицо",
    "fantasy": "Фэнтези",
    "filmed": "Съёмка в реалистичном стиле",
    "foot-job": "Футджоб",
    "futanari": "Футанари",
    "gangbang": "Гэнг-бэнг",
    "glasses": "Очки",
    "hand-job": "Мастурбация рукой",
    "harem": "Гарем",
    "hd": "Высокое разрешение",
    "horror": "Ужасы",
    "incest": "Инцест",
    "inflation": "Инфляция тела",
    "lactation": "Лактация",
    "maid": "Горничные",
    "masturbation": "Мастурбация",
    "milf": "Зрелые женщины (MILF)",
    "mind-break": "Психологический слом",
    "mind-control": "Контроль сознания",
    "monster": "Монстры",
    "nekomimi": "Нэкомими",
    "ntr": "NTR (измена и отъём партнёра)",
    "nurse": "Медсёстры",
    "oral": "Оральный секс",
    "orgy": "Оргия",
    "plot": "Сюжетное",
    "pov": "От первого лица (POV)",
    "pregnant": "Беременность",
    "public-sex": "Секс в общественном месте",
    "rape": "Изнасилование",
    "reverse-rape": "Обратное изнасилование",
    "rimjob": "Римминг",
    "scat": "Скат-фетиш",
    "school-girl": "Школьная форма",
    "short": "Короткие видео",
    "softcore": "Мягкая эротика",
    "swimsuit": "Купальники",
    "teacher": "Учительницы",
    "tentacle": "Щупальца",
    "threesome": "Секс втроём",
    "toys": "Секс-игрушки",
    "trap": "Феминные мужские персонажи",
    "tsundere": "Цундэрэ",
    "ugly-bastard": "Некрасивый мужчина (ugly bastard)",
    "uncensored": "Без цензуры",
    "vanilla": "Ванильный секс",
    "virgin": "Девственность",
    "watersports": "Водные фетиши",
    "x-ray": "Рентген",
    "yaoi": "Яой",
    "yuri": "Юри",
}

LOG = logging.getLogger("hentaihaven")


class ParserError(RuntimeError):
    """Raised when a page cannot be parsed safely."""


@dataclass(slots=True)
class Genre:
    name: str
    ru_name: str
    slug: str
    url: str
    count: int | None = None


@dataclass(slots=True)
class Video:
    title: str
    url: str
    slug: str
    genres: list[str] = field(default_factory=list)
    series: str | None = None
    release_date: str | None = None
    cover_url: str | None = None
    media_url: str | None = None
    subtitle_url: str | None = None
    media_referer: str | None = None
    player_url: str | None = None

    @property
    def title_group(self) -> str:
        """Folder name shared by all episodes of one title."""
        if self.series:
            return self.series
        # Fallback for pages where the series link is missing.
        value = re.sub(r"\s+(?:episode|ep\.?|часть|серия)\s*\d+.*$", "", self.title, flags=re.I)
        return value.strip() or self.title


def random_sleep(min_s: float, max_s: float) -> None:
    time.sleep(random.uniform(min_s, max_s))


def clean_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def safe_filename(value: str, max_length: int = 160) -> str:
    value = re.sub(r"[<>:\"/\\|?*\x00-\x1f]", "_", value)
    value = re.sub(r"\s+", " ", value).strip(" .")
    return (value or "video")[:max_length].rstrip(" .")


def decode_b64(value: str) -> str:
    """Decode standard or URL-safe base64 used in nhplayer data-id values."""
    try:
        padded = value + "=" * (-len(value) % 4)
        return base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8")
    except (ValueError, UnicodeError) as exc:
        raise ParserError("Некорректный base64-параметр плеера") from exc


class HentaiHavenClient:
    def __init__(
        self,
        *,
        base_url: str = BASE_URL,
        delay: float = 1.5,
        timeout: float = 60,
        ignore_robots: bool = False,
        impersonate_browser: bool = True,
    ) -> None:
        self.base_url = base_url.rstrip("/") + "/"
        self.delay = max(0.0, delay)
        self.timeout = timeout
        self._retry = 3
        if impersonate_browser and curl_requests is not None:
            self.session = curl_requests.Session(impersonate="chrome")
            LOG.info("Используется Chrome TLS/HTTP2 impersonation")
        else:
            self.session = requests.Session()
            if impersonate_browser:
                LOG.info("curl_cffi не установлен; используется requests")
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml",
            }
        )
        self._last_request = 0.0
        self.robots = RobotFileParser()
        self.robots.set_url(urljoin(self.base_url, "robots.txt"))
        self._robots_loaded = False
        self.ignore_robots = ignore_robots

    def _check_robots(self, url: str) -> None:
        if self.ignore_robots:
            return
        # robots.txt from hentaihaven.co does not govern a separate CDN host.
        # The media host is still accessed only through a public URL exposed by
        # the page; checking the source site's robots rules is sufficient here.
        if urlparse(url).netloc.lower() != urlparse(self.base_url).netloc.lower():
            return
        if not self._robots_loaded:
            try:
                robots_url = urljoin(self.base_url, "robots.txt")
                response = self.session.get(
                    robots_url,
                    headers={"User-Agent": self.session.headers["User-Agent"]},
                    timeout=self.timeout,
                )
                if response.status_code == 404:
                    self.robots.parse([])
                else:
                    response.raise_for_status()
                    self.robots.parse(response.text.splitlines())
            except NETWORK_ERRORS as exc:  # network: fail closed
                raise ParserError(
                    "Не удалось прочитать robots.txt; используйте --ignore-robots "
                    "только если это разрешено владельцем сайта."
                ) from exc
            self._robots_loaded = True
        if not self.robots.can_fetch(self.session.headers["User-Agent"], url):
            raise ParserError(f"Запрос запрещён robots.txt: {url}")

    def get(self, url: str, *, referer: str | None = None) -> requests.Response:
        self._check_robots(url)
        wait = self.delay - (time.monotonic() - self._last_request)
        if wait > 0:
            time.sleep(wait)
        headers = {"Referer": referer} if referer else {}
        last_exc: Exception | None = None
        for attempt in range(1, self._retry + 1):
            try:
                response = self.session.get(url, headers=headers, timeout=self.timeout)
                self._last_request = time.monotonic()
                response.raise_for_status()
                return response
            except Exception as exc:
                last_exc = exc
                LOG.warning("Попытка %d/%d не удалась для %s: %s", attempt, self._retry, url, exc)
                if attempt < self._retry:
                    random_sleep(2.0, 6.0)
        raise ParserError(f"Ошибка запроса к {url} после {self._retry} попыток: {last_exc}")

    def soup(self, url: str, *, referer: str | None = None) -> BeautifulSoup:
        response = self.get(url, referer=referer)
        return BeautifulSoup(response.text, "html.parser")

    def genres(self) -> list[Genre]:
        url = urljoin(self.base_url, "genres/")
        response = self.get(url)
        print(f"DEBUG: {url} -> {response.status_code}")
        print(f"DEBUG: HTML length: {len(response.text)}")
        soup = BeautifulSoup(response.text, "html.parser")
        result: list[Genre] = []
        seen: set[str] = set()
        for link in soup.select('a[href*="/genre/"]'):
            href = urljoin(self.base_url, link.get("href", ""))
            parsed = urlparse(href)
            match = re.search(r"/genre/([^/]+)/?", parsed.path)
            if not match:
                continue
            slug = match.group(1).lower()
            if slug in seen or slug in BLOCKED_GENRES:
                continue
            seen.add(slug)
            text = clean_text(link.get_text(" ", strip=True))
            count_match = re.search(r"(\d[\d,]*)\s*$", text)
            count = int(count_match.group(1).replace(",", "")) if count_match else None
            name = clean_text(text[: count_match.start()] if count_match else text)
            result.append(
                Genre(
                    name=name or slug,
                    ru_name=GENRE_RU.get(slug, name or slug),
                    slug=slug,
                    url=href,
                    count=count,
                )
            )
        return result

    def _assert_allowed(self, *, genre: str | None = None, text: str = "") -> None:
        values = set(re.findall(r"[a-z0-9-]+", (genre or "").lower()))
        values.update(re.findall(r"[a-z0-9-]+", text.lower()))
        blocked = values & BLOCKED_GENRES
        if blocked:
            raise ParserError(f"Категория отфильтрована как небезопасная: {sorted(blocked)}")

    def video_links(self, genre: str, page: int = 1) -> list[tuple[str, str]]:
        slug = genre.strip().lower().strip("/")
        if slug in BLOCKED_GENRES:
            raise ParserError(f"Жанр запрещён фильтром безопасности: {slug}")
        path = f"genre/{slug}/"
        url = urljoin(self.base_url, path)
        if page > 1:
            url += "?" + urlencode({"page": page})
        soup = self.soup(url)
        result: list[tuple[str, str]] = []
        seen: set[str] = set()
        for link in soup.select('a[href*="/watch/"]'):
            href = urljoin(self.base_url, link.get("href", ""))
            parsed = urlparse(href)
            if parsed.netloc and parsed.netloc != urlparse(self.base_url).netloc:
                continue
            match = re.search(r"/watch/([^/]+)/?", parsed.path)
            if not match or href in seen:
                continue
            title = clean_text(link.get("aria-label") or link.get_text(" ", strip=True))
            self._assert_allowed(genre=slug, text=title)
            seen.add(href)
            result.append((title or match.group(1), href))
        return result

    def iter_video_links(self, genre: str, pages: int) -> Iterator[tuple[str, str]]:
        seen: set[str] = set()
        for page in range(1, max(1, pages) + 1):
            links = self.video_links(genre, page)
            if not links:
                break
            for title, url in links:
                if url not in seen:
                    seen.add(url)
                    yield title, url

    def parse_video(self, url: str, *, fallback_title: str = "") -> Video:
        soup = self.soup(url, referer=self.base_url)
        title_node = soup.find("h1")
        title = clean_text(title_node.get_text(" ", strip=True) if title_node else "")
        title = title or fallback_title or urlparse(url).path.rstrip("/").split("/")[-1]
        self._assert_allowed(text=title)
        match = re.search(r"/watch/([^/]+)/?", urlparse(url).path)
        if not match:
            raise ParserError(f"Не удалось определить slug: {url}")

        genres = [clean_text(a.get_text(" ", strip=True)) for a in soup.select('a[href*="/genre/"]')]
        genres = [g for g in genres if g]
        self._assert_allowed(text=" ".join(genres))
        # Exclude the navigation link `/series/`; keep only a concrete series
        # page such as `/series/deco-x-deco-the-animation/`.
        series_link = next(
            (
                node
                for node in soup.select('a[href^="/series/"]')
                if re.fullmatch(r"/series/[^/]+/?", node.get("href", ""))
            ),
            None,
        )
        series = clean_text(series_link.get_text(" ", strip=True)) if series_link else None
        cover = soup.select_one('img[alt*="cover" i], img')
        cover_url = urljoin(url, cover.get("src")) if cover and cover.get("src") else None

        release_date = None
        labels = soup.select("body *")
        for node in labels:
            text = clean_text(node.get_text(" ", strip=True))
            if text.lower() == "release date":
                sibling = node.find_next(string=re.compile(r"\d{4}-\d{2}-\d{2}"))
                if sibling:
                    release_date = clean_text(str(sibling))
                    break

        player_url = None
        for frame in soup.select("iframe[src]"):
            candidate = urljoin(url, frame.get("src", ""))
            host = urlparse(candidate).netloc.lower()
            if host in PLAYER_HOSTS and "/v/" in urlparse(candidate).path:
                player_url = candidate
                break

        video = Video(
            title=title,
            url=url,
            slug=match.group(1),
            genres=genres,
            series=series,
            release_date=release_date,
            cover_url=cover_url,
        )
        if player_url:
            self._populate_player(video, player_url, referer=url)
        return video

    def _populate_player(self, video: Video, player_url: str, *, referer: str) -> None:
        soup = self.soup(player_url, referer=referer)
        server = soup.select_one(".servers li[data-id]")
        if not server:
            LOG.warning("Плеер не раскрыл сервер для %s", video.url)
            return
        # The CDN hotlink-checks the player origin. A browser video element
        # sends the player page as Referer, not the HentaiHaven watch page.
        video.media_referer = player_url
        data_id = server.get("data-id", "")
        # Store the exact player.php URL so we can bypass UI clicking later
        video.player_url = urljoin(player_url, data_id)

        query = parse_qs(urlparse(video.player_url).query)
        encoded_media = query.get("vid", [""])[0]
        if encoded_media:
            decoded = decode_b64(encoded_media)
            media_url = decoded.split("|", 1)[0]
            if urlparse(media_url).scheme in {"http", "https"}:
                video.media_url = media_url
        encoded_subtitle = query.get("s", [""])[0]
        if encoded_subtitle:
            subtitle = decode_b64(encoded_subtitle)
            if urlparse(subtitle).scheme in {"http", "https"}:
                video.subtitle_url = subtitle
        encoded_cover = query.get("i", [""])[0]
        if encoded_cover:
            cover = decode_b64(encoded_cover)
            if urlparse(cover).scheme in {"http", "https"}:
                video.cover_url = cover

    def download(self, video: Video, output_dir: Path, *, overwrite: bool = False) -> Path:
        if not video.media_url:
            raise ParserError(f"Прямая ссылка недоступна: {video.url}")
        title_dir = output_dir / safe_filename(video.title_group)
        title_dir.mkdir(parents=True, exist_ok=True)
        target = title_dir / f"{safe_filename(video.title)}.mp4"
        if target.exists() and not overwrite:
            LOG.info("Пропуск существующего файла: %s", target)
            return target
        self._check_robots(video.media_url)
        wait = self.delay - (time.monotonic() - self._last_request)
        if wait > 0:
            time.sleep(wait)
        response = self.session.get(
            video.media_url,
            headers={
                "Referer": video.media_referer or "https://nhplayer.com/",
                "Origin": "https://nhplayer.com",
                "Accept": "*/*",
                "Range": "bytes=0-",
            },
            stream=True,
            timeout=self.timeout,
        )
        try:
            self._last_request = time.monotonic()
            response.raise_for_status()
            total_size = int(response.headers.get("content-length", 0))
            downloaded = 0
            with target.open("wb") as handle:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        handle.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            percent = (downloaded / total_size) * 100
                            bar_length = 40
                            filled_length = int(bar_length * downloaded // total_size)
                            bar = '█' * filled_length + '░' * (bar_length - filled_length)
                            sys.stdout.write(f'\r\033[92mЗагрузка:\033[0m [{bar}] {percent:.1f}% ({downloaded/(1024*1024):.1f}MB / {total_size/(1024*1024):.1f}MB)')
                            sys.stdout.flush()
                        else:
                            sys.stdout.write(f'\r\033[92mЗагрузка:\033[0m {downloaded/(1024*1024):.1f}MB')
                            sys.stdout.flush()
            print()
        finally:
            response.close()
        return target


class BrowserDownloadSession:
    def __init__(self, *, headless: bool = False, timeout_ms: int = 120_000, proxy: str | None = None) -> None:
        self.headless = headless
        self.timeout_ms = timeout_ms
        self.proxy = proxy
        self.playwright = None
        self.browser = None
        self.context = None
        self.http = None

    def __enter__(self) -> "BrowserDownloadSession":
        try:
            # Импортируем скрытый Playwright, который вырезает рантайм-утечки
            from rebrowser_playwright.sync_api import sync_playwright
            self.playwright = sync_playwright().start()
            
            # Запускаем реальный Google Chrome с коммерческими медиа-кодеками
            self.browser = self.playwright.chromium.launch(
                headless=self.headless,
                channel="chrome",
                args=["--disable-blink-features=AutomationControlled", "--disable-infobars", "--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
                proxy={"server": self.proxy} if self.proxy else None
            )
            self.context = self.browser.new_context(
                accept_downloads=True,
                viewport={"width": 1920, "height": 1080},
                device_scale_factor=1,
                is_mobile=False,
                has_touch=False,
                locale="en-US",
                timezone_id="America/New_York",
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
            )
            # Принудительно зачищаем флаг автоматизации на страницах
            # (Удалено: эта команда приводила к краху rebrowser-playwright на пустых iframe)
            
            # Сессия для прямой скачки потока
            try:
                from curl_cffi import requests as curl_requests
                self.http = curl_requests.Session(impersonate="chrome")
            except ImportError:
                import requests
                self.http = requests.Session()
                
            return self
        except Exception as exc:
            self.close()
            raise ParserError(f"Ошибка запуска Chrome: {exc}")

    def close(self) -> None:
        if self.http: self.http.close()
        if self.context: self.context.close()
        if self.browser: self.browser.close()
        if self.playwright: self.playwright.stop()

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()

    def download(self, video: Video, output_dir: Path, *, overwrite: bool = False) -> Path:
        title_dir = output_dir / safe_filename(video.title_group)
        title_dir.mkdir(parents=True, exist_ok=True)
        target = title_dir / f"{safe_filename(video.title)}.mp4"
        if target.exists() and not overwrite:
            return target
        
        page = self.context.new_page()
        try:
            # Парсер ранее вытаскивал URL из JSON (vid), но недавно они добавили 
            # защиту: к URL нужно добавлять динамический параметр ?verify=..., 
            # который генерируется только если пройти JS-проверку (Proof-of-Work).
            # Скрипт player-core-v2.php проверяет бота и если находит - выдает ошибку.
            # Мы перехватим скрипт защиты и вырежем проверку на бота!
            
            real_url = None
            def handle_route(route):
                if "player-core-v2.php" in route.request.url:
                    resp = route.fetch()
                    body = resp.text()
                    # Полностью вырезаем функцию обнаружения Playwright, чтобы 
                    # сервер не получил флаги обнаружения в параметре `df`!
                    body = body.replace("var _NbXkcYfU=function(){", "var _NbXkcYfU=function(){ return []; ")
                    body = body.replace("return blockFlags.includes(f);", "return false;")
                    body = body.replace("if(w._pC)w._pC.error=new Error('blocked');", "")
                    route.fulfill(response=resp, body=body)
                else:
                    route.continue_()
            
            # Включаем перехват запросов
            page.route("**/*", handle_route)
            
            # Слушаем ответ от сервера, который выдаст нам финальную ссылку с токеном verify
            def handle_response(response):
                nonlocal real_url
                if "get-video-url-v2.php" in response.url:
                    try:
                        data = response.json()
                        if "url" in data:
                            real_url = data["url"]
                            LOG.info("Успешно получен верифицированный URL с токеном!")
                    except Exception:
                        pass
                        
            page.on("response", handle_response)
            
            LOG.info("Запускаю плеер для прохождения JS-проверки и генерации токена...")
            
            if not video.player_url:
                raise ParserError("Плеер URL отсутствует! Не удалось извлечь его ранее.")
                
            LOG.info("Перехожу напрямую в плеер (в обход UI): %s", video.player_url)
            page.goto(video.player_url, wait_until="domcontentloaded", timeout=30_000, referer=video.media_referer or video.url)
            
            # Ждем пока скрипты на странице плеера отработают и пришлют нам JSON
            # с реальным URL
            page.wait_for_timeout(10000)
            
            if not real_url:
                raise ParserError("Не удалось получить верифицированную ссылку (token) от плеера!")
            
            LOG.info("Инициирую скачивание через curl_cffi...")
            
            cookies = {item["name"]: item["value"] for item in self.context.cookies([real_url])}
            headers = {
                "Referer": "https://nhplayer.com/",
                "Accept": "*/*",
                "Range": "bytes=0-",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"
            }
            
            response = self.http.get(real_url, headers=headers, cookies=cookies, stream=True, timeout=60)
            response.raise_for_status()
            
            total_size = int(response.headers.get("content-length", 0))
            downloaded = 0
            with target.open("wb") as handle:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk: 
                        handle.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            percent = (downloaded / total_size) * 100
                            bar_length = 40
                            filled_length = int(bar_length * downloaded // total_size)
                            bar = '█' * filled_length + '░' * (bar_length - filled_length)
                            sys.stdout.write(f'\r\033[92mЗагрузка:\033[0m [{bar}] {percent:.1f}% ({downloaded/(1024*1024):.1f}MB / {total_size/(1024*1024):.1f}MB)')
                            sys.stdout.flush()
                        else:
                            sys.stdout.write(f'\r\033[92mЗагрузка:\033[0m {downloaded/(1024*1024):.1f}MB')
                            sys.stdout.flush()
            print()
            
            # Выключаем перехват, чтобы не мешал дальше
            page.unroute("**/*", handle_route)
            
            return target
        finally:
            page.close()


def write_jsonl(items: Iterable[Video], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for item in items:
            handle.write(json.dumps(asdict(item), ensure_ascii=False) + "\n")


def build_cli() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Парсер публичных страниц hentaihaven.co")
    parser.add_argument("--delay", type=float, default=1.5, help="Пауза между запросами в секундах")
    parser.add_argument("--ignore-robots", action="store_true", help="Не проверять robots.txt (только с разрешения владельца)")
    parser.add_argument("--proxy", type=str, default=None, help="Прокси-сервер (например, http://user:pass@host:port)")

    sub = parser.add_subparsers(dest="command")

    sub.add_parser("genres", help="Вывести доступные жанры")
    sub.add_parser("menu", help="Запустить интерактивное меню")

    list_cmd = sub.add_parser("list", help="Собрать метаданные видео в JSONL")
    list_cmd.add_argument("--genre", required=True)
    list_cmd.add_argument("--pages", type=int, default=1)
    list_cmd.add_argument("--output", type=Path, default=Path("videos.jsonl"))

    download_cmd = sub.add_parser("download", help="Собрать и скачать видео")
    download_cmd.add_argument("--genre", required=True)
    download_cmd.add_argument("--pages", type=int, default=1)
    download_cmd.add_argument("--limit", type=int, default=0, help="0 — без лимита")
    download_cmd.add_argument("--output-dir", type=Path, default=Path("downloads"))
    download_cmd.add_argument("--metadata", type=Path, default=Path("videos.jsonl"))
    download_cmd.add_argument("--overwrite", action="store_true")
    return parser


def ask_int(prompt: str, *, default: int, minimum: int = 0) -> int:
    while True:
        raw = input(f"{prompt} [{default}]: ").strip()
        if not raw:
            return default
        try:
            value = int(raw)
        except ValueError:
            print("Введите целое число.")
            continue
        if value < minimum:
            print(f"Значение должно быть не меньше {minimum}.")
            continue
        return value


def interactive_menu(client: HentaiHavenClient) -> int:
    print("\033[38;2;252;209;215m" + r"""
     __  ____  ______  ___    ____  _____ __________ 
   / / / / / / / __ \/   |  / __ \/ ___// ____/ __ \
  / /_/ / /_/ / /_/ / /| | / /_/ /\__ \/ __/ / /_/ /
 / __  / __  / ____/ ___ |/ _, _/___/ / /___/ _, _/ 
/_/ /_/_/ /_/_/   /_/  |_/_/ |_|/____/_____/_/ |_|  
                                                    
(hparser)
by sakuraidev
v1.0.0
""" + "\033[0m")
    print("Загружаю список жанров...")
    genres = client.genres()
    if not genres:
        print("Жанры не найдены.")
        return 1

    for index, genre in enumerate(genres, start=1):
        print(f"{index:>3}. {genre.name} — {genre.ru_name}")

    while True:
        choice = input("\nВыберите жанр по номеру или slug (q — выход): ").strip()
        if choice.lower() in {"q", "quit", "выход"}:
            return 0
        selected: Genre | None = None
        if choice.isdigit() and 1 <= int(choice) <= len(genres):
            selected = genres[int(choice) - 1]
        else:
            selected = next((item for item in genres if item.slug == choice.lower().strip("/")), None)
        if selected:
            break
        print("Такого жанра нет.")

    pages = ask_int("Сколько страниц обработать", default=1, minimum=1)
    limit = ask_int("Лимит эпизодов (0 — без лимита)", default=0, minimum=0)
    output_dir = Path(input("Папка загрузки [downloads]: ").strip() or "downloads")
    metadata = Path(input("Файл метаданных [videos.jsonl]: ").strip() or "videos.jsonl")
    proxy = input("Прокси-сервер [пусто]: ").strip() or None

    visible = input("Показывать окно Playwright? [y/N]: ").strip().lower()
    headless = visible not in {"y", "yes", "д", "да"}

    videos: list[Video] = []
    print(f"\nОбрабатываю жанр: {selected.name}")
    with BrowserDownloadSession(headless=headless, proxy=proxy) as browser:
        for title, url in client.iter_video_links(selected.slug, pages):
            try:
                video = client.parse_video(url, fallback_title=title)
            except ParserError as exc:
                LOG.warning("Пропуск %s: %s", url, exc)
                continue
            videos.append(video)
            try:
                path = browser.download(video, output_dir)
                print(f"Скачано: {path}")
            except NETWORK_ERRORS + (ParserError,) as exc:
                LOG.warning("Не удалось скачать %s: %s", video.url, exc)
            if limit and len(videos) >= limit:
                break
    print(f"DEBUG: main started with command: {args.command}")



    write_jsonl(videos, metadata)
    print(f"\nГотово. Эпизодов: {len(videos)}. Метаданные: {metadata}")
    return 0


def main() -> int:
    args = build_cli().parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    client = HentaiHavenClient(delay=args.delay, ignore_robots=args.ignore_robots)

    if args.command in {None, "menu"}:
        return interactive_menu(client)

    if args.command == "genres":
        for genre in client.genres():
            print(f"{genre.name} — {genre.ru_name}")
        return 0

    videos: list[Video] = []
    
    if args.command == "download":
        with BrowserDownloadSession(headless=True, proxy=args.proxy) as browser:
            for title, url in client.iter_video_links(args.genre, args.pages):
                try:
                    video = client.parse_video(url, fallback_title=title)
                except ParserError as exc:
                    LOG.warning("Пропуск %s: %s", url, exc)
                    continue
                videos.append(video)
                
                try:
                    path = browser.download(video, args.output_dir, overwrite=args.overwrite)
                    LOG.info("Скачано через Stealth-браузер: %s", path)
                except NETWORK_ERRORS + (ParserError,) as exc:
                    LOG.warning("Не удалось скачать %s: %s", video.url, exc)
                    
                if getattr(args, "limit", 0) and len(videos) >= args.limit:
                    break
    else:
        for title, url in client.iter_video_links(args.genre, args.pages):
            try:
                video = client.parse_video(url, fallback_title=title)
            except ParserError as exc:
                LOG.warning("Пропуск %s: %s", url, exc)
                continue
            videos.append(video)
            if getattr(args, "limit", 0) and len(videos) >= args.limit:
                break

    output = args.output if args.command == "list" else args.metadata
    write_jsonl(videos, output)
    LOG.info("Метаданные сохранены: %s (%d записей)", output, len(videos))
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())

