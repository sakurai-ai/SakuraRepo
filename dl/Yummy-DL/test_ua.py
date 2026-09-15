import requests
import re
# Get fresh JSON
r_playlist = requests.get("https://plapi.cdnvideohub.com/api/v1/player/sv/playlist?pub=745&aggr=mali&id=37982&ep=1", headers={"Referer": "https://ru.yummyani.me/", "User-Agent": "MyAgent/1.0"}).json()
vk_id = r_playlist['items'][0]['vkId']
r_video = requests.get(f"https://plapi.cdnvideohub.com/api/v1/player/sv/video/{vk_id}", headers={"Referer": "https://ru.yummyani.me/", "User-Agent": "MyAgent/1.0"}).json()
hlsUrl = r_video['sources']['hlsUrl']

# Request with same UA
r1 = requests.get(hlsUrl, headers={"User-Agent": "MyAgent/1.0"})
print("Same UA:", r1.status_code)

# Request with different UA
r2 = requests.get(hlsUrl, headers={"User-Agent": "DifferentAgent/2.0"})
print("Different UA:", r2.status_code)
