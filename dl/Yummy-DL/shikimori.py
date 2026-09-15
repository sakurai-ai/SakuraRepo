import json
import os

def load_shikimori_list(filepath):
    """
    Загружает список аниме из JSON файла Шикимори.
    Ожидается структура, экспортированная из Shikimori или подобных сервисов.
    """
    if not os.path.exists(filepath):
        print(f"Файл {filepath} не найден.")
        return []

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Обычно API шикимори возвращает список словарей. 
        # Извлекаем названия для поиска.
        anime_list = []
        for item in data:
            # Адаптируем под различные структуры json (rates или чистый список)
            if 'anime' in item and 'name' in item['anime']:
                anime_list.append(item['anime']['name'])
            elif 'target_title' in item:
                anime_list.append(item['target_title'])
            elif 'name' in item:
                anime_list.append(item['name'])
        
        return anime_list
    except Exception as e:
        print(f"Ошибка при чтении файла Шикимори: {e}")
        return []
