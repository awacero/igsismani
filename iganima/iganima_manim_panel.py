"""Manim-based animation helpers for IGANIMA informational panels."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from manim import FadeIn, Rectangle, Scene, Text, config


@dataclass
class InfoAnimationConfig:
    """Configuration options for the information bar animation."""

    info_text: str = "Magnitud 4.8"
    bar_color: str = "#3287C8"
    text_color: str = "#FFFFFF"
    font_size: int = 36
    bar_initial_width: float = 0.01
    bar_height: float = 0.8
    bar_target_width: float = 6.0
    bar_animation_time: float = 1.2
    text_fade_time: float = 0.6
    background_color: str = "#000000"


class InfoAnimation(Scene):
    """Animate a horizontal bar that reveals the magnitude text."""

    def __init__(self, animation_config: Optional[InfoAnimationConfig] = None, **kwargs):
        self.animation_config = animation_config or InfoAnimationConfig()
        super().__init__(**kwargs)

    def construct(self) -> None:  # pragma: no cover - requires manim engine
        cfg = self.animation_config

        bar = Rectangle(
            width=cfg.bar_initial_width,
            height=cfg.bar_height,
            fill_color=cfg.bar_color,
            fill_opacity=1,
            stroke_width=0,
        )
        bar.set_fill(cfg.bar_color)
        bar.set_stroke(width=0)

        text = Text(
            cfg.info_text,
            color=cfg.text_color,
            font_size=cfg.font_size,
        )
        text.move_to(bar.get_center())

        self.camera.background_color = cfg.background_color

        self.play(bar.animate.stretch_to_fit_width(cfg.bar_target_width), run_time=cfg.bar_animation_time)
        self.play(FadeIn(text), run_time=cfg.text_fade_time)


def render_info_animation(
    animation_config: Optional[InfoAnimationConfig] = None,
    *,
    output_file: str = "info_animation.mp4",
    media_width: str = "100%",
    pixel_height: int = 720,
    pixel_width: int = 1280,
    frame_height: float = 8.0,
    frame_width: float = 14.0,
    background_color: Optional[str] = None,
) -> None:
    """Render the informational animation directly, without invoking the CLI."""

    animation_config = animation_config or InfoAnimationConfig()
    if background_color is not None:
        animation_config.background_color = background_color

    output_path = Path(output_file).expanduser()
    if not output_path.is_absolute():
        output_path = Path.cwd() / output_path

    config.media_width = media_width
    config.pixel_height = pixel_height
    config.pixel_width = pixel_width
    config.frame_height = frame_height
    config.frame_width = frame_width
    config.output_file = output_path.name
    config.output_directory = str(output_path.parent)
    config.background_color = animation_config.background_color

    scene = InfoAnimation(animation_config)
    scene.render()
