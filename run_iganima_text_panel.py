"""Runner that generates frames using the styled text panel module."""

import argparse
import configparser
import json
import logging
import logging.config
import os
from dataclasses import fields
from pathlib import Path
from typing import Dict, Iterable, Optional, Sequence

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from obspy import read_inventory

from iganima import iganima_utils as u
from iganima.iganima_functions import (
    clean_frame_directory,
    compile_animation,
    create_circle_frames,
    create_initial_point_frame,
    create_line_growth_frame,
    create_sine_wave_frame,
)
from iganima import get_circle_color
from iganima.iganima_text_panel import (
    PanelTheme,
    SeismicTextInfo,
    save_frame_with_text_panel,
)


pd.set_option("display.max_colwidth", None)
pd.set_option("display.max_columns", None)


def read_parameters(file_path: str) -> Dict[str, Dict[str, str]]:
    """Read an INI configuration file and return the parsed sections."""

    parser = configparser.ConfigParser()
    parser.read(file_path)
    return parser._sections


def load_config_from_file(json_file_path: str) -> Dict[str, Dict[str, str]]:
    """Read a JSON configuration file and expand any environment variables."""

    with open(os.path.expandvars(json_file_path), "r", encoding="utf-8") as file_obj:
        config_data = json.load(file_obj)

    def expand_env(value):
        if isinstance(value, str):
            return os.path.expandvars(value)
        if isinstance(value, dict):
            return {k: expand_env(v) for k, v in value.items()}
        if isinstance(value, list):
            return [expand_env(v) for v in value]
        return value

    return expand_env(config_data)


def configure_logging() -> logging.Logger:
    """Initialise logging using the repository configuration."""

    logging.config.fileConfig(Path("./config/", "logging.ini"), disable_existing_loggers=True)
    logger = logging.getLogger(__name__)
    logger.info("Logging configuration loaded")
    return logger


def _safe_get_section_value(section: Dict[str, str], key: str, default: Optional[str] = None) -> Optional[str]:
    value = section.get(key) if section else None
    return value if value not in (None, "") else default


def _extract_comment_distance(comment: str) -> Optional[str]:
    if not comment:
        return None
    for segment in comment.split(","):
        if "km" in segment.lower():
            return segment.strip()
    return None


def _extract_comment_province(comment: str) -> Optional[str]:
    if not comment:
        return None
    for segment in comment.split(","):
        if "prov" in segment.lower():
            return segment.strip()
    return None


def _get_event_description(event_obj, keywords: Iterable[str]) -> Optional[str]:
    for description in getattr(event_obj, "event_descriptions", []) or []:
        description_type = (description.type or "").lower()
        if any(keyword in description_type for keyword in keywords):
            return description.text.strip()
    return None


def _parse_bool(value: Optional[str], default: bool) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _build_panel_theme(animation_config: Dict[str, str]) -> PanelTheme:
    theme_kwargs = {}
    for field in fields(PanelTheme):
        config_key = f"text_panel_{field.name}"
        raw_value = _safe_get_section_value(animation_config, config_key)
        if raw_value is None:
            continue
        if field.type is int:
            try:
                theme_kwargs[field.name] = int(raw_value)
            except ValueError:
                continue
        else:
            theme_kwargs[field.name] = raw_value
    if theme_kwargs:
        return PanelTheme(**theme_kwargs)
    return PanelTheme()


def _load_logo_overlays(animation_config: Dict[str, str]) -> Optional[Sequence[dict]]:
    logos_path = _safe_get_section_value(animation_config, "text_panel_logos_json")
    if not logos_path:
        return None
    with open(os.path.expandvars(logos_path), "r", encoding="utf-8") as file_obj:
        return json.load(file_obj)


def _build_seismic_text_info(
    event_dict: Dict[str, str],
    event_obj,
    animation_config: Dict[str, str],
) -> SeismicTextInfo:
    comment_text = event_obj.comments[0].text if getattr(event_obj, "comments", None) else ""
    distance_text = _safe_get_section_value(animation_config, "text_panel_distance_text")
    if distance_text is None:
        distance_text = (
            _extract_comment_distance(comment_text)
            or _get_event_description(event_obj, ("region", "area"))
            or f"Lat. {event_dict['latitude']}°, Lon. {event_dict['longitude']}°"
        )

    province_text = _safe_get_section_value(animation_config, "text_panel_province_text")
    if province_text is None:
        province_text = (
            _extract_comment_province(comment_text)
            or _get_event_description(event_obj, ("earthquake name", "region"))
            or "Por confirmar"
        )

    status_text = _safe_get_section_value(animation_config, "text_panel_status_text", event_dict.get("status", ""))
    hashtags_text = _safe_get_section_value(animation_config, "text_panel_hashtags_text", "")
    header_title = _safe_get_section_value(animation_config, "text_panel_header_title", "INFORMATIVO SISMO")
    header_subtitle = _safe_get_section_value(animation_config, "text_panel_header_subtitle", "Actualización")

    info = SeismicTextInfo.from_event_dict(
        event_dict,
        distance_text=distance_text,
        province_text=province_text,
        status_text=status_text,
        hashtags_text=hashtags_text,
        header_title=header_title,
        header_subtitle=header_subtitle,
    )

    info.footer_text = _safe_get_section_value(animation_config, "text_panel_footer_text", info.footer_text)
    info.header_icon_text = _safe_get_section_value(animation_config, "text_panel_header_icon_text", info.header_icon_text)
    info.magnitude_subtitle = _safe_get_section_value(animation_config, "text_panel_magnitude_subtitle", info.magnitude_subtitle)
    info.depth_subtitle = _safe_get_section_value(animation_config, "text_panel_depth_subtitle", info.depth_subtitle)
    info.location_subtitle = _safe_get_section_value(animation_config, "text_panel_location_subtitle", info.location_subtitle)
    info.province_subtitle = _safe_get_section_value(animation_config, "text_panel_province_subtitle", info.province_subtitle)
    info.status_title = _safe_get_section_value(animation_config, "text_panel_status_title", info.status_title)
    info.date_title = _safe_get_section_value(animation_config, "text_panel_date_title", info.date_title)
    info.show_magnitude_marker = _parse_bool(
        _safe_get_section_value(animation_config, "text_panel_show_magnitude_marker"),
        info.show_magnitude_marker,
    )
    info.magnitude_marker_color = _safe_get_section_value(
        animation_config,
        "text_panel_magnitude_marker_color",
        info.magnitude_marker_color,
    )
    return info


def main(args, logger: logging.Logger) -> None:
    configuration_file = args.iganima_config
    event_id = args.event_id

    logger.info("Generating styled animation for event %s", event_id)

    if not os.path.isfile(configuration_file):
        raise FileNotFoundError(f"Configuration file {configuration_file} does not exist")

    run_param = read_parameters(configuration_file)
    mseed_server_param = load_config_from_file(run_param["fdsn"]["server_config_file"])

    fdsn_server_ip = mseed_server_param[run_param["fdsn"]["server_id"]]["server_ip"]
    fdsn_server_port = mseed_server_param[run_param["fdsn"]["server_id"]]["port"]

    fdsn_client = u.connect_fdsn(fdsn_server_ip, fdsn_server_port)

    frame_directory = run_param["animation"]["frame_directory"]
    clean_frame_directory(frame_directory)

    event_inventory = u.get_event_by_id(fdsn_client, event_id)
    event_dict = u.event2dict(event_inventory[0])

    event_annotation = (
        f"ID: {event_dict['event_id']} {event_dict['status']}<br>{event_dict['time_local']} Hora Local"
        f"<br>Prof. {event_dict['depth']} Km.  Magnitud:  {event_dict['magnitude']}"
    )

    event_latitude = event_dict["latitude"]
    event_longitude = event_dict["longitude"]
    intensity = event_dict["magnitude"]

    inventory = read_inventory(run_param["fdsn"]["xml_inventory_file"])

    picks_df = u.picks2dataframe(event_inventory)
    stations_set = set(picks_df[:].apply(lambda row: f"{row['network']}.{row['station']}", axis=1))

    _, stations_list = u.create_stations_dict(stations_set, inventory)
    station_list_temp = [u.attach_distance_dict(station_dict, event_inventory[0]) for station_dict in stations_list]
    station_list_sorted = sorted(station_list_temp, key=lambda x: x["distance"])
    station_lat_lon_list_ordered = [(station["latitude"], station["longitude"]) for station in station_list_sorted]
    station_name_list_ordered = [station["station_id"].split(".")[1] for station in station_list_sorted]
    lat_stations, lon_stations = zip(*station_lat_lon_list_ordered)

    animation_config = run_param.get("animation", {})
    text_info = _build_seismic_text_info(event_dict, event_inventory[0], animation_config)
    theme = _build_panel_theme(animation_config)
    logos = _load_logo_overlays(animation_config)

    text_magnitude = [f"{intensity}"]
    circle_colors = get_circle_color.get_colors_from_intensity(intensity)
    sinewave_color = get_circle_color.get_color_from_intensity(intensity)

    vertical_scale = get_circle_color.get_value_from_intensity(intensity)
    horizontal_scale = 0.3
    seismic_wave_time = np.linspace(-1, 1, 100)
    lon_total = np.linspace(event_longitude - horizontal_scale, event_longitude + horizontal_scale, len(seismic_wave_time))
    waveform = np.exp(-seismic_wave_time ** 2) * np.sin(13 * seismic_wave_time)

    MAX_LEN = len(seismic_wave_time)
    SEISMIC_WAVE_GROW = 10
    SEISMIC_WAVE_SHRINK = 10
    LINE_2_POINT_FRAMES = 5
    POINT_FRAMES = 2
    LINE_GROWTH_FRAMES = 3
    WAVE_GROWTH_FRAMES = 5

    total_frames = int(run_param["animation"]["frames_number"])

    for t in range(1, total_frames + 1):
        if t <= POINT_FRAMES + 1:
            frame_data = create_initial_point_frame(
                event_longitude, event_latitude, lon_stations, lat_stations, station_name_list_ordered
            )
        elif POINT_FRAMES - 1 <= t <= POINT_FRAMES + LINE_GROWTH_FRAMES:
            frame_data = create_line_growth_frame(
                t,
                POINT_FRAMES,
                LINE_GROWTH_FRAMES,
                MAX_LEN,
                lon_total,
                event_latitude,
                lon_stations,
                lat_stations,
                station_name_list_ordered,
            )
        elif POINT_FRAMES + LINE_GROWTH_FRAMES <= t < POINT_FRAMES + LINE_GROWTH_FRAMES + WAVE_GROWTH_FRAMES:
            frame_data = create_sine_wave_frame(
                t,
                POINT_FRAMES,
                LINE_GROWTH_FRAMES,
                WAVE_GROWTH_FRAMES,
                waveform,
                vertical_scale,
                lon_total,
                event_latitude,
                lon_stations,
                lat_stations,
                station_name_list_ordered,
                is_growing=True,
            )
        elif POINT_FRAMES + LINE_GROWTH_FRAMES + WAVE_GROWTH_FRAMES <= t <= POINT_FRAMES + LINE_GROWTH_FRAMES + WAVE_GROWTH_FRAMES * 2:
            frame_data = create_sine_wave_frame(
                t,
                POINT_FRAMES,
                LINE_GROWTH_FRAMES,
                WAVE_GROWTH_FRAMES,
                waveform,
                vertical_scale,
                lon_total,
                event_latitude,
                lon_stations,
                lat_stations,
                station_name_list_ordered,
                is_growing=False,
            )
        elif (
            POINT_FRAMES + LINE_GROWTH_FRAMES + WAVE_GROWTH_FRAMES * 2
            <= t
            <= POINT_FRAMES + LINE_GROWTH_FRAMES * 2 + WAVE_GROWTH_FRAMES * 2
        ):
            shrink_time = t - (POINT_FRAMES + LINE_GROWTH_FRAMES + WAVE_GROWTH_FRAMES * 2)
            length = int(np.interp(shrink_time, [0, LINE_2_POINT_FRAMES], [MAX_LEN, 1]))
            mid = MAX_LEN // 2
            idx_range = slice(mid - length // 2, mid + length // 2)
            lon = lon_total[idx_range]
            lat = np.full_like(lon, event_latitude)

            frame_data = [
                go.Scattermapbox(
                    lon=lon,
                    lat=lat,
                    mode="lines",
                    line=dict(width=1, color=sinewave_color),
                    showlegend=False,
                    hoverinfo="skip",
                ),
                go.Scattermapbox(
                    lon=lon_stations,
                    lat=lat_stations,
                    text=station_name_list_ordered,
                    mode="markers+text",
                    marker=dict(color=[], size=4, symbol="circle"),
                    textposition="top left",
                    showlegend=False,
                    hoverinfo="text",
                ),
            ]
        else:
            frame_data = create_circle_frames(
                t,
                SEISMIC_WAVE_GROW,
                SEISMIC_WAVE_SHRINK,
                event_latitude,
                event_longitude,
                circle_colors,
                station_lat_lon_list_ordered,
                lon_stations,
                lat_stations,
                station_name_list_ordered,
                text_magnitude,
            )

        frame_name = os.path.join(frame_directory, f"frame_{t:03}.png")
        fig = go.Figure(data=frame_data)
        zoom_start = 4.5
        zoom_end = 10.5
        zoom_level = zoom_start + (zoom_end - zoom_start) * (t / total_frames)

        save_frame_with_text_panel(
            fig,
            frame_name,
            run_param["animation"]["mapbox_access_token"],
            event_latitude,
            event_longitude,
            event_annotation,
            zoom_level,
            text_info,
            theme,
            logos,
        )

    compile_animation(frame_directory, f"{event_id}.gif", f"{event_id}.mp4", fps=2)


if __name__ == "__main__":
    logger = configure_logging()
    parser = argparse.ArgumentParser()
    parser.add_argument("--iganima_config", type=str, required=True)
    parser.add_argument("--event_id", type=str, required=True)
    args = parser.parse_args()
    logger.info("Arguments parsed", extra={"args": args.__dict__})
    main(args, logger)
