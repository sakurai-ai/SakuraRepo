from playwright.sync_api import sync_playwright
import time
from rich.console import Console
from config import load_config

console = Console()

def get_direct_stream_url(iframe_url):
    """
    Открывает iframe в невидимом браузере и перехватывает сетевые запросы
    для получения прямой ссылки на .m3u8 или .mp4 файл.
    """
    console.print(f"[cyan]Ищем прямую ссылку через Playwright для: {iframe_url}[/cyan]")
    stream_url = None
    
    config = load_config()
    is_headless = not config.get("playwright_visible", False)
    proxy_url = config.get("proxy")
    
    proxy_config = None
    if proxy_url:
        proxy_config = {"server": proxy_url}

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=is_headless, 
            args=['--disable-blink-features=AutomationControlled'],
            proxy=proxy_config
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        def on_request(request):
            nonlocal stream_url
            url = request.url
            if 'google' in url or 'yandex' in url or 'mail.ru' in url or 'ad' in url or 'metrika' in url:
                return
                
            # Ищем манифесты видео потоков (.m3u8, .mpd)
            if '.m3u8' in url or '.mpd' in url:
                stream_url = url
            elif 'solodcdn' in url and '/f/' in url and '.jpg' not in url and '.png' not in url: # Прямой поток Kodik
                stream_url = url
            elif 'cdnvideohub' in url and '/video/' in url:
                # Нашли API с видео ссылками!
                stream_url = url
            elif 'cdnvideohub' in url and ('/playlist' in url or '.mp4' in url):
                if not stream_url:
                    stream_url = url
            elif '.mp4' in url and 'segment' not in url:
                if not stream_url:
                    stream_url = url

        page.on("request", on_request)

        try:
            # Чтобы обойти X-Frame-Options и проверку на Рикролл, мы идем на сам YummyAnime,
            # и уже там подменяем контент страницы на наш iframe!
            # Так мы будем на правильном домене (origin), и плеер нам поверит.
            
            # Мокаем Referer через route
            page.route("**/*", lambda route: route.continue_(headers={**route.request.headers, "Referer": "https://ru.yummyani.me/"}))
            
            # Идем на корень сайта
            page.goto("https://ru.yummyani.me/", timeout=15000, wait_until="domcontentloaded")
            
            # Встраиваем плеер прямо в их сайт!
            js_code = f"""
            document.body.innerHTML = '<iframe id="hack_iframe" src="{iframe_url}" style="position:fixed; top:0; left:0; width:100%; height:100%; border:none; z-index:999999;"></iframe>';
            """
            page.evaluate(js_code)
            
            page.wait_for_timeout(3000)
            
            if not stream_url:
                console.print("[dim]Пытаемся нажать Play...[/dim]")
                try:
                    # Ищем внутри iframe
                    frame = page.frames[1] if len(page.frames) > 1 else page
                    frame.click('.play_button', timeout=3000, force=True)
                except:
                    page.mouse.click(400, 300)
                
                page.wait_for_timeout(4000)
                
        except Exception as e:
            console.print(f"[dim]Playwright timeout или ошибка (это нормально): {e}[/dim]")
            
        finally:
            browser.close()

    # Если мы поймали API-запрос от CVH, нам нужно распаковать его
    if stream_url and 'cdnvideohub' in stream_url:
        import requests
        try:
            headers = {
                "Referer": "https://ru.yummyani.me/",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
            }
            
            req_proxies = None
            if proxy_url:
                req_proxies = {"http": proxy_url, "https": proxy_url}
                
            # Если поймали плейлист, достаем из него vkId и формируем ссылку на видео
            if '/playlist' in stream_url:
                r_playlist = requests.get(stream_url, headers=headers, proxies=req_proxies).json()
                items = r_playlist.get('items', [])
                if items and 'vkId' in items[0]:
                    vk_id = items[0]['vkId']
                    stream_url = f"https://plapi.cdnvideohub.com/api/v1/player/sv/video/{vk_id}"
            
            # Если у нас ссылка на видео, достаем hlsUrl
            if '/video/' in stream_url:
                r_video = requests.get(stream_url, headers=headers, proxies=req_proxies).json()
                if 'sources' in r_video and 'hlsUrl' in r_video['sources']:
                    stream_url = r_video['sources']['hlsUrl']
        except Exception as e:
            pass

    return stream_url
