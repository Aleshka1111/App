# майн
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
from load_track import load_tracks, load_liked, toggle_like
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
        self.queue = [] 

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

        self.block_next_prev = False
        self.container.bind(on_touch_up=self.on_touch_up)

        self.play_texture = self.load_image(['icons/play.png'])
        self.pause_texture = self.load_image(['icons/pause.png'])
        self.nav_texture = self.load_image(['icons/nextorback.png'])
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

        self.heart_outline_texture = self.load_image(['icons/heart_outline.png'])
        self.heart_filled_texture = self.load_image(['icons/heart_filled.png'])

        self.like_btn = self.create_button(pos_hint={'center_x': 0.78, 'y': self.y_buttons}, size=(self.btn_size, self.btn_size))
        self.container.add_widget(self.like_btn)
        self.like_btn.bind(on_press=self.on_like_press)

        self.like_btn.bind(pos=self.update_heart_icon, size=self.update_heart_icon)
        self.update_heart_icon()


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
        return Button(
            background_normal='',
            background_color=(0, 0, 0, 0),
            size_hint=(None, None),
            size=size,
            pos_hint=pos_hint
        )

    def init_ui(self, dt):
        self.draw_icons()
        self.draw_progress_bar()
        #self.update_heart_icon()

    def update_heart_icon(self, *args):
        liked = self.is_current_track_liked()
        tex = self.heart_filled_texture if liked else self.heart_outline_texture
        if tex:
            self.like_btn.canvas.before.clear()
            with self.like_btn.canvas.before:
                Rectangle(texture=tex, pos=self.like_btn.pos, size=self.like_btn.size)



    def is_current_track_liked(self):
        track_name = self.current_track_name()
        liked_list = load_liked()
        return track_name in liked_list


    def on_like_press(self, instance):
        track_name = self.current_track_name()
        toggled_on = toggle_like(track_name)  
        self.update_heart_icon()



    def update_layout(self, *args):
        if self._resize_event:
            Clock.unschedule(self._resize_event)
        self._resize_event = Clock.schedule_once(self._update_layout_safe, 0.05)

    def _update_layout_safe(self, dt):
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
            self.add_btn.bind(pos=self.draw_add_icon, size=self.draw_add_icon)

    def draw_next_icon(self, *args):
        if self.nav_texture:
            self.next_btn.canvas.before.clear()
            with self.next_btn.canvas.before:
                Rectangle(texture=self.nav_texture, pos=self.next_btn.pos, size=self.next_btn.size)
            self.next_btn.bind(pos=self.draw_next_icon, size=self.draw_next_icon)

    def draw_prev_icon(self, *args):
        if self.nav_texture_prev:
            self.prev_btn.canvas.before.clear()
            with self.prev_btn.canvas.before:
                Rectangle(texture=self.nav_texture_prev, pos=self.prev_btn.pos, size=self.prev_btn.size)
            self.prev_btn.bind(pos=self.draw_prev_icon, size=self.draw_prev_icon)

    def draw_play_icon(self, *args):
        if not (self.play_texture or self.pause_texture):
            return
        self.play_btn.canvas.before.clear()
        with self.play_btn.canvas.before:
            tex = self.play_texture if not self.is_playing else self.pause_texture
            Rectangle(texture=tex, pos=self.play_btn.pos, size=self.play_btn.size)
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
            if self.is_playing:
                Clock.unschedule(self.update_progress_bar_from_player)

            self.is_scrubbing = True

            pos_x = max(0, min(touch.x - x, self.progress_width))
            progress = pos_x / self.progress_width

            progress = max(0.001, min(0.99, progress))
            self.update_progress_bar_position(progress)

            if 'move' in touch.profile:
                now = time()
                if now - self._last_seek_time > 0.1:
                    self._last_seek_time = now
                    self._simple_seek(progress)
            else:
                if self._seek_event:
                    Clock.unschedule(self._seek_event)
                self._seek_event = Clock.schedule_once(
                    lambda dt: self._simple_seek(progress), 0.1
                )
            
            return True
        return False

    def _simple_seek(self, progress):
        if not self.player:
            return
        
        try:
            track_name = self.current_track_name()
            if track_name not in self.tracks:
                return
                
            duration = self.tracks[track_name]["len_song"]
            if duration <= 0:
                return
            
            seek_time = progress * duration
            
            print(f"Перемотка: {seek_time:.1f}/{duration:.1f} сек")
            
            self.ignore_end_check = True
            Clock.schedule_once(self.reset_ignore_check, 2.0)
            
            was_playing = self.is_playing
            
            if was_playing:
                self.player.set_pause(True)
            Clock.schedule_once(lambda dt: self._do_actual_seek(seek_time, was_playing, progress), 0.05)
            
        except Exception as e:
            print(f"Ошибка подготовки перемотки: {e}")

    def _do_actual_seek(self, seek_time, was_playing, progress):
        try:
            result = self.player.seek(seek_time, relative=False, accurate=False)

            self.update_progress_bar_position(progress)

            if was_playing:
                Clock.schedule_once(lambda dt: self._safe_resume(), 0.1)
                
        except Exception as e:
            print(f"Ошибка перемотки: {e}")

    def _safe_resume(self):
        if self.player and self.is_playing:
            try:
                self.player.set_pause(False)
            except:
                pass
    
    def on_touch_up(self, widget, touch):
        if self.is_scrubbing:
            self.is_scrubbing = False
            if self.is_playing:
                Clock.schedule_interval(self.update_progress_bar_from_player, 0.1)
        return False

    def reset_ignore_check(self, dt):
        self.ignore_end_check = False

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
        if self.player:
            self.player.close_player()
        path = self.current_track_name()
        full_path = self.tracks[path]["filepath"]
        if not os.path.exists(full_path):
            return

        from ffpyplayer.player import MediaPlayer
        self.player = MediaPlayer(full_path)
        self.player.set_pause(True)

        Clock.unschedule(self.check_end)
        Clock.schedule_interval(self.check_end, 0.5)

    def check_end(self, dt):
        if not self.is_playing or not self.player or self.ignore_end_check or self.is_scrubbing:
            return
        
        try:
            track_name = self.current_track_name()
            if track_name in self.tracks:
                duration = self.tracks[track_name]["len_song"]
                current = self.player.get_pts()
                if current is not None and duration > 0 and current >= 0:
                    if current >= duration - 0.5:
                        print(f"Трек закончился, переключаем: {current:.1f}/{duration:.1f}")
                        self.next_track(None)
        except:
            pass

    def update_progress_bar_from_player(self, dt):
        if self.player and self.is_playing and not self.is_scrubbing:
            try:
                current = self.player.get_pts()
                if current is None:
                    return
                    
                track_name = self.current_track_name()
                if track_name in self.tracks:
                    duration = self.tracks[track_name]["len_song"]
                    if duration > 0 and current >= 0:
                        progress = min(current / duration, 0.999)
                        self.update_progress_bar_position(progress)
            except Exception as e:
                pass
    def next_track(self, instance):
        if self.block_next_prev:
            return
        self.block_next_prev = True
        Clock.schedule_once(self.reset_block_next_prev, 0.3)
        self._next_track_logic()

    def previous_track(self, instance):
        if self.block_next_prev:
            return
        self.block_next_prev = True
        Clock.schedule_once(self.reset_block_next_prev, 0.3)
        self._previous_track_logic()

    def reset_block_next_prev(self, dt):
        self.block_next_prev = False

    def _next_track_logic(self):
        if self.queue:
            next_name = self.queue.pop(0)
            if next_name in self.tracks:
                self.current_index = self.track_names.index(next_name)
            else:
                self._next_track_fallback()
        else:
            self._next_track_fallback()

    def _previous_track_logic(self):
        self.current_index = (self.current_index - 1) % len(self.track_names)
        self.play_new_track()

    def _next_track_fallback(self):
        self.current_index = (self.current_index + 1) % len(self.track_names)
        self.play_new_track()

    def _next_track_logic(self):
        if self.queue:
            next_name = self.queue.pop(0)
            if next_name in self.tracks:
                self.current_index = self.track_names.index(next_name)
            else:
                self._next_track_fallback()
        else:
            self._next_track_fallback()

    def play_new_track(self):
        was_playing = self.is_playing
        self.is_playing = False
        if self.player:
            self.player.set_pause(True)
            self.player.close_player()
        self.load_current_track()
        if was_playing:
            Clock.schedule_once(lambda dt: self.on_play_press(None), 0.1)
        Clock.schedule_once(lambda dt: self.update_heart_icon(), 0.05)

    def load_image(self, paths):
        for path in paths:
            if os.path.exists(path):
                img = CoreImage(path)
                if img.texture:
                    return img.texture
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
        fc = FileChooserListView(filters=['*.mp3', '*.wav'], path='/storage/emulated/0/Music')#да ошибка, но мне поебать 
        content.add_widget(fc)
        btns = BoxLayout(size_hint_y=None, height=50)
        cancel = Button(text="Отмена")
        choose = Button(text="Выбрать")
        btns.add_widget(cancel)
        btns.add_widget(choose)
        content.add_widget(btns)
        self.file_popup = Popup(title="Выбери аудиофайл", content=content, size_hint=(0.9, 0.9))
        self.file_popup.open()
        choose.bind(on_press=lambda x: self.on_file_chosen(fc.selection))
        cancel.bind(on_press=self.file_popup.dismiss)

    def on_file_chosen(self, selection):
        self.file_popup.dismiss()
        if not selection:
            return
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
        cancel = Button(text="Отмена")
        save = Button(text="Добавить в очередь")
        btns.add_widget(cancel)
        btns.add_widget(save)
        layout.add_widget(btns)
        self.meta_popup = Popup(title="Добавить в очередь", content=layout, size_hint=(0.8, 0.7))
        self.meta_popup.open()
        save.bind(on_press=self.add_to_queue)
        cancel.bind(on_press=self.meta_popup.dismiss)

    def add_to_queue(self, instance):
        title = self.title_input.text.strip()
        if not title:
            return
        if title in self.tracks:
            self.queue.append(title)
            print(f"Трек '{title}' добавлен в очередь")
        else:
            info = get_audio_info(self.selected_file_path)
            if not info:
                return
            length = round(info["len_song"], 1)
            music_dir = "music"
            os.makedirs(music_dir, exist_ok=True)
            ext = os.path.splitext(self.selected_file_path)[1]
            dest_path = os.path.join(music_dir, f"{title}{ext}")
            shutil.copy(self.selected_file_path, dest_path)
            self.tracks[title] = {
                "filepath": f"music/{title}{ext}",
                "len_song": length
            }
            self.track_names.append(title)
            self.queue.append(title)
            print(f"Новый трек '{title}' добавлен и в очередь")

        self.meta_popup.dismiss()

    def save_track(self, instance):  
        pass  

    def show_message(self, text):
        popup = Popup(title="Сообщение", content=Label(text=text), size_hint=(0.6, 0.3))
        popup.open()
        Clock.schedule_once(lambda dt: popup.dismiss(), 2)


if __name__ == '__main__':
    MusicApp().run()