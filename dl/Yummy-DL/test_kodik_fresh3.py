import requests
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
    'Referer': 'https://ru.yummyani.me/',
    'X-Requested-With': 'XMLHttpRequest'
}
videos = requests.get("https://ru.yummyani.me/api/anime/253/videos", headers=headers).json()
for v in videos['response']:
    if 'kodik' in v['data']['player'].lower():
        print("Fresh Kodik URL:", v['iframe_url'])
        break
