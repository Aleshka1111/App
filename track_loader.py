import os
import json
from ffpyplayer.player import MediaPlayer
from ffpyplayer.tools import set_loglevel

set_loglevel("quiet")

def get_audio_info(filepath):
    player = MediaPlayer(filepath)
    import time
    time.sleep(0.1)  

    metadata = player.get_metadata()
    duration = metadata.get('duration', 0)
    length = round(float(duration), 2) if duration else 0.0
    author = metadata.get('artist', None)
    album = metadata.get('album', None)

    player.close_player()

    return {
        "len_song": length,
        "author": author,
        "album": album,
        "filepath": filepath
    }

def scan_music_folder(music_dir="music"):
    supported_ext = {".mp3", ".wav", ".flac", ".m4a", ".ogg", ".aac", ".wma"}
    tracks = {}

    for filename in os.listdir(music_dir):
        ext = os.path.splitext(filename)[1].lower()
        if ext not in supported_ext:
            continue

        filepath = os.path.join(music_dir, filename)
        if not os.path.isfile(filepath):
            continue

        song_name = os.path.splitext(filename)[0]
        info = get_audio_info(filepath)
        tracks[song_name] = info

    return tracks


def update_tracks_json(json_file="tracks.json", music_dir="music"):
    current_tracks = scan_music_folder(music_dir)
    old_tracks = {}
    if os.path.exists(json_file):
        with open(json_file, "r", encoding="utf-8") as f:
            old_tracks = json.load(f)

    updated_tracks = {}
    for name, info in old_tracks.items():
        filepath = info.get("filepath")
        if not filepath:
            for ext in [".mp3", ".wav", ".flac", ".m4a", ".ogg", ".aac", ".wma"]:
                alt_path = os.path.join(music_dir, f"{name}{ext}")
                if os.path.exists(alt_path):
                    filepath = alt_path
                    break

        if filepath and os.path.exists(filepath):
            updated_tracks[name] = current_tracks.get(name, info)

    for name, info in current_tracks.items():
        if name not in updated_tracks:
            updated_tracks[name] = info
            print(f"Добавлен: {name}")

    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(updated_tracks, f, ensure_ascii=False, indent=4)
    print(f"Обновлено: {len(updated_tracks)} треков")
    return updated_tracks

if __name__ == "__main__":
    update_tracks_json()
