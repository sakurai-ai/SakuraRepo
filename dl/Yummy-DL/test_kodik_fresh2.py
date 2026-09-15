import requests
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
    'Referer': 'https://ru.yummyani.me/',
    'X-Requested-With': 'XMLHttpRequest'
}
videos_url = "https://ru.yummyani.me/api/anime/253/videos"
videos = requests.get(videos_url, headers=headers).json()
for v in videos.get('response', []):
    if 'kodik' in v['player'].lower():
        print("Fresh Kodik URL:", v['iframe_url'])
        break
