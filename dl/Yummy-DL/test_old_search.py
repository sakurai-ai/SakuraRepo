import requests

url = "https://old.yummyani.me/api/search?q=Домекано&limit=5&offset=0"
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
    'Referer': 'https://old.yummyani.me/',
    'X-Requested-With': 'XMLHttpRequest'
}
resp = requests.get(url, headers=headers)
print("Search code:", resp.status_code)
data = resp.json()
if 'data' in data: data = data['data']
for anime in data.get('response', []):
    print("Found anime:", anime['id'])
    videos = requests.get(f"https://old.yummyani.me/api/anime/{anime['id']}/videos", headers=headers).json()
    for v in videos.get('response', []):
        if 'kodik' in v.get('data', {}).get('player', '').lower() and v.get('number') == '1':
            print("Old Yummy Kodik Ep 1:", v['iframe_url'])
            break
    break
