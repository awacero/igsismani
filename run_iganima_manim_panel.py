"""Render the informational animation using the Manim helpers."""

from __future__ import annotations

import argparse
from pathlib import Path

from iganima.iganima_manim_panel import InfoAnimationConfig, render_info_animation


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render the IGANIMA Manim information animation.")
    parser.add_argument("--text", default="Magnitud 4.8", help="Text to display in the animation.")
    parser.add_argument("--bar-color", default="#3287C8", help="Hex color for the animated bar.")
    parser.add_argument("--text-color", default="#FFFFFF", help="Hex color for the displayed text.")
    parser.add_argument("--font-size", type=int, default=36, help="Font size for the magnitude text.")
    parser.add_argument("--output", default="info_animation.mp4", help="Filename for the rendered video.")
    parser.add_argument(
        "--pixel-size",
        type=int,
        nargs=2,
        metavar=("WIDTH", "HEIGHT"),
        default=(1280, 720),
        help="Output resolution in pixels (width height).",
    )
    parser.add_argument(
        "--frame-size",
        type=float,
        nargs=2,
        metavar=("WIDTH", "HEIGHT"),
        default=(14.0, 8.0),
        help="Logical frame size for the Manim camera (width height).",
    )
    parser.add_argument(
        "--background-color",
        default="#000000",
        help="Background color for the scene.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    pixel_width, pixel_height = args.pixel_size
    frame_width, frame_height = args.frame_size

    animation_config = InfoAnimationConfig(
        info_text=args.text,
        bar_color=args.bar_color,
        text_color=args.text_color,
        font_size=args.font_size,
        background_color=args.background_color,
    )

    output_path = Path(args.output)
    render_info_animation(
        animation_config,
        output_file=str(output_path),
        pixel_width=pixel_width,
        pixel_height=pixel_height,
        frame_width=frame_width,
        frame_height=frame_height,
    )


if __name__ == "__main__":
    main()
