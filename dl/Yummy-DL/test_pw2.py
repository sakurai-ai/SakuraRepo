from playwright.sync_api import sync_playwright

url = "https://kodikplayer.com/season/43260/5338de5256f9f6a66b3d671de709a712/720p?translations=false&only_episode=true&only_season=true&episode=2"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=['--disable-blink-features=AutomationControlled'])
    context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
    page = context.new_page()
    
    def on_req(req):
        if not req.url.startswith('data:') and not 'google-analytics' in req.url:
            print("REQ:", req.url)
            
    page.on("request", on_req)
    print("Navigating...")
    page.goto(url, wait_until="domcontentloaded")
    print("Clicking play...")
    page.wait_for_timeout(2000)
    page.mouse.click(400, 300)
    page.wait_for_timeout(4000)
    browser.close()
