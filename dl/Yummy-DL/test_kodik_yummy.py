import requests

anime_id = 37982
url = f"https://ru.yummyani.me/api/anime/{anime_id}/videos"
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
    'Referer': 'https://ru.yummyani.me/',
    'X-Requested-With': 'XMLHttpRequest'
}
resp = requests.get(url, headers=headers).json()
for video in resp.get('data', {}).get('response', []):
    if 'kodik' in video.get('data', {}).get('player', '').lower():
        print("KODIK IFRAME URL:", video.get('iframe_url'))
        break
