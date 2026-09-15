import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote

from config import load_config

BASE_URL = "https://old.yummyani.me"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
}

class YummyParser:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        
        config = load_config()
        proxy_url = config.get("proxy")
        if proxy_url:
            self.session.proxies.update({"http": proxy_url, "https": proxy_url})

    def search_anime(self, query):
        """Поиск аниме по названию через скрытый API сайта"""
        url = f"{BASE_URL}/api/search?q={quote(query)}&limit=20&offset=0"
        try:
            self.session.headers.update({"X-Requested-With": "XMLHttpRequest", "Accept": "application/json"})
            response = self.session.get(url)
            response.raise_for_status()
            
            data = response.json()
            results = []
            
            anime_list = data.get('response', [])
            if isinstance(anime_list, list):
                for item in anime_list:
                    title = item.get('title')
                    anime_url = item.get('anime_url')
                    anime_id = item.get('anime_id')
                    
                    if title and anime_url and anime_id:
                        link = urljoin(BASE_URL, f"/catalog/item/{anime_url}")
                        results.append({'title': title, 'url': link, 'anime_id': anime_id})
            return results
        except Exception as e:
            print(f"Ошибка при поиске: {e}")
            return []

    def get_anime_details(self, anime_id):
        """Получает информацию о доступных озвучках, плеерах и сериях"""
        url = f"{BASE_URL}/api/anime/{anime_id}/videos"
        try:
            self.session.headers.update({"X-Requested-With": "XMLHttpRequest", "Accept": "application/json"})
            response = self.session.get(url)
            response.raise_for_status()
            data = response.json()
            videos = data.get('response', [])
            
            players_map = {}
            max_episode = 0
            
            for v in videos:
                dubbing = v.get('data', {}).get('dubbing', 'Неизвестная озвучка')
                player = v.get('data', {}).get('player', 'Плеер')
                
                # Добавляем информацию о максимальном качестве плеера
                quality_info = ""
                player_lower = player.lower()
                if 'cvh' in player_lower:
                    quality_info = " [До 1080p]"
                elif 'vk' in player_lower or 'вк' in player_lower:
                    quality_info = " [До 1080p]"
                elif 'aksor' in player_lower:
                    quality_info = " [До 1080p]"
                elif 'sibnet' in player_lower or 'сибнет' in player_lower:
                    quality_info = " [До 720p]"
                elif 'kodik' in player_lower:
                    quality_info = " [До 720p]"
                elif 'alloha' in player_lower:
                    quality_info = " [До 1080p]"
                elif 'ok' in player_lower or 'одноклассники' in player_lower:
                    quality_info = " [До 1080p]"
                else:
                    quality_info = " [Качество неизвестно]"
                
                player_name = f"{player}{quality_info}"
                
                ep_num_str = v.get('number', '')
                try:
                    ep_num = int(ep_num_str) if ep_num_str else 1
                except:
                    ep_num = 1
                    
                if ep_num > max_episode:
                    max_episode = ep_num
                    
                if player_name not in players_map:
                    players_map[player_name] = {}
                if dubbing not in players_map[player_name]:
                    players_map[player_name][dubbing] = {}
                    
                players_map[player_name][dubbing][ep_num] = v.get('iframe_url')

            if not players_map:
                return None

            return {
                'players_map': players_map,
                'players': list(players_map.keys()),
                'qualities': ['1080p (В разработке - выкачивание iframe)'],
                'episodes': max_episode
            }
        except Exception as e:
            print(f"Ошибка при получении деталей: {e}")
            return None

    def get_download_links(self, players_map, player, translation, episodes=[]):
        """Получает iframe-ссылки на скачивание серий"""
        links = []
        if player not in players_map or translation not in players_map[player]:
            return links
            
        for ep in episodes:
            iframe_url = players_map[player][translation].get(ep)
            if iframe_url:
                if iframe_url.startswith('//'):
                    iframe_url = 'https:' + iframe_url
                links.append(iframe_url)
            else:
                print(f"Ссылка для серии {ep} не найдена в озвучке {translation} (плеер {player}).")
        return links
