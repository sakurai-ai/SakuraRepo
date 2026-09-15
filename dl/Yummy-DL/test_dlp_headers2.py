import requests
import subprocess
r_playlist = requests.get("https://plapi.cdnvideohub.com/api/v1/player/sv/playlist?pub=745&aggr=mali&id=37982&ep=1", headers={"Referer": "https://ru.yummyani.me/"}).json()
vk_id = r_playlist['items'][0]['vkId']
r_video = requests.get(f"https://plapi.cdnvideohub.com/api/v1/player/sv/video/{vk_id}", headers={"Referer": "https://ru.yummyani.me/"}).json()
hlsUrl = r_video['sources']['hlsUrl']

# test exact yt-dlp headers
headers = [
    "-H", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
    "-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "-H", "Accept-Language: en-us,en;q=0.5",
    "-H", "Sec-Fetch-Mode: navigate",
    "-H", "Accept-Encoding: identity",
    "-H", "Connection: close"
]

subprocess.run(['curl', '-s', '-o', '/dev/null', '-w', 'YT-DLP GET: %{http_code}\\n'] + headers + [hlsUrl])
