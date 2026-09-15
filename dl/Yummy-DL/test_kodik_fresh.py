import requests

url = "https://ru.yummyani.me/api/search?q=Домекано&limit=5&offset=0"
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
    'Referer': 'https://ru.yummyani.me/',
    'X-Requested-With': 'XMLHttpRequest'
}
resp = requests.get(url, headers=headers)
print("Search code:", resp.status_code)
data = resp.json()

# if data exists
if 'data' in data and 'response' in data['data']:
    for anime in data['data']['response']:
        print("Found anime:", anime['id'])
        videos_url = f"https://ru.yummyani.me/api/anime/{anime['id']}/videos"
        videos = requests.get(videos_url, headers=headers).json()
        for v in videos.get('data', {}).get('response', []):
            if 'kodik' in v['data']['player'].lower():
                print("Fresh Kodik URL:", v['iframe_url'])
                break
        break
else:
    print("No data:", data)
