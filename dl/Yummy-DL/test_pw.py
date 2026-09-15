from playwright.sync_api import sync_playwright

url = "https://kodikplayer.com/season/43260/5338de5256f9f6a66b3d671de709a712/720p?translations=false&only_episode=true&only_season=true&episode=2"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    def on_req(req):
        if 'm3u8' in req.url or 'mp4' in req.url or 'm4s' in req.url or 'txt' in req.url:
            print("FOUND:", req.url)
            
    page.on("request", on_req)
    print("Navigating...")
    page.goto(url, wait_until="domcontentloaded")
    print("Clicking play...")
    page.wait_for_timeout(2000)
    page.mouse.click(400, 300)
    page.wait_for_timeout(5000)
    browser.close()
