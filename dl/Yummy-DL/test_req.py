import requests
url = "https://vd528.okcdn.ru/video.m3u8?cmd=videoPlayerCdn&expires=1789574088329&srcIp=159.195.16.107&pr=90&srcAg=UNKNOWN&ch=-647529056&ms=185.226.55.38&type=2&sig=7Tbm6lZrv20&ct=8&urls=178.237.23.53&clientType=46&zs=43&id=9163351526128"
r = requests.get(url, headers={'User-Agent': 'curl/7.81.0'})
print(r.request.url)
