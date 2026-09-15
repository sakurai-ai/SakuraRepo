from playwright.sync_api import sync_playwright

iframe_url = "https://ru.yummyani.me/iframeCVH.html?dubbing_code=AnilibriaTV&anime_id=37982&episode=1"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=['--disable-blink-features=AutomationControlled'])
    context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
    page = context.new_page()
    
    page.route("**/*", lambda route: route.continue_(headers={**route.request.headers, "Referer": "https://ru.yummyani.me/"}))
    page.goto("https://ru.yummyani.me/", timeout=15000, wait_until="domcontentloaded")
    
    js_code = f"""
    document.body.innerHTML = '<iframe id="hack_iframe" src="{iframe_url}" style="position:fixed; top:0; left:0; width:100%; height:100%; border:none; z-index:999999;"></iframe>';
    """
    page.evaluate(js_code)
    page.wait_for_timeout(5000)
    
    html = page.content()
    print("Injected HTML length:", len(html))
    
    frames = page.frames
    print("Frames count:", len(frames))
    for f in frames:
        print(" - Frame URL:", f.url)
        
    browser.close()
