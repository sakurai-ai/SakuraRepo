from playwright.sync_api import sync_playwright

url = "https://kodikplayer.com/season/43260/5338de5256f9f6a66b3d671de709a712/720p?translations=false&only_episode=true&only_season=true&episode=2"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=['--disable-blink-features=AutomationControlled'])
    context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36")
    page = context.new_page()
    
    def on_req(req):
        if 'gvi' in req.url or 'm3u8' in req.url or 'mp4' in req.url or 'solodcdn' in req.url:
            print("TARGET REQ:", req.url)
            
    page.on("request", on_req)
    print("Navigating...")
    page.goto(url, wait_until="domcontentloaded")
    
    print("Waiting for play button...")
    try:
        page.wait_for_selector('.play_button', timeout=5000)
        print("Clicking play button...")
        page.click('.play_button')
    except Exception as e:
        print("Play button not found or error:", e)
        
    page.wait_for_timeout(5000)
    browser.close()
