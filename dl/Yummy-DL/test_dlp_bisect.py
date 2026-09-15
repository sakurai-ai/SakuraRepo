import requests
import subprocess
r_playlist = requests.get("https://plapi.cdnvideohub.com/api/v1/player/sv/playlist?pub=745&aggr=mali&id=37982&ep=1", headers={"Referer": "https://ru.yummyani.me/"}).json()
vk_id = r_playlist['items'][0]['vkId']
r_video = requests.get(f"https://plapi.cdnvideohub.com/api/v1/player/sv/video/{vk_id}", headers={"Referer": "https://ru.yummyani.me/"}).json()
hlsUrl = r_video['sources']['hlsUrl']

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-us,en;q=0.5",
    "Sec-Fetch-Mode": "navigate",
    "Accept-Encoding": "identity",
    "Connection": "close"
}

for k, v in headers.items():
    res = subprocess.run(['curl', '-s', '-o', '/dev/null', '-w', f'With {k}: %{{http_code}}\\n', '-H', f'{k}: {v}', hlsUrl], capture_output=True, text=True)
    print(res.stdout.strip())
