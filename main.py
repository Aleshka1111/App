from kivy.app import App
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.core.audio import SoundLoader
from kivy.core.image import Image as CoreImage
from kivy.graphics import Rectangle, Color
from kivy.clock import Clock
import os


class MusicApp(App):
    def build(self):
        layout = BoxLayout(orientation='vertical', padding=30, spacing=20)
        try:
            from ffpyplayer.player import MediaPlayer
            self.player = MediaPlayer('music/люби меня алина.mp3')
            self.player.set_pause(True)  
            self.use_ffpy_direct = True
        except Exception as e:
            print(f"ffpyplayer: {e}")
            self.sound = SoundLoader.load('music/overdose.wav')
            self.use_ffpy_direct = False
            if not self.sound:
                layout.add_widget(Button(text="Файл не найден", font_size=20))
                return layout

        self.play_texture = self.load_image(['icons/play.png', 'icons/play.jpg', 'icons/play.jpeg'])
        self.pause_texture = self.load_image(['icons/pause.png', 'icons/pause.jpg', 'icons/pause.jpeg'])

        self.btn = Button(
            background_normal='',   
            background_down='',     
            size_hint=(None, None),
            width=300,
            height=300,
            pos_hint={'center_x': 0.5}
        )
        self.btn.canvas.clear()
        with self.btn.canvas:

            self.icon_rect = Rectangle(
                texture=self.play_texture or None,
                pos=self.btn.pos,
                size=self.btn.size
            )
        self.btn.bind(pos=self.update_canvas, size=self.update_canvas)
        self.btn.bind(on_press=self.on_button_press)
        layout.add_widget(self.btn)
        self.current_pos = 0
        self.is_playing = False

        return layout

    def update_canvas(self, instance, value):
        self.icon_rect.pos = instance.pos
        self.icon_rect.size = instance.size


    def load_image(self, paths):
        for path in paths:
            if os.path.exists(path):
                try:
                    img = CoreImage(path)
                    if img.texture and img.texture.width > 0:
                        print(f"Загружено: {path} (размер: {img.texture.size})")
                        return img.texture
                    else:
                        print(f"Текстура пустая: {path}")
                except Exception as e:
                    print(f"Ошибка {path}: {e}")
            else:
                print(f"Файл не найден: {path}")
        return None

    def on_button_press(self, instance):
        if self.use_ffpy_direct:
            self.handle_ffpy_direct(instance)
        else:
            self.handle_sound_loader(instance)

    def handle_ffpy_direct(self, instance):
        if self.is_playing:
            self.current_pos = self.player.get_pts()
            self.player.set_pause(True)
            if self.icon_rect and self.play_texture:
                self.icon_rect.texture = self.play_texture
            else:
                self.btn.text = "PLAY"
            self.is_playing = False
        else:
            self.player.set_pause(False)
            if self.current_pos > 0:
                self.player.seek(self.current_pos, relative=False)
            if self.icon_rect and self.pause_texture:
                self.icon_rect.texture = self.pause_texture
            else:
                self.btn.text = "PAUSE"
            self.is_playing = True

    def handle_sound_loader(self, instance):
        if self.is_playing:
            self.current_pos = self.sound.get_pos()
            self.sound.stop()
            if self.icon_rect and self.play_texture:
                self.icon_rect.texture = self.play_texture
            else:
                self.btn.text = "PLAY"
            self.is_playing = False
        else:
            self.sound.play()
            if self.icon_rect and self.pause_texture:
                self.icon_rect.texture = self.pause_texture
            else:
                self.btn.text = "PAUSE"
            self.is_playing = True


if __name__ == '__main__':
    MusicApp().run()
