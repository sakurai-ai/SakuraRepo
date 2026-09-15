import os
import subprocess
from rich.console import Console
from extractor import get_direct_stream_url

console = Console()

def download_file(url, filepath):
    """
    Скачивает видео по ссылке на iframe/плеер с использованием yt-dlp.
    Если плеер зашифрован (Aksor, CVH, Kodik), использует Playwright для обхода.
    """
    console.print(f"[bold yellow]Запуск yt-dlp для ссылки:[/bold yellow] {url}")
    
    # Меняем расширение на .mp4
    base, ext = os.path.splitext(filepath)
    if ext == '.txt':
        filepath = base + '.mp4'
    from config import load_config
    
    def run_ytdlp(target_url):
        cmd = [
            "yt-dlp",
            target_url,
            "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
            "--no-playlist",
            "--progress",
            "-o", filepath,
            "--merge-output-format", "mp4",
            "--no-abort-on-error"
        ]
        
        config = load_config()
        proxy_url = config.get("proxy")
        if proxy_url:
            cmd.extend(["--proxy", proxy_url])
        
        try:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            failed = False
            
            for line in process.stdout:
                out_line = line.strip()
                print(out_line)
                if "ERROR:" in out_line or "Unsupported URL" in out_line:
                    failed = True
            
            process.wait()
            if process.returncode != 0:
                failed = True
            return not failed, failed
        except FileNotFoundError:
            console.print("[bold red]Утилита yt-dlp не найдена! Установите её: pip install yt-dlp[/bold red]")
            return False, True
        except Exception as e:
            console.print(f"[bold red]Ошибка при скачивании:[/bold red] {e}")
            return False, True

    # Пытаемся скачать напрямую (работает для VK, Sibnet)
    success, failed = run_ytdlp(url)
    
    if failed:
        console.print("\n[bold red]Плеер защищен! Подключаем тяжелую артиллерию (Playwright)...[/bold red]")
        
        direct_url = get_direct_stream_url(url)
        if direct_url:
            console.print(f"\n[bold green]Ссылка успешно перехвачена:[/bold green] {direct_url}")
            console.print("[bold yellow]Пробуем скачать чистый поток...[/bold yellow]")
            # Скачиваем уже чистую m3u8/mpd ссылку
            success, _ = run_ytdlp(direct_url)
        else:
            console.print("[bold red]Не удалось перехватить ссылку. Возможно, плеер требует капчу или сменил защиту.[/bold red]")
            return False
            
    if success:
        console.print("[bold green]Скачивание завершено успешно![/bold green]")
        return True
    else:
        console.print("[bold red]Произошла ошибка при скачивании.[/bold red]")
        return False
