from playwright.sync_api import sync_playwright

url = "https://kodikplayer.com/season/43260/5338de5256f9f6a66b3d671de709a712/720p?translations=false&only_episode=true&only_season=true&episode=1"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    )
    page = context.new_page()
    page.goto(url, wait_until="domcontentloaded", referer="https://old.yummyani.me/")
    page.wait_for_timeout(3000)
    print("HTML length:", len(page.content()))
    if "данной страницы не существует" in page.content():
        print("ERROR: PAGE DOES NOT EXIST")
    else:
        print("SUCCESS! Page exists!")
    browser.close()
