import requests
import subprocess
r_playlist = requests.get("https://plapi.cdnvideohub.com/api/v1/player/sv/playlist?pub=745&aggr=mali&id=37982&ep=1", headers={"Referer": "https://ru.yummyani.me/"}).json()
vk_id = r_playlist['items'][0]['vkId']
r_video = requests.get(f"https://plapi.cdnvideohub.com/api/v1/player/sv/video/{vk_id}", headers={"Referer": "https://ru.yummyani.me/"}).json()
hlsUrl = r_video['sources']['hlsUrl']
print("URL:", hlsUrl)
subprocess.run(['curl', '-s', '-o', '/dev/null', '-w', '%{http_code}\\n', hlsUrl])
