# main.py
from kivy.app import App
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.core.image import Image as CoreImage
from kivy.graphics import Rectangle, Color, PushMatrix, PopMatrix, Rotate
from kivy.clock import Clock
from kivy.uix.anchorlayout import AnchorLayout  
import os
from load_track import load_tracks


class MusicApp(App):
    def build(self):
        self.tracks = load_tracks("tracks.json")
        if not self.tracks:
            layout = BoxLayout(orientation='vertical')
            layout.add_widget(Label(text="Нет треков", font_size=24))
            return layout

        self.track_names = list(self.tracks.keys())
        self.current_index = 0
        self.current_pos = 0
        self.is_playing = False
        self.player = None

        main_layout = BoxLayout(orientation='vertical')

        spacer = BoxLayout(size_hint_y=1)
        main_layout.add_widget(spacer)

        controls = BoxLayout(
            orientation='horizontal',
            size_hint=(None, None), 
            spacing=40,
            width=300,  
            height=100
        )

        btn_size = (80, 80)

        self.prev_btn = Button(
            background_normal='',
            background_down='',
            size_hint=(None, None),
            width=btn_size[0],
            height=btn_size[1]
        )
        self.prev_btn.bind(on_press=self.previous_track)
        controls.add_widget(self.prev_btn)

        self.play_btn = Button(
            background_normal='',
            background_down='',
            size_hint=(None, None),
            width=btn_size[0],
            height=btn_size[1]
        )
        self.play_btn.bind(on_press=self.on_play_press)
        controls.add_widget(self.play_btn)

        self.next_btn = Button(
            background_normal='',
            background_down='',
            size_hint=(None, None),
            width=btn_size[0],
            height=btn_size[1]
        )
        self.next_btn.bind(on_press=self.next_track)
        controls.add_widget(self.next_btn)

        anchor = AnchorLayout(
            anchor_x='center',
            anchor_y='center',
            size_hint_y=None,
            height=100
        )
        anchor.add_widget(controls)
        main_layout.add_widget(anchor)

        self.play_texture = self.load_image(['icons/play.png'])
        self.pause_texture = self.load_image(['icons/pause.png'])
        self.nav_texture = self.load_image(['icons/nextorback.png'])

        self.update_navigation_icons()
        self.update_play_button_icon()

        self.load_current_track()

        return main_layout

    def current_track_name(self):
        return self.track_names[self.current_index] if self.track_names else "Неизвестно"

    def current_track_path(self):
        return f"music/{self.current_track_name()}.mp3"

    def load_current_track(self):
        path = self.current_track_path()
        if os.path.exists(path):
            if self.player:
                self.player.close_player()
            from ffpyplayer.player import MediaPlayer
            from ffpyplayer.tools import set_loglevel
            set_loglevel("quiet")
            self.player = MediaPlayer(path)
            self.player.set_pause(True)
            print(f"Загружен: {path}")
        else:
            print(f"Файл не найден: {path}")

    def update_navigation_icons(self):
        if self.nav_texture:
            self.draw_rotated_icon(self.prev_btn, self.nav_texture, 180)  
            self.draw_rotated_icon(self.next_btn, self.nav_texture, 0)    

    def draw_rotated_icon(self, btn, texture, angle):
        btn.canvas.clear()
        with btn.canvas:
            PushMatrix()
            Rotate(angle=angle, origin=btn.center)
            Rectangle(
                texture=texture,
                pos=btn.pos,
                size=btn.size
            )
            PopMatrix()

        btn.bind(
            pos=lambda instance, value: self.draw_rotated_icon(btn, texture, angle),
            size=lambda instance, value: self.draw_rotated_icon(btn, texture, angle)
    )


    def update_play_button_icon(self):
        if not self.play_btn.canvas or not self.play_texture:
            return
        self.play_btn.canvas.clear()
        with self.play_btn.canvas:
            self.icon_rect = Rectangle(
                texture=self.play_texture if not self.is_playing else self.pause_texture,
                pos=self.play_btn.pos,
                size=self.play_btn.size
            )
        self.play_btn.bind(pos=self.update_icon_pos, size=self.update_icon_pos)


    def update_icon_pos(self, instance, value):
        if hasattr(self, 'icon_rect') and self.icon_rect:
            self.icon_rect.pos = instance.pos
            self.icon_rect.size = instance.size

    def on_play_press(self, instance):
        if not self.player:
            return
        if self.is_playing:
            self.current_pos = self.player.get_pts()
            self.player.set_pause(True)
            self.icon_rect.texture = self.play_texture
            self.is_playing = False
        else:
            self.player.set_pause(False)
            if self.current_pos > 0:
                self.player.seek(self.current_pos, relative=False)
            self.icon_rect.texture = self.pause_texture
            self.is_playing = True

    def next_track(self, instance):
        if len(self.track_names) <= 1:
            return
        self.current_index = (self.current_index + 1) % len(self.track_names)
        self.play_new_track()

    def previous_track(self, instance):
        if len(self.track_names) <= 1:
            return
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
            Clock.schedule_once(self.start_current_track, 0.1)


    def start_current_track(self, dt):
        if self.player:
            self.player.set_pause(False)
            if hasattr(self, 'icon_rect'):
                self.icon_rect.texture = self.pause_texture
            self.is_playing = True

    def load_image(self, paths):
        for path in paths:
            if os.path.exists(path):
                try:
                    img = CoreImage(path)
                    if img.texture and img.texture.width > 0:
                        print(f"Загружено: {path}")
                        return img.texture
                except Exception as e:
                    print(f" Ошибка {path}: {e}")
            else:
                print(f"Не найден: {path}")
        return None


if __name__ == '__main__':
    MusicApp().run()
