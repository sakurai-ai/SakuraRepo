from scraper import YummyParser
from extractor import get_direct_stream_url
import subprocess
from config import load_config

# Set playwright to headless for testing
config = load_config()
config["playwright_visible"] = False
from config import save_config
save_config(config)

parser = YummyParser()
# Anime ID for Domekano is 37982
details = parser.get_anime_details("37982")

if not details:
    print("Failed to get details")
    exit(1)

players_map = details['players_map']

for player, dubbings in players_map.items():
    print(f"\n{'='*50}\nTesting Player: {player}")
    # Just test the first dubbing to save time, or we can test all
    for dubbing, episodes in dubbings.items():
        print(f"  Dubbing: {dubbing}")
        # Test episode 1
        iframe_url = episodes.get(1)
        if not iframe_url:
            print("    No ep 1 found")
            continue
            
        if iframe_url.startswith('//'):
            iframe_url = 'https:' + iframe_url
            
        print(f"    Iframe URL: {iframe_url}")
        
        # Test extraction
        try:
            stream_url = get_direct_stream_url(iframe_url)
            if not stream_url:
                stream_url = iframe_url # fallback to let yt-dlp try natively
        except Exception as e:
            print(f"    Extractor Failed: {e}")
            continue
            
        print(f"    Stream URL: {stream_url}")
        
        # Test yt-dlp simulate
        cmd = [
            "yt-dlp",
            stream_url,
            "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
            "--simulate"
        ]
        
        proxy_url = config.get("proxy")
        if proxy_url:
            cmd.extend(["--proxy", proxy_url])
            
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            print("    [SUCCESS] yt-dlp can download this stream!")
        else:
            print("    [FAILED] yt-dlp error:")
            for line in res.stderr.split('\n'):
                if 'ERROR' in line:
                    print(f"      {line.strip()}")
