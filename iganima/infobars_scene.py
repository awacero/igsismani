from manim import *
from PIL import Image
import os


class InfoBarsScene(Scene):
    """
    Clase independiente para generar animaciones de barras informativas sísmicas
    usando Manim. Guarda los frames como imágenes PNG.
    """

    def __init__(self, event_info, output_dir="frames_info", n_frames=20, **kwargs):
        super().__init__(**kwargs)
        self.event_info = event_info
        self.output_dir = output_dir
        self.n_frames = n_frames

        os.makedirs(output_dir, exist_ok=True)

    def make_bar(self, height, color, text_str, font_size):
        bar = RoundedRectangle(
            width=0.01,
            height=height,
            fill_color=color,
            fill_opacity=1,
            corner_radius=0.15,
            stroke_width=0
        )
        text = Text(text_str, color=WHITE, font_size=font_size).move_to(bar.get_center())
        return bar, text

    def construct(self):

    
        blue_dark = "#1A4C80"
        blue_light = "#4EA7E0"
        info = self.event_info
        N = self.n_frames

        # Fondo blanco
        background = Rectangle(
            width=config.frame_width,
            height=config.frame_height * 1.5,
            fill_color=WHITE,
            fill_opacity=1,
            stroke_width=0
        )
        self.add(background)

        # Crear barras y textos
        bar_magnitude, text_magnitude = self.make_bar(1.1, blue_light, f"Magnitud {info['magnitude']}", 56)
        bar_depth, text_depth = self.make_bar(1.1, blue_dark, f"{info['depth']} Km. de profundidad", 46)
        bar_location, text_location = self.make_bar(1.1, blue_light, f"a : {info['distance']} Km. de  {info['city']}", 56)
        bar_province, text_province = self.make_bar(1.1, blue_dark, f"Provincia: {info['province']}", 46)
        bar_date, text_date = self.make_bar(1.1, blue_light, f"Fecha: {info['local_date']}", 56)
        bar_time, text_time = self.make_bar(1.1, blue_dark, f"Hora: {info['local_time']}", 46)

        bars = VGroup(bar_magnitude, bar_depth, bar_location, bar_province, bar_date, bar_time).arrange(DOWN, buff=0.05)
        texts = VGroup(text_magnitude, text_depth, text_location, text_province, text_date, text_time)

        for bar, txt in zip(bars, texts):
            txt.move_to(bar.get_center())

        self.add(bars, texts)

        # Animación: crecimiento progresivo
        target_widths = [8, 6, 8, 6, 8, 6]
        for i in range(N):
            for idx, bar in enumerate(bars):
                w = 0.1 + (target_widths[idx] - 0.1) * (i + 1) / N
                bar_new = RoundedRectangle(
                    width=w,
                    height=bar.height,
                    fill_color=bar.fill_color,
                    fill_opacity=1,
                    corner_radius=0.15,
                    stroke_width=0
                ).move_to(bar.get_center())
                bars[idx].become(bar_new)
                texts[idx].move_to(bars[idx].get_center())

            self.wait(0.01)
            frame = self.renderer.get_frame()
            img = Image.fromarray(frame)
            img.save(os.path.join(self.output_dir, f"info_{i:03}.png"))

    def generate_frames(self):
        """Configura parámetros y ejecuta el renderizado."""

        config.preview = False
        config.save_last_frame = False
        config.write_to_movie = False
        self.render()
