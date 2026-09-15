import requests
import subprocess
import threading
import socket

# create proxy server
def proxy_server():
    s = socket.socket()
    s.bind(('127.0.0.1', 8888))
    s.listen(1)
    c, a = s.accept()
    req = c.recv(4096).decode()
    print("YT-DLP SENT:\n" + req)
    c.send(b"HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n")
    c.close()
    s.close()
threading.Thread(target=proxy_server).start()

r_playlist = requests.get("https://plapi.cdnvideohub.com/api/v1/player/sv/playlist?pub=745&aggr=mali&id=37982&ep=1", headers={"Referer": "https://ru.yummyani.me/"}).json()
vk_id = r_playlist['items'][0]['vkId']
r_video = requests.get(f"https://plapi.cdnvideohub.com/api/v1/player/sv/video/{vk_id}", headers={"Referer": "https://ru.yummyani.me/"}).json()
hlsUrl = r_video['sources']['hlsUrl']

# replace https:// with http://127.0.0.1:8888/
fake_url = hlsUrl.replace("https://vd528.okcdn.ru", "http://127.0.0.1:8888")
subprocess.run(['yt-dlp', fake_url])
