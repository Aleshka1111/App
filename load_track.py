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


def load_liked():
    if not os.path.exists("my_playlist.json"):
        return []
    try:
        with open("my_playlist.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except:
        return []


def save_liked(liked_list):
    try:
        with open("my_playlist.json", "w", encoding="utf-8") as f:
            json.dump(liked_list, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Ошибка при сохранении my_playlist.json: {e}")


def toggle_like(track_name):
    liked = load_liked()
    if track_name in liked:
        liked.remove(track_name)
        save_liked(liked)
        return False
    else:
        liked.append(track_name)
        save_liked(liked)
        return True
