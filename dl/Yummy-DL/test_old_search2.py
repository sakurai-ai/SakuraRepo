import requests

url = "https://old.yummyani.me/api/search?q=Домекано&limit=5&offset=0"
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
    'Referer': 'https://old.yummyani.me/',
    'X-Requested-With': 'XMLHttpRequest'
}
data = requests.get(url, headers=headers).json()
if 'data' in data: data = data['data']
for anime in data.get('response', []):
    aid = anime.get('id') or anime.get('anime_id')
    print("Found anime:", aid)
    videos = requests.get(f"https://old.yummyani.me/api/anime/{aid}/videos", headers=headers).json()
    for v in videos.get('response', []):
        if 'kodik' in v.get('data', {}).get('player', '').lower() and v.get('number') == '1':
            print(v['data']['dubbing'], "->", v['iframe_url'])
    break
