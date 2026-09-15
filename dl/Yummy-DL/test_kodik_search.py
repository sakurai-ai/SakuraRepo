import requests

url = "https://ru.yummyani.me/api/search?q=домекано&limit=5&offset=0"
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
    'Referer': 'https://ru.yummyani.me/',
    'X-Requested-With': 'XMLHttpRequest'
}
resp = requests.get(url, headers=headers).json()
anime_id = resp['data']['response'][0]['id']

videos_url = f"https://ru.yummyani.me/api/anime/{anime_id}/videos"
videos = requests.get(videos_url, headers=headers).json()
for v in videos['data']['response']:
    player = v['data']['player']
    iframe = v['iframe_url']
    print(player, "->", iframe)
