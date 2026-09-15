from playwright.sync_api import sync_playwright

iframe_url = "https://ru.yummyani.me/iframeCVH.html?dubbing_code=AnilibriaTV&anime_id=37982&episode=1"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=['--disable-blink-features=AutomationControlled'])
    context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
    page = context.new_page()
    
    def on_request(request):
        url = request.url
        if '.m3u8' in url or '.mpd' in url or 'solodcdn' in url or 'cdnvideohub' in url:
            if '.jpg' not in url and '.png' not in url:
                print("FOUND TARGET:", url)
                
    page.on("request", on_request)
    
    page.route("**/*", lambda route: route.continue_(headers={**route.request.headers, "Referer": "https://ru.yummyani.me/"}))
    page.goto("https://ru.yummyani.me/", timeout=15000, wait_until="domcontentloaded")
    
    js_code = f"""
    document.body.innerHTML = '<iframe id="hack_iframe" src="{iframe_url}" style="position:fixed; top:0; left:0; width:100%; height:100%; border:none; z-index:999999;"></iframe>';
    """
    page.evaluate(js_code)
    print("Injected iframe...")
    
    page.wait_for_timeout(5000)
    
    # Try to click the center of the iframe
    print("Clicking center...")
    page.mouse.click(400, 300)
    
    page.wait_for_timeout(5000)
    browser.close()
