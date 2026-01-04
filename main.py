from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.core.image import Image as CoreImage
from kivy.graphics import Color, Rectangle, Line
from kivy.graphics.texture import Texture
from kivy.graphics.fbo import Fbo
from kivy.clock import Clock
from kivy.metrics import dp
import os
import shutil
import json
from load_track import load_tracks
from track_loader import get_audio_info
from time import time


class MusicApp(App):
    def build(self):
        self.tracks = load_tracks("tracks.json")
        if not self.tracks:
            layout = BoxLayout(orientation='vertical')
            layout.add_widget(Label(text="Нет треков", font_size=24))
            return layout

        self.track_names = list(self.tracks.keys())
        self.current_index = 0
        self.is_playing = False
        self.player = None

        self.progress_fraction = 0.0
        self.is_scrubbing = False
        self.ignore_end_check = False
        self._seek_event = None
        self._resize_event = None
        self._last_seek_time = 0

        main_layout = BoxLayout(orientation='vertical')
        spacer = BoxLayout(size_hint_y=1)
        main_layout.add_widget(spacer)

        self.container = FloatLayout(size_hint_y=None, height=dp(120))
        main_layout.add_widget(self.container)

        self.btn_size = dp(40)
        self.play_size = dp(50)
        self.progress_height = dp(8)
        self.slider_size = dp(16)
        self.y_buttons = 0.1
        self.y_progress = 0.65

        self.play_texture = self.load_image(['icons/play.png'])
        self.pause_texture = self.load_image(['icons/pause.png'])
        self.nav_texture = self.load_image(['icons/nextorback.png'], mirror=False)
        self.add_texture = self.load_image(['icons/add.png'])
        self.slider_texture = self.load_image(['icons/progress_bar_slider.png'])
        self.nav_texture_prev = self.flip_texture(self.nav_texture) if self.nav_texture else None

        self.add_btn = self.create_button(pos_hint={'center_x': 0.2, 'y': self.y_buttons}, size=(self.btn_size, self.btn_size))
        self.prev_btn = self.create_button(pos_hint={'center_x': 0.35, 'y': self.y_buttons}, size=(self.btn_size, self.btn_size))
        self.play_btn = self.create_button(pos_hint={'center_x': 0.5, 'y': self.y_buttons}, size=(self.play_size, self.play_size))
        self.next_btn = self.create_button(pos_hint={'center_x': 0.65, 'y': self.y_buttons}, size=(self.btn_size, self.btn_size))

        self.container.add_widget(self.add_btn)
        self.container.add_widget(self.prev_btn)
        self.container.add_widget(self.play_btn)
        self.container.add_widget(self.next_btn)

        self.add_btn.bind(on_press=self.start_add_music)
        self.prev_btn.bind(on_press=self.previous_track)
        self.next_btn.bind(on_press=self.next_track)
        self.play_btn.bind(on_press=self.on_play_press)

        Clock.schedule_once(self.init_ui, 0)

        self.container.bind(size=self.update_layout, pos=self.update_layout)

        self.container.bind(on_touch_down=self.on_progress_touch, on_touch_move=self.on_progress_touch)

        return main_layout
    
    @property
    def progress_width(self):
        return self.container.width * 0.8

    def create_button(self, pos_hint, size):
        btn = Button(
            background_normal='',
            background_color=(0, 0, 0, 0),
            size_hint=(None, None),
            size=size,
            pos_hint=pos_hint
        )
        return btn
    
    def on_container_resize(self, *args):
        if self._resize_event:
            Clock.unschedule(self._resize_event)
        self._resize_event = Clock.schedule_once(self.update_layout, 0.05)


    def init_ui(self, dt):
        self.draw_icons()
        self.draw_progress_bar()

    def update_layout(self, *args):
        self.draw_icons()
        self.draw_progress_bar()

    def draw_icons(self):
        self.draw_add_icon()
        self.draw_prev_icon()
        self.draw_next_icon()
        self.draw_play_icon()

    def draw_add_icon(self, *args):
        if self.add_texture:
            self.add_btn.canvas.before.clear()
            with self.add_btn.canvas.before:
                Rectangle(texture=self.add_texture, pos=self.add_btn.pos, size=self.add_btn.size)
            self.add_btn.unbind(pos=self.draw_add_icon, size=self.draw_add_icon)
            self.add_btn.bind(pos=self.draw_add_icon, size=self.draw_add_icon)

    def draw_next_icon(self, *args):
        if self.nav_texture:
            self.next_btn.canvas.before.clear()
            with self.next_btn.canvas.before:
                Rectangle(texture=self.nav_texture, pos=self.next_btn.pos, size=self.next_btn.size)
            self.next_btn.unbind(pos=self.draw_next_icon, size=self.draw_next_icon)
            self.next_btn.bind(pos=self.draw_next_icon, size=self.draw_next_icon)

    def draw_prev_icon(self, *args):
        if self.nav_texture_prev:
            self.prev_btn.canvas.before.clear()
            with self.prev_btn.canvas.before:
                Rectangle(texture=self.nav_texture_prev, pos=self.prev_btn.pos, size=self.prev_btn.size)
            self.prev_btn.unbind(pos=self.draw_prev_icon, size=self.draw_prev_icon)
            self.prev_btn.bind(pos=self.draw_prev_icon, size=self.draw_prev_icon)

    def draw_play_icon(self, *args):
        if not (self.play_texture or self.pause_texture):
            return
        self.play_btn.canvas.before.clear()
        with self.play_btn.canvas.before:
            tex = self.play_texture if not self.is_playing else self.pause_texture
            Rectangle(texture=tex, pos=self.play_btn.pos, size=self.play_btn.size)
        self.play_btn.unbind(pos=self.draw_play_icon, size=self.draw_play_icon)
        self.play_btn.bind(pos=self.draw_play_icon, size=self.draw_play_icon)

    def draw_progress_bar(self, *args):
        Clock.schedule_once(self._do_draw_progress_bar, 0)

    def _do_draw_progress_bar(self, dt):
        self.container.canvas.after.clear()
        with self.container.canvas.after:
            cx = self.container.center_x
            y = self.container.height * self.y_progress
            x = cx - self.progress_width / 2

            Color(0.3, 0.3, 0.3, 1)
            Line(
                width=dp(2),
                points=[
                    x, y + self.progress_height / 2,
                    x + self.progress_width, y + self.progress_height / 2
                ]
            )

            Color(0.6, 0.4, 0.8, 1)
            self.progress_fill_line = Line(
                width=dp(2),
                points=[
                    x, y + self.progress_height / 2,
                    x, y + self.progress_height / 2
                ]
            )

            if self.slider_texture:
                self.slider_inst = Rectangle(
                    texture=self.slider_texture,
                    pos=(0, 0),
                    size=(self.slider_size, self.slider_size)
                )

        self.update_progress_bar_position(self.progress_fraction)

    def update_progress_bar_position(self, progress):
        progress = max(0.0, min(1.0, progress))
        self.progress_fraction = progress

        cx = self.container.center_x
        x = cx - self.progress_width / 2
        y = self.container.height * self.y_progress
        filled_width = self.progress_width * progress

        self.progress_fill_line.points = [
            x, y + self.progress_height / 2,
            x + filled_width, y + self.progress_height / 2
        ]

        slider_x = x + filled_width - self.slider_size / 2
        slider_y = y - self.slider_size / 2
        if hasattr(self, 'slider_inst'):
            self.slider_inst.pos = (slider_x, slider_y)

    def on_progress_touch(self, widget, touch):
        if not self.player:
            return False

        cx = self.container.center_x
        x = cx - self.progress_width / 2
        y = self.container.height * self.y_progress
        bar_y = y + self.progress_height

        if x <= touch.x <= x + self.progress_width and y <= touch.y <= bar_y:
            self.is_scrubbing = True
            Clock.unschedule(self.update_progress_bar_from_player)

            pos_x = max(0, min(touch.x - x, self.progress_width))
            progress = pos_x / self.progress_width
            self.update_progress_bar_position(progress)

            duration = self.tracks[self.current_track_name()]["len_song"]
            seek_time = progress * duration

            if hasattr(self, '_seek_event') and self._seek_event:
                self._seek_event.cancel()
            self._seek_event = Clock.schedule_once(
                lambda dt: self.safe_seek(seek_time), 0.05
            )

            return True
        return False

    def safe_seek(self, seek_time):
        try:
            was_playing = self.is_playing

            self.load_current_track() 

            Clock.schedule_once(lambda dt: self.perform_seek_and_play(seek_time, was_playing), 0.1)

        except Exception as e:
            print(f"Ошибка перемотки: {e}")
            self.is_scrubbing = False
            self.ignore_end_check = False

    def perform_seek_and_play(self, seek_time, was_playing):
        try:
            if self.player:
                self.player.seek(seek_time)
                self.player.set_pause(not was_playing)

                duration = self.tracks[self.current_track_name()]["len_song"]
                self.update_progress_bar_position(seek_time / duration)

                if was_playing:
                    Clock.unschedule(self.update_progress_bar_from_player)
                    Clock.schedule_interval(self.update_progress_bar_from_player, 0.1)

                self.is_playing = was_playing
                self.is_scrubbing = False
                self.ignore_end_check = False
                self.draw_play_icon()

                print(f"Перемотка с перезагрузкой: {seek_time:.1f}")

        except Exception as e:
            print(f"Ошибка после seek: {e}")
            self.is_scrubbing = False
            self.ignore_end_check = False


    def reset_ignore_check(self, dt):
        self.ignore_end_check = False

    def reset_scrubbing(self, dt):
        self.is_scrubbing = False


    def on_play_press(self, instance):
        if not self.player:
            self.load_current_track()
            if not self.player:
                return

        self.is_playing = not self.is_playing
        self.player.set_pause(not self.is_playing)

        if self.is_playing:
            Clock.unschedule(self.update_progress_bar_from_player)
            Clock.schedule_interval(self.update_progress_bar_from_player, 0.1)
        else:
            Clock.unschedule(self.update_progress_bar_from_player)

        self.draw_play_icon()

    def load_current_track(self):
        path = self.current_track_name()
        if path not in self.tracks: return
        full_path = self.tracks[path]["filepath"]
        if not os.path.exists(full_path): return

        from ffpyplayer.player import MediaPlayer
        self.player = MediaPlayer(full_path)
        self.player.set_pause(True)

        duration = self.tracks[path]["len_song"]
        print(f"Загружен трек: {path} | Длительность: {duration:.1f} сек")

        Clock.schedule_interval(self.check_end, 0.5)

    def check_end(self, dt):
        if not self.is_playing or not self.player:
            return
        if self.ignore_end_check:
            return
        if self.is_scrubbing:
            return

        duration = self.tracks[self.current_track_name()]["len_song"]
        current = self.player.get_pts()
        if current >= duration - 0.5:
            self.next_track(None)


    def update_progress_bar_from_player(self, dt):
        if self.player and self.is_playing:
            duration = self.tracks[self.current_track_name()]["len_song"]
            current = self.player.get_pts()
            progress = current / duration
            self.update_progress_bar_position(progress)

    def next_track(self, instance):
        if len(self.track_names) <= 1: return
        self.current_index = (self.current_index + 1) % len(self.track_names)
        self.play_new_track()

    def previous_track(self, instance):
        if len(self.track_names) <= 1: return
        self.current_index = (self.current_index - 1) % len(self.track_names)
        self.play_new_track()

    def play_new_track(self):
        was_playing = self.is_playing
        self.is_playing = False
        if self.player:
            self.player.set_pause(True)
            self.player.close_player()
        self.current_pos = 0
        self.load_current_track()
        if was_playing:
            Clock.schedule_once(lambda dt: self.on_play_press(None), 0.1)

    def load_image(self, paths, mirror=False):
        for path in paths:
            if os.path.exists(path):
                try:
                    img = CoreImage(path)
                    if img.texture:
                        if not mirror:
                            return img.texture
                        else:
                            return self.flip_texture(img.texture)
                except Exception as e:
                    print(f"Ошибка загрузки {path}: {e}")
        return None

    def flip_texture(self, texture):
        fbo = Fbo(size=texture.size)
        with fbo:
            Color(1, 1, 1)
            Rectangle(
                pos=(0, 0),
                size=texture.size,
                texture=texture,
                tex_coords=[1, 0, 0, 0, 0, 1, 1, 1]
            )
        fbo.draw()
        flipped = fbo.texture
        flipped.flip_vertical()
        return flipped

    def current_track_name(self):
        return self.track_names[self.current_index]
    
    def start_add_music(self, instance):
        content = BoxLayout(orientation='vertical')
        fc = FileChooserListView(filters=['*.mp3', '*.wav'], path='/storage/emulated/0/Music')
        content.add_widget(fc)
        btns = BoxLayout(size_hint_y=None, height=50)
        cancel = Button(text="Отмена"); choose = Button(text="Выбрать")
        btns.add_widget(cancel); btns.add_widget(choose)
        content.add_widget(btns)
        self.file_popup = Popup(title="Выбери аудиофайл", content=content, size_hint=(0.9, 0.9))
        self.file_popup.open()
        choose.bind(on_press=lambda x: self.on_file_chosen(fc.selection))
        cancel.bind(on_press=self.file_popup.dismiss)

    def on_file_chosen(self, selection):
        self.file_popup.dismiss()
        if not selection: return
        self.selected_file_path = selection[0]
        self.show_metadata_form()

    def show_metadata_form(self):
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        layout.add_widget(Label(text="Название трека*", size_hint_y=None, height=30))
        self.title_input = TextInput(multiline=False)
        layout.add_widget(self.title_input)
        layout.add_widget(Label(text="Автор", size_hint_y=None, height=30))
        self.author_input = TextInput(multiline=False)
        layout.add_widget(self.author_input)
        layout.add_widget(Label(text="Альбом", size_hint_y=None, height=30))
        self.album_input = TextInput(multiline=False)
        layout.add_widget(self.album_input)
        btns = BoxLayout(size_hint_y=None, height=50)
        cancel = Button(text="Отмена"); save = Button(text="Добавить")
        btns.add_widget(cancel); btns.add_widget(save)
        layout.add_widget(btns)
        self.meta_popup = Popup(title="Добавить трек", content=layout, size_hint=(0.8, 0.7))
        self.meta_popup.open()
        save.bind(on_press=self.save_track)
        cancel.bind(on_press=self.meta_popup.dismiss)

    def save_track(self, instance):
        title = self.title_input.text.strip()
        if not title: return
        info = get_audio_info(self.selected_file_path)
        if not info: return
        length = round(info["len_song"], 1)
        music_dir = "music"; os.makedirs(music_dir, exist_ok=True)
        ext = os.path.splitext(self.selected_file_path)[1]
        dest_path = os.path.join(music_dir, f"{title}{ext}")
        shutil.copy(self.selected_file_path, dest_path)
        self.add_track_to_json(title, length)
        self.meta_popup.dismiss()
        Clock.schedule_once(self.refresh_tracks, 0.5)

    def add_track_to_json(self, title, length):
        tracks = {}
        if os.path.exists("tracks.json"):
            with open("tracks.json", "r", encoding="utf-8") as f:
                tracks = json.load(f)
        tracks[title] = {
            "len_song": length,
            "filepath": f"music/{title}{os.path.splitext(self.selected_file_path)[1]}"
        }
        with open("tracks.json", "w", encoding="utf-8") as f:
            json.dump(tracks, f, ensure_ascii=False, indent=4)

    def refresh_tracks(self, dt):
        self.tracks = load_tracks("tracks.json")
        self.track_names = list(self.tracks.keys())

    def show_message(self, text):
        popup = Popup(title="Сообщение", content=Label(text=text), size_hint=(0.6, 0.3))
        popup.open()
        Clock.schedule_once(lambda dt: popup.dismiss(), 2)


if __name__ == '__main__':
    MusicApp().run()

