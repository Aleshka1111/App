import os
import json


def load_tracks(filepath="tracks.json"):
    if not os.path.exists(filepath):
        print(f"Файл не найден: {filepath}")
        return {}

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        print(f"Успешно загружено {len(data)} треков из {filepath}")
        return data
    except Exception as e:
        print(f"Ошибка при чтении {filepath}: {e}")
        return {}
