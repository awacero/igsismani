import sys
from pathlib import Path

current_dir = Path(__file__).parent.resolve()
sys.path.append(str(current_dir))

import plotly.graph_objects as go
import numpy as np
from moviepy.editor import ImageSequenceClip
import pandas as pd
import os
import glob
import iganima_utils as u


def clean_frame_directory(frame_dir):
    """Limpia el directorio de frames o lo crea si no existe."""
    if os.path.exists(frame_dir):
        for f in glob.glob(os.path.join(frame_dir, "frame*.png")):
            os.remove(f)
    else:
        os.makedirs(frame_dir)

def compile_animation(frame_dir, output_gif, output_mp4, fps=2):
    """Compila los frames en un GIF y un MP4."""
    frame_names = sorted(glob.glob(os.path.join(frame_dir, "*.png")))
    clip = ImageSequenceClip(frame_names, fps=0.001)
    clip.write_gif(output_gif)
    clip_video = ImageSequenceClip(frame_names, fps=fps)
    clip_video.write_videofile(output_mp4, codec='libx264')

def generate_circle(lat, lon, radius, points=100):
    """Genera coordenadas para un círculo alrededor de un punto."""
    lat_circle = []
    lon_circle = []
    for i in np.linspace(0, 2*np.pi, points):
        lat_circle.append(lat + radius * np.sin(i))
        lon_circle.append(lon + radius * np.cos(i))
    return lat_circle, lon_circle

def create_initial_point_frame(event_longitude, event_latitude, lon_stations, lat_stations, station_name_list_ordered):
    """Crea el frame inicial con solo un punto."""
    frame_data = [
        go.Scattermapbox(
            lon=[event_longitude],
            lat=[event_latitude],
            mode='markers',
            marker=dict(size=6, color='green'),
            showlegend=False,
            hoverinfo='skip'
        ),
        go.Scattermapbox(
            lon=lon_stations,
            lat=lat_stations,
            text=station_name_list_ordered,
            mode="markers+text",
            marker=dict(color=[], size=4, symbol="circle"),
            textposition='top left',
            showlegend=False,
            hoverinfo='text'
        )
    ]
    return frame_data

def create_line_growth_frame(t, POINT_FRAMES, LINE_GROWTH_FRAMES, MAX_LEN, lon_total, event_latitude, lon_stations, lat_stations, station_name_list_ordered):
    """Crea frames con línea creciente."""
    growth_t = t - POINT_FRAMES
    length = int(np.interp(growth_t, [1, LINE_GROWTH_FRAMES], [1, MAX_LEN]))
    mid = MAX_LEN // 2
    idx_range = slice(mid - length // 2, mid + length // 2)
    lon = lon_total[idx_range]
    lat = np.full_like(lon, event_latitude)

    frame_data = [
        go.Scattermapbox(
            lon=lon,
            lat=lat,
            mode='lines',
            line=dict(width=1, color='green'),
            showlegend=False,
            hoverinfo='skip'
        ),
        go.Scattermapbox(
            lon=lon_stations,
            lat=lat_stations,
            text=station_name_list_ordered,
            mode="markers+text",
            marker=dict(color=[], size=4, symbol="circle"),
            textposition='top left',
            showlegend=False,
            hoverinfo='text'
        )
    ]
    return frame_data

def create_sine_wave_frame(t, POINT_FRAMES, LINE_GROWTH_FRAMES, WAVE_GROWTH_FRAMES, waveform, vertical_scale, lon_total, event_latitude, lon_stations, lat_stations, station_name_list_ordered, is_growing=True):
    """Crea frames con onda sinusoidal creciente o decreciente."""
    if is_growing:
        wave_t = t - (POINT_FRAMES + LINE_GROWTH_FRAMES)
        alpha = min(1.0, wave_t / WAVE_GROWTH_FRAMES)
        waveform_scaled = alpha * waveform
    else:
        t_sine_shrink = t - (POINT_FRAMES + LINE_GROWTH_FRAMES + WAVE_GROWTH_FRAMES)
        fade = lambda f: max(0, 1 - f / WAVE_GROWTH_FRAMES)
        alpha = fade(t_sine_shrink)
        waveform_scaled = alpha * waveform

    lat = event_latitude + waveform_scaled * vertical_scale

    frame_data = [
        go.Scattermapbox(
            lon=lon_total,
            lat=lat,
            mode='lines',
            line=dict(width=1, color='green'),
            showlegend=False,
            hoverinfo='skip'
        ),
        go.Scattermapbox(
            lon=lon_stations,
            lat=lat_stations,
            text=station_name_list_ordered,
            mode="markers+text",
            marker=dict(color=[], size=4, symbol="circle"),
            textposition='top left',
            showlegend=False,
            hoverinfo='text'
        )
    ]
    return frame_data

def create_circle_frames(t, SEISMIC_WAVE_GROW, SEISMIC_WAVE_SHRINK, event_latitude, event_longitude, circle_colors, station_lat_lon_list_ordered, lon_stations, lat_stations, station_name_list_ordered, text_magnitude):
    """Crea frames con círculos concéntricos."""
    t_circle = t - (SEISMIC_WAVE_GROW + SEISMIC_WAVE_SHRINK)
    frame_data = []
    
    for radius, color in zip([t_circle * 0.1, t_circle * 0.07, t_circle * 0.05], circle_colors):
        lat_circ, lon_circ = generate_circle(event_latitude, event_longitude, radius)
        frame_data.append(
            go.Scattermapbox(
                lon=lon_circ,
                lat=lat_circ,
                mode="lines",
                line=dict(width=2, color=color),
                showlegend=False,
            )
        )

    station_colors = []
    for lat_station, lon_station in station_lat_lon_list_ordered:
        is_inside_circle = False
        for radius in [t_circle * 0.1, t_circle * 0.07, t_circle * 0.05]:
            distance = ((lat_station - event_latitude)**2 + (lon_station - event_longitude)**2)**0.5
            if distance <= radius:
                is_inside_circle = True
                break
        color = "Red" if is_inside_circle else "Gray"
        station_colors.append(color)

    frame_data.extend([
        go.Scattermapbox(
            lon=lon_stations,
            lat=lat_stations,
            text=station_name_list_ordered,
            mode="markers+text",
            marker=dict(color=station_colors, size=4, symbol="circle"),
            textposition='top left',
            showlegend=False,
            hoverinfo='text'
        ),
        go.Scattermapbox(
            lon=[event_longitude],
            lat=[event_latitude],
            text=text_magnitude,
            mode='markers+text',
            marker=dict(color='white', size=4, symbol="circle"),
            textposition='top center',
            textfont=dict(size=30),
            showlegend=False,
            hoverinfo='text'
        )
    ])
    return frame_data

def save_frame(fig, frame_name, mapbox_access_token, event_latitude, event_longitude, event_annotation, zoom_level):
    """Guarda un frame como imagen PNG."""

    import math

    # Parámetros del círculo
    circle_radius_km = 7  # puedes ajustar el tamaño
    circle_points = 100
    earth_radius_km = 6371

    circle_lat = []
    circle_lon = []

    for i in range(circle_points):
        angle = 2 * np.pi * i / circle_points
        d = circle_radius_km / earth_radius_km
        lat = math.asin(math.sin(math.radians(event_latitude)) * math.cos(d) +
                        math.cos(math.radians(event_latitude)) * math.sin(d) * math.cos(angle))
        lon = math.radians(event_longitude) + math.atan2(
            math.sin(angle) * math.sin(d) * math.cos(math.radians(event_latitude)),
            math.cos(d) - math.sin(math.radians(event_latitude)) * math.sin(lat))
        circle_lat.append(math.degrees(lat))
        circle_lon.append(math.degrees(lon))

    fig.add_trace(go.Scattermapbox(
        lat=circle_lat,
        lon=circle_lon,
        mode='lines',
        line=dict(width=2, color='red'),
        fill='toself',
        opacity=0.3,
        name='Zona epicentral',
        showlegend=False
    ))
   




    fig.update_layout(
        mapbox=dict(
            accesstoken=mapbox_access_token,
            center=dict(lat=event_latitude, lon=event_longitude),
            zoom=zoom_level,
            style='light'
        ),
        images=[dict(
            source="https://raw.githubusercontent.com/awacero/grafana_plotly/main/images/logo_igepn.png",
            xref="paper",
            yref="paper",
            x=0,
            y=1,
            sizex=0.20,
            sizey=0.10,
            sizing="contain",
            opacity=1.0,
        )],
        annotations=[
            dict(
                xref="paper",
                yref="paper",
                x=1,
                y=1,
                text=event_annotation,
                showarrow=False,
                font=dict(size=14, color="black"),
                bgcolor="white",
                bordercolor="black",
                borderwidth=2,
                borderpad=4,
                opacity=0.7
            )
        ],
        margin=dict(l=10, r=10, t=10, b=10),
        width=666,
        height=666
    )
    fig.write_image(frame_name)
