from playwright.sync_api import sync_playwright
url = "https://kodikplayer.com/season/43260/5338de5256f9f6a66b3d671de709a712/720p?translations=false&only_episode=true&only_season=true&episode=2"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=['--disable-blink-features=AutomationControlled'])
    page = browser.new_page()
    page.goto(url, wait_until="domcontentloaded")
    
    # print all button or iframe elements to see what we can click
    page.wait_for_timeout(3000)
    html = page.content()
    with open("kodik_html.html", "w") as f:
        f.write(html)
    browser.close()
