import requests
import socket
# start dummy server to see what requests sends
import threading
def server():
    s = socket.socket()
    s.bind(('127.0.0.1', 9999))
    s.listen(1)
    c, a = s.accept()
    print("REQUESTS SENT:\n", c.recv(1024).decode())
    c.close()
    s.close()
threading.Thread(target=server).start()

url = "http://127.0.0.1:9999/video.m3u8?cmd=videoPlayerCdn&expires=1789574088329&srcIp=159.195.16.107&pr=90&srcAg=UNKNOWN&ch=-647529056&ms=185.226.55.38&type=2&sig=7Tbm6lZrv20&ct=8&urls=178.237.23.53&clientType=46&zs=43&id=9163351526128"
try: requests.get(url)
except: pass

def server2():
    s = socket.socket()
    s.bind(('127.0.0.1', 9998))
    s.listen(1)
    c, a = s.accept()
    print("CURL SENT:\n", c.recv(1024).decode())
    c.close()
    s.close()
threading.Thread(target=server2).start()
import subprocess
subprocess.run(['curl', '-s', 'http://127.0.0.1:9998/video.m3u8?cmd=videoPlayerCdn&expires=1789574088329&srcIp=159.195.16.107&pr=90&srcAg=UNKNOWN&ch=-647529056&ms=185.226.55.38&type=2&sig=7Tbm6lZrv20&ct=8&urls=178.237.23.53&clientType=46&zs=43&id=9163351526128'])
