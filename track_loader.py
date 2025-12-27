import os
import json
from ffpyplayer.player import MediaPlayer
from ffpyplayer.pic import SWScale
from ffpyplayer.tools import set_loglevel

set_loglevel("quiet")


def get_audio_info(filepath):
    try:
        player = MediaPlayer(filepath)
        import time
        time.sleep(0.1)
        length = player.get_metadata().get('duration', None)
        if length is None:
            player.set_pause(False)
            time.sleep(0.05)
            length = player.get_metadata().get('duration', 0)
            player.set_pause(True)
        length = round(float(length), 2) if length else 0.0

        metadata = player.get_metadata()
        author = metadata.get('artist', None)
        album = metadata.get('album', None)

        player.close_player()

        if length <= 0:
            return None

        return {
            "len_song": length,
            "author": author,
            "album": album
        }
    except Exception as e:
        print(f"Ошибка при чтении {filepath}: {e}")
        try:
            player.close_player()
        except:
            pass
        return None


def scan_music_folder(music_dir="music"):

    if not os.path.exists(music_dir):
        return {}

    supported_ext = (".mp3", ".wav", ".flac", ".m4a", ".ogg", ".wma", ".aac")
    tracks = {}

    for filename in os.listdir(music_dir):
        filepath = os.path.join(music_dir, filename)
        if not os.path.isfile(filepath):
            continue
        if not filename.lower().endswith(supported_ext):
            continue

        song_name = os.path.splitext(filename)[0] 
        info = get_audio_info(filepath)
        if info:
            tracks[song_name] = info
            print(f"{filename}: {info}")
        else:
            print(f"{filename}: не удалось получить длину")
            tracks[song_name] = {
                "len_song": 0.0,
                "author": None,
                "album": None
            }

    return tracks


def save_tracks_json(output_file="tracks.json", music_dir="music"):
    tracks = scan_music_folder(music_dir)
    if tracks:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(tracks, f, ensure_ascii=False, indent=4)
        print(f"Информация о треках сохранена в: {output_file}")
    else:
        print(" Нет данных для сохранения")
    return tracks


