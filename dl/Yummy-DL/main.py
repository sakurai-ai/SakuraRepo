import os
import questionary
from rich.console import Console

from scraper import YummyParser
from downloader import download_file
from shikimori import load_shikimori_list

console = Console()
parser = YummyParser()
DOWNLOAD_DIR = "Downloads"

def ensure_download_dir():
    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)

def process_anime_selection(anime_url, title, anime_id):
    console.print(f"[bold green]Выбрано аниме:[/bold green] {title}")
    
    details = parser.get_anime_details(anime_id)
    if not details:
        console.print("[bold red]Не удалось получить детали аниме (возможно, нет доступных серий).[/bold red]")
        return

    if not details.get('players'):
        console.print("[bold red]Нет доступных плееров.[/bold red]")
        return
        
    player = questionary.select(
        "Выберите плеер:",
        choices=details['players']
    ).ask()
    
    if not player: return
    
    translations = list(details['players_map'][player].keys())
    
    translation = questionary.select(
        "Выберите озвучку:",
        choices=translations
    ).ask()
    
    if not translation: return

    quality = questionary.select(
        "Выберите качество (пока качаем iframe):",
        choices=details['qualities']
    ).ask()
    
    if not quality: return

    episodes_choice = questionary.select(
        "Что будем скачивать?",
        choices=[
            "Все серии",
            "Выбрать конкретные серии (диапазон)",
            "Назад"
        ]
    ).ask()
    
    if not episodes_choice or episodes_choice == "Назад": return

    episodes_to_download = []
    total_episodes = details.get('episodes', 12)
    
    if episodes_choice == "Все серии":
        episodes_to_download = list(range(1, total_episodes + 1))
    else:
        ans = questionary.text(f"Введите серии (например 1-5 или 1,2,3). Макс. серия: {total_episodes}").ask()
        if not ans: return
        # Простой парсинг (1-5 или 1, 2, 3)
        if '-' in ans:
            start, end = map(int, ans.split('-'))
            episodes_to_download = list(range(start, end + 1))
        else:
            episodes_to_download = [int(x.strip()) for x in ans.split(',')]

    ensure_download_dir()
    
    players_map = details.get('players_map')
    links = parser.get_download_links(players_map, player, translation, episodes_to_download)
    
    title_folder = title.replace('/', '_').strip()
    target_dir = os.path.join(DOWNLOAD_DIR, title_folder)
    os.makedirs(target_dir, exist_ok=True)
    
    for i, link in enumerate(links):
        ep = episodes_to_download[i]
        filename = f"{title}_Ep{ep}.mp4".replace(' ', '_').replace('/', '_')
        filepath = os.path.join(target_dir, filename)
        
        console.print(f"\n[cyan]Запуск скачивания серии {ep}...[/cyan]")
        download_file(link, filepath)
    
    console.print("[bold green]Все выбранные серии скачаны (или попытка завершена)![/bold green]")

def search_menu():
    query = questionary.text("Введите название аниме:").ask()
    if not query: return
    
    console.print("[cyan]Поиск...[/cyan]")
    results = parser.search_anime(query)
    
    if not results:
        console.print("[bold red]Ничего не найдено![/bold red]")
        return
        
    choices = [r['title'] for r in results] + ["Отмена"]
    choice = questionary.select("Результаты поиска:", choices=choices).ask()
    
    if choice and choice != "Отмена":
        selected = next(r for r in results if r['title'] == choice)
        process_anime_selection(selected['url'], selected['title'], selected['anime_id'])

def shikimori_menu():
    filepath = questionary.text("Введите путь к JSON файлу Шикимори:", default="shikimori_list.json").ask()
    if not filepath: return
    
    anime_list = load_shikimori_list(filepath)
    if not anime_list:
        console.print("[bold red]Список пуст или файл не найден.[/bold red]")
        return
        
    choice = questionary.select(
        "Ваш список:",
        choices=anime_list + ["Назад"]
    ).ask()
    
    if choice and choice != "Назад":
        # Выполняем поиск по выбранному тайтлу
        console.print(f"[cyan]Поиск '{choice}' на YummyAnime...[/cyan]")
        results = parser.search_anime(choice)
        if results:
            process_anime_selection(results[0]['url'], results[0]['title'], results[0]['anime_id'])
        else:
            console.print("[bold red]Не найдено на YummyAnime.[/bold red]")

from config import load_config, save_config

def settings_menu():
    config = load_config()
    while True:
        visible_status = "Вкл" if config.get("playwright_visible") else "Выкл"
        proxy_status = config.get("proxy") if config.get("proxy") else "Нет"
        
        action = questionary.select(
            "Настройки:",
            choices=[
                f"Показ браузера (Playwright): {visible_status}",
                f"Прокси: {proxy_status}",
                "Назад"
            ]
        ).ask()
        
        if not action or action == "Назад":
            break
            
        if "Показ браузера" in action:
            config["playwright_visible"] = not config.get("playwright_visible", False)
            save_config(config)
            console.print("[green]Настройка сохранена![/green]")
        elif "Прокси" in action:
            new_proxy = questionary.text("Введите URL прокси (например, http://user:pass@ip:port) или оставьте пустым для отключения:").ask()
            config["proxy"] = new_proxy.strip() if new_proxy else ""
            save_config(config)
            console.print("[green]Настройка прокси сохранена![/green]")

def main():
    console.print(r"""
[#fcd1d7]

⣿⣿⣿⣿⣿⢿⣿⣿⡿⣿⣿⣿⣿⢿⣿⣿⢿⣿⡿⣿⣿⡿⣿⣿⡿⣿⣿⠻⣣⣿⣷⣙⣫⢻⣿⠿⡿⡟⣷⢹⣿⣿⢿⣿⣿⣿⢿⣿⣿⣿⢿⣿⣿⣄⠀⢀⠐⠐⠢⢑⡀⠀⢀⠀⠀⡀⠀⡀⠀⠀
⣿⣿⣾⣷⣿⣿⢿⣷⣿⣿⣷⣿⣾⣿⣿⣽⣿⣟⣿⣿⣷⣿⣿⣷⣿⣿⣻⢼⣿⣾⢿⣻⠿⡻⠷⠿⠯⠿⠿⢮⣵⣿⣿⣟⣷⣿⣿⢿⠾⢛⠫⡉⠌⠊⠄⠄⢀⠠⠀⡀⠈⠄⠀⡀⠂⠀⠄⠀⠄⠁
⣿⡿⣷⣿⢿⣾⡿⡿⠾⡻⣞⣟⣽⡻⣺⢻⣹⣛⣛⡚⡛⢚⠳⠻⠳⠿⣟⢟⣻⣸⡵⡾⣽⢟⢿⡽⣯⢷⣳⢶⢦⢭⣍⡫⡙⠩⠨⡑⠌⠢⠑⠈⠈⠈⡀⠄⠀⡀⢀⠀⠄⠐⠀⠀⠄⠀⠂⠐⡠⢀
⣴⣿⣿⣻⣿⡏⡭⠊⠉⠉⠈⠉⠉⠙⠛⠉⠁⡀⢀⠀⡀⠠⠀⡀⢁⡤⣖⡿⣺⢞⣱⢯⢯⡟⣺⡝⡷⣝⣞⣟⣯⢷⡱⡿⣽⣲⣅⢌⠀⠐⠀⡈⠀⠁⠀⢀⠠⠀⠀⠄⠀⠂⠈⢀⠀⠂⠐⠀⠐⠡
⣿⣿⣽⣿⡽⢸⠁⠂⡀⣌⡴⠜⡴⠲⣲⢼⢤⢢⣤⣤⣤⡤⡀⣦⣻⢽⡺⡝⡥⡞⡾⡽⡯⡃⣿⠨⡻⡕⣳⣽⣺⣫⣗⠍⢷⣻⣺⣪⡑⢪⣀⠀⡀⠁⡈⠀⠀⢀⠂⠀⠐⠀⠐⠀⠀⠂⠐⠀⠂⠀
⢁⡞⣿⣽⡏⠎⠀⠐⣜⣗⠇⣯⢮⢗⣯⡻⡜⣾⣿⡿⡟⢡⣞⣗⡯⡏⡞⣸⡞⣽⡯⣿⠣⢅⡿⡐⢭⡫⢺⣺⣗⣷⢯⣇⢊⢷⣳⣽⣺⢄⠘⢧⣄⠓⠖⠶⠧⢦⢤⣌⣀⠀⠂⠈⡀⠐⠀⠁⡀⠂
⣧⣾⣿⣻⡇⢁⠐⠀⣗⡯⣗⢕⡯⡯⣞⣷⢹⣿⢿⠝⡰⣽⡾⣽⡺⠨⣼⡳⣽⢽⢽⠣⠩⢀⡗⡌⠜⡕⡱⡿⡸⣏⢟⣽⠔⡐⣻⣜⢾⢯⣦⠐⢹⣵⣄⠀⢀⠀⠤⠈⠙⠛⠓⠓⠲⠲⠬⠤⢤⠀
⣿⣿⣽⣿⣯⠀⢀⠀⢸⣺⣣⡑⢮⢯⢿⣵⣽⣿⠏⢌⣾⣻⣾⡳⠡⣱⢟⣸⢺⢍⢍⠊⡀⠐⡇⡇⠍⢎⢜⡟⢔⢣⡃⢏⢗⢨⠂⣿⢽⡹⡻⣧⠐⡹⣞⢦⡀⡀⡄⣀⣁⢄⣐⣈⢠⣠⣠⡐⠀⠀
⣿⣿⣽⣷⣿⡅⠀⠠⠀⢺⣞⣌⡫⡯⣷⣿⣟⡗⢅⣟⣟⡯⡟⢄⢣⢏⠢⢅⠣⡢⠑⢀⡴⠀⡇⡇⠅⡣⠢⡯⡊⣺⠨⡢⠱⡐⢕⢘⡮⡞⡎⡪⡣⡈⣳⡑⢵⠘⡽⡕⡝⢽⣺⡪⡕⢵⡳⣽⠀⠀
⣟⠻⣽⣿⣽⣿⠀⠐⠀⡈⢾⡺⣕⢹⣾⣯⡿⢨⣞⢱⢳⢩⠸⠐⡜⡜⢌⠪⡊⢂⡔⡯⣛⡆⡃⡇⡃⠘⡂⡇⡜⡰⡑⡅⡣⡘⢌⢢⢙⡧⡓⡕⢌⢆⢂⠧⡑⡕⡸⡱⣹⣕⢷⣝⣷⣭⢺⡳⠀⠀
⣿⠽⣶⣿⣯⣿⣷⠀⠁⠀⠐⢟⢎⣟⣿⣯⢇⠧⡒⠅⠃⢕⠂⠕⠑⢜⢌⠪⣰⣪⢗⡯⡷⣽⢸⠰⡁⡀⡃⡎⡢⡑⡕⢜⢨⠢⡑⡕⢔⢱⣑⢪⠢⡣⢢⠣⡱⡨⡂⣺⡺⣪⣟⣾⡽⣔⡯⡂⠐⠀
⣿⢣⣿⣷⣿⣯⠿⢢⠐⠀⠐⠈⠶⡍⠿⡽⡠⠣⠑⠈⢠⡄⠐⢀⡅⠐⡡⣺⢵⣳⡳⣱⣿⣳⡘⢜⢄⢷⡠⡣⢊⢆⢕⢑⢜⠰⢨⢪⠸⡸⡢⡣⡱⡸⡰⢑⢕⢨⠪⡐⣿⡵⣿⠇⢇⢷⠍⠀⡰⠁
⣯⣿⢟⢓⢅⡦⡯⡪⢧⡀⠈⢀⠈⢗⡧⡄⠂⡠⡨⡡⠆⠀⠀⠄⠰⢁⢟⡮⡻⡜⢟⣛⣭⣭⡬⠪⡢⡯⡖⠌⢜⢢⢑⢅⡣⣙⠀⢪⠪⡪⡢⢕⢜⢘⢌⠔⢕⢅⢣⢃⣿⡿⣏⣾⣾⡕⠁⢠⠁⠀
⢟⣥⢚⣜⢮⣫⡫⢆⣿⢱⠀⠀⠄⠈⢺⠀⠈⠈⠀⡈⠫⠄⠂⠠⣡⣺⣪⢞⣽⣿⣿⢿⣽⣿⡇⡕⢼⣝⡎⠅⡣⡱⡱⢱⢘⠤⢹⣢⠣⡗⢅⢣⢑⢅⢇⢊⢎⢊⢆⠣⡳⢷⡡⣿⡗⠁⢠⠃⠀⢀
⢏⡆⡺⢠⠓⢁⠠⣾⢇⡯⡸⣄⠂⢀⠀⠂⡬⢢⠣⡣⡱⠱⢈⡖⣗⢵⣳⢯⣿⣯⣚⣋⠯⣷⡗⢜⢼⣿⢌⢼⠔⢕⡱⣑⢜⠔⣰⣑⢇⢏⢎⢔⢕⠰⡱⢈⢖⢱⢑⢕⢸⣿⣾⡛⠀⡰⢡⠀⠐⠀
⣿⢸⠁⡈⢀⢢⢿⡃⣗⡇⡎⡪⠣⡀⡀⠄⡪⡱⡑⡕⡌⠇⡮⠯⡳⠯⠿⠿⡿⣾⣿⣟⣷⣸⣯⠢⣻⣽⠅⣿⣕⠕⡆⠢⡣⠕⣕⡯⡿⣔⢡⢊⠲⢘⢜⠰⣑⢕⡱⣑⢸⡿⠃⢀⠎⡠⣥⠐⠂⠀
⡃⡇⠄⠠⢰⡿⣣⠣⣿⢇⢖⢈⢆⢑⠀⠀⡪⡪⣊⢆⠇⡇⠏⠉⢀⠠⡠⣀⢀⠀⠨⠹⣹⣿⣽⡠⣿⢿⣸⣿⣺⢧⡣⢁⢕⢅⣗⣻⢿⣺⣢⢃⠎⡬⡊⡸⡰⢱⢸⢰⠘⠀⠠⠁⢠⣞⢵⡣⠀⠁
⢇⠅⠐⠠⣿⡇⠃⢼⡿⠰⡱⠡⡐⢅⠠⠀⡜⢬⠲⡡⠱⡂⢠⣾⣧⠨⡪⡦⡧⡵⣔⡀⣜⣽⣿⡦⣿⢧⣿⡯⣮⣿⣧⢹⡜⢨⣾⣿⣻⣮⣞⡦⡑⡜⡌⡪⡊⡎⡎⡖⢀⠌⠀⡀⣚⢮⡳⣽⡀⠀
⢕⠁⢤⡝⣿⠂⣬⡿⠁⢍⢪⣨⣤⠐⡀⠀⡇⣇⢏⢎⢇⢶⣾⢽⢶⢗⢇⣍⣌⣕⡂⣼⣿⡾⣿⣽⣿⣽⣷⡿⣾⣻⣿⠽⢂⠓⠚⠚⠙⠝⢷⡏⢜⢜⠰⡱⡨⡕⡕⠊⣿⡆⠁⣸⢽⢵⢮⣗⢀⠪
⢇⣵⡿⠓⠘⢿⠛⡈⢌⢢⢣⣫⢻⣷⡀⠀⣓⢜⡎⡎⣎⢸⣾⢿⡽⣯⢿⢾⡯⡷⣿⢯⢷⣻⡯⣷⣻⢞⡷⡿⣟⣿⡇⢲⣴⣨⣒⢌⢢⣆⡀⠁⡸⡰⢸⢨⢪⢊⠎⢦⣸⣿⠀⢧⣫⡫⡳⣫⣗⡆
⣺⠟⠁⡈⠄⠂⠁⠀⠂⣗⣿⣜⢧⢻⣿⡀⢎⢮⢣⢪⠢⢪⣻⢯⣟⡽⡽⣕⢯⣻⢺⣝⡯⡷⣽⢵⢯⢯⢯⢯⡫⣞⢿⣲⣬⣕⠹⠋⣾⣻⣗⠀⢐⠅⡎⡞⡜⢜⠌⡢⢻⡗⡀⠄⠀⠉⠚⠪⠞⣾
⢏⢼⠀⠠⠐⠀⠌⠀⡀⣷⣿⢪⢵⢇⣿⣇⢇⢳⢕⠕⡍⢔⣷⣳⡳⣽⣺⣝⡯⣾⢝⣮⡻⣮⣳⢻⢾⣝⢯⢷⢘⢮⢯⣗⢯⣞⣟⣮⢿⢾⣲⣾⠨⢂⡼⢌⢎⠕⢨⠪⡎⡥⣄⣀⠠⠀⣢⣦⣆⠄
⢪⡎⡧⠐⢀⠁⠄⠁⢤⢺⡿⣜⢝⡇⣾⣗⢕⢕⢇⢕⢕⢸⣳⣯⣿⣺⣺⣺⣽⣞⣟⡾⣽⣺⣞⣯⣟⡾⣯⢯⣞⣽⣳⢽⣕⣟⣞⢾⡻⣯⣷⣟⢈⢖⢜⢢⠱⠁⡐⢡⢻⡜⢽⡺⣕⡦⣞⣿⣾⡿
⡣⣻⢮⣧⢀⠐⠀⠂⣹⣦⡛⢿⣾⣬⣜⣷⢊⢮⡣⡊⡆⢜⣾⣿⡾⣿⣽⡿⣷⡿⣯⡿⣯⣿⢾⣻⣞⣯⣿⣽⣞⣷⣽⣻⢞⣮⡷⣽⣺⣳⣻⢎⢞⢰⢡⢣⠑⠁⡀⣚⢜⣷⢹⣚⡧⣻⣻⠝⣃⣵
⢪⢎⣝⣞⣧⡐⠈⢀⠸⣿⣷⣌⠙⢿⣯⣿⢐⢕⢎⠪⢌⠼⣽⣾⡿⣻⣽⣿⡿⣿⣟⡿⡿⡻⠋⢙⡶⡖⠮⢝⢷⡿⣾⣻⣿⣵⢿⣳⣟⡾⡱⡑⢅⢇⢕⠬⠀⠂⠀⢘⢧⡹⠇⡞⡞⣑⣥⣾⣿⣿
⢪⣳⠸⣸⠺⢽⢦⢀⠈⣿⣯⣿⣧⣂⢙⢙⢐⢕⡕⡕⢕⢸⡺⣿⣻⣵⡿⣷⣿⣿⠋⡀⠠⠀⠈⣴⠁⠅⢀⠀⠀⢿⣿⣯⣷⣿⢿⡯⢏⠆⠃⢜⠌⡆⢇⠁⠄⠁⡌⠀⠳⠝⢁⣵⣺⣽⣿⣯⣷⣿
⢘⢬⢳⡅⢏⠪⡍⡧⡢⡸⣿⣷⣿⡿⣦⠐⠨⡂⣗⢅⢣⢸⢜⣿⡿⣟⣿⣿⣻⡞⠀⡠⡢⡒⣶⡯⢤⢆⢄⠀⠂⢈⣷⡿⣳⣷⣿⢸⣴⠁⡰⡱⡑⡍⢂⠐⣀⣥⣵⣶⡾⣵⣿⣟⣿⣻⣷⣿⢯⣻
⡎⡪⡱⡹⡨⢕⠈⠪⡪⡪⡰⡹⣾⣿⡿⣷⡀⢇⢺⡐⡅⢸⣝⢾⣻⣻⣻⣯⣿⡇⠨⣪⢮⣳⣕⢿⣸⣸⡜⣕⠄⢢⣿⡯⣿⢿⣾⣻⠃⢠⢪⢂⠃⣥⣶⢿⣻⣷⣿⣾⣽⡿⣷⣿⣿⣻⣿⢮⣿⡿
⣟⠈⡎⡎⡞⠬⡪⢄⠠⠃⢇⠧⡪⠺⣿⡿⣇⠥⢱⢊⢎⠘⣼⣷⣿⢿⣷⣫⣿⢷⡈⣞⣷⢷⢽⣕⡟⣵⣝⡮⡇⣾⣿⣻⣷⡿⡾⠃⢀⢅⠆⣴⣟⣿⣾⣿⡿⣿⡞⣿⣾⣿⡿⣿⣾⣿⣳⣿⣻⣿
⢇⠠⠘⡜⡬⢣⢕⡱⡠⠠⠐⣕⠍⡮⢌⢿⣷⢑⠸⡸⡘⢼⣿⣯⣿⣿⣻⣗⣿⣿⢽⡔⣯⣿⣳⢗⡯⣗⣯⡟⣵⣿⣟⣿⠷⢋⢢⢜⢕⢡⣾⣿⢿⣻⣯⣷⣿⢟⣼⣿⣯⣷⣿⣿⣞⣽⣾⣿⣻⣽
⠀⡎⠄⡘⡜⡜⡢⡓⣌⠣⡀⢿⣿⣦⡱⠨⣿⡨⡢⡱⡅⡃⠛⢟⢾⢟⠟⠾⣿⣾⢽⢵⡹⡷⣿⢽⡽⣟⢗⣽⢿⡾⠛⠁⢂⢎⠮⠪⣢⣿⡿⣿⣿⡿⣿⣻⣝⣮⣿⣷⣿⣿⣽⣷⢷⣻⣽⣾⣿⣿
⣼⠇⡁⢀⠈⠮⡘⢜⠴⡑⣌⢊⢿⣾⣿⠌⢼⡆⣱⠘⡜⡔⠀⢸⢽⢽⠫⣀⣬⣝⠪⣿⣿⣾⡬⣿⣟⣼⡿⠛⠉⢀⠀⢂⢵⢙⠘⢰⣿⣟⣿⣿⣷⣿⡿⡯⣞⣾⣯⣷⣿⣷⣿⢿⣽⣾⣿⢿⣽⣾
⣾⠁⠄⢂⠠⠘⢜⢌⠪⡪⡐⢅⢌⢻⣾⡇⠠⣗⢸⣇⢣⢪⠠⠐⠂⢲⣿⠡⣀⡀⢀⠀⢈⡑⢫⡏⣊⡁⠀⠉⠉⠉⠉⠨⠐⢀⢰⣿⢿⣻⣿⣾⣷⢿⢽⢽⣳⣿⣽⣿⢷⣿⣻⣿⣟⣿⢾⣻⢽⡺
⡗⠐⢈⠀⢀⠠⠘⡔⡄⠱⡑⢅⠢⠊⡿⠐⡀⣿⡐⣿⠀⣓⠄⠐⠀⢸⣿⠀⣧⠃⠀⠠⠘⠧⡟⣽⣿⠇⠀⡂⠄⠂⡁⡡⠈⡀⣾⣻⣿⣿⢿⡾⡯⣯⣻⢽⣺⣷⣿⢿⡿⣿⣻⡷⡯⣗⣟⠞⣉⣴
⠀⠌⠠⠐⠀⠀⡂⢪⠢⠀⢍⢂⠅⡃⢁⠡⢠⣿⣧⢚⠀⠈⢆⠠⠈⢸⣿⠀⠀⡀⡀⡂⡀⠀⡁⢟⣩⠕⣭⠂⡂⠡⠀⡂⢰⢧⣿⣿⣻⣾⣻⢽⢽⣺⢞⣽⣺⣿⣽⣿⣿⡻⣽⣺⣻⣺⢊⡼⢟⡽
⢈⠠⠁⢀⠜⢀⠂⢰⢑⠀⠕⡐⠌⡀⢂⡴⣿⣿⣽⡆⠀⡈⠀⠄⣀⢸⣿⡺⠟⠛⠛⠛⠙⣣⠶⢋⣥⡿⢑⠐⠨⠀⡂⢂⣿⣟⣿⣾⣿⢽⣺⣫⢟⣞⣟⣞⢾⢯⣟⣗⡯⣞⣗⣗⣗⠇⣼⣳⢯⣟
[white]  __  __                                      ____  __ [/white]
[white]\ \/ /_  ______ ___  ____ ___  __  __      / __ \/ / [/white]
[white] \  / / / / __ `__ \/ __ `__ \/ / / /_____/ / / / /  [/white]
[white] / / /_/ / / / / / / / / / / / /_/ /_____/ /_/ / /___[/white]
[white]/_/\__,_/_/ /_/ /_/_/ /_/ /_/\__, /     /_____/_____/[/white]
[white]                            /____/                   [/white]
             [#c3829e]by sakuraidev v1.0.0[/#c3829e]

[/#fcd1d7]
""")
    
    while True:
        action = questionary.select(
            "Главное меню:",
            choices=[
                "Поиск аниме по названию",
                "Поиск по жанру (в разработке)",
                "Топ аниме (в разработке)",
                "Последние обновления (в разработке)",
                "Ваш список (Shikimori JSON)",
                "Настройки",
                "Выход"
            ]
        ).ask()
        
        if action == "Поиск аниме по названию":
            search_menu()
        elif action == "Ваш список (Shikimori JSON)":
            shikimori_menu()
        elif action == "Настройки":
            settings_menu()
        elif action == "Выход" or not action:
            console.print("До свидания!")
            break
        else:
            console.print("[yellow]Этот раздел еще в разработке. Мы создали базовый каркас, который можно будет расширять![/yellow]")

if __name__ == "__main__":
    main()
