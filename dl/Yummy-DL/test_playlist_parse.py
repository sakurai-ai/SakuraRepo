import requests

stream_url = "https://plapi.cdnvideohub.com/api/v1/player/sv/playlist?pub=745&aggr=mali&id=37982&ep=1"

headers = {"Referer": "https://ru.yummyani.me/"}

# Если поймали плейлист, достаем из него vkId и формируем ссылку на видео
if '/playlist' in stream_url:
    r_playlist = requests.get(stream_url, headers=headers).json()
    items = r_playlist.get('items', [])
    if items and 'vkId' in items[0]:
        vk_id = items[0]['vkId']
        stream_url = f"https://plapi.cdnvideohub.com/api/v1/player/sv/video/{vk_id}"

# Если у нас ссылка на видео, достаем hlsUrl
if '/video/' in stream_url:
    r_video = requests.get(stream_url, headers=headers).json()
    if 'sources' in r_video and 'hlsUrl' in r_video['sources']:
        stream_url = r_video['sources']['hlsUrl']

print("FINAL URL:", stream_url)
