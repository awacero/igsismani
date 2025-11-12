"""Utilities to render seismic text overlays following the IGANIMA style."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence

import plotly.graph_objects as go


@dataclass
class PanelTheme:
    """Visual configuration for the seismic text panel.

    The defaults were chosen to resemble the layout shared in the
    requirements: a dark background with cyan/blue cards and yellow accents.
    """

    panel_background: str = "#02142B"
    header_background: str = "#0B5ED7"
    block_primary: str = "#1282F3"
    block_secondary: str = "#0F6BD7"
    block_border: str = "rgba(255, 255, 255, 0.22)"
    accent_color: str = "#FFC857"
    text_primary: str = "#FFFFFF"
    text_secondary: str = "#D7EBFF"
    text_muted: str = "#9CC9FF"
    map_style: str = "light"
    font_family: str = "'Montserrat', 'Open Sans', 'Arial', sans-serif"
    export_scale: int = 2
    header_text_color: str = "#FFFFFF"
    header_subtext_color: str = "#D7EBFF"
    footer_text_color: str = "#D7EBFF"
    marker_text_color: str = "#041527"
    marker_border_color: str = "#FFFFFF"


@dataclass
class SeismicTextInfo:
    """Semantic content displayed inside the styled panel."""

    magnitude_value: str
    depth_text: str
    location_text: str
    province_text: str
    status_text: str
    date_text: str
    magnitude_title: str = "Magnitud"
    magnitude_subtitle: str = ""
    depth_title: str = "Profundidad"
    depth_subtitle: str = ""
    location_title: str = "Localizado"
    location_subtitle: str = ""
    province_title: str = "Provincia"
    province_subtitle: str = ""
    status_title: str = "IGepnEcuador"
    date_title: str = "Fecha"
    header_title: str = "INFORMATIVO SISMO"
    header_subtitle: str = "Actualización"
    footer_text: str = ""
    hashtags_text: str = ""
    show_magnitude_marker: bool = True
    header_icon_text: Optional[str] = None
    header_icon_background: str = "#12B4FF"
    magnitude_marker_color: str = "#FF5A5F"

    @classmethod
    def from_event_dict(
        cls,
        event_dict: dict,
        *,
        distance_text: str,
        province_text: str,
        status_text: str,
        hashtags_text: str = "",
        header_title: str = "INFORMATIVO SISMO",
        header_subtitle: str = "Actualización",
    ) -> "SeismicTextInfo":
        """Convenience helper to populate the panel from the existing event dict."""

        magnitude = f"{event_dict['magnitude']}"
        depth = f"{event_dict['depth']} km de profundidad"
        date_text = event_dict.get("time_local", "")

        return cls(
            magnitude_value=magnitude,
            depth_text=depth,
            location_text=distance_text,
            province_text=province_text,
            status_text=status_text,
            date_text=date_text,
            hashtags_text=hashtags_text,
            header_title=header_title,
            header_subtitle=header_subtitle,
        )


def save_frame_with_text_panel(
    fig: go.Figure,
    frame_name: str,
    mapbox_access_token: str,
    event_latitude: float,
    event_longitude: float,
    event_annotation: str,
    zoom_level: float,
    text_info: SeismicTextInfo,
    theme: Optional[PanelTheme] = None,
    logos: Optional[Sequence[dict]] = None,
) -> None:
    """Persist a figure using the new textual style."""

    theme = theme or PanelTheme()

    _prepare_map_layout(
        fig,
        mapbox_access_token,
        event_latitude,
        event_longitude,
        zoom_level,
        theme,
    )
    _add_logo_images(fig, logos)
    _apply_event_annotation(fig, event_annotation, theme)

    if text_info.show_magnitude_marker:
        _add_magnitude_marker(fig, event_longitude, event_latitude, text_info, theme)

    _apply_text_panel(fig, text_info, theme)
    fig.write_image(frame_name, scale=theme.export_scale)


def _prepare_map_layout(
    fig: go.Figure,
    mapbox_access_token: str,
    event_latitude: float,
    event_longitude: float,
    zoom_level: float,
    theme: PanelTheme,
) -> None:
    fig.update_layout(
        mapbox=dict(
            accesstoken=mapbox_access_token,
            center=dict(lat=event_latitude, lon=event_longitude),
            zoom=zoom_level,
            style=theme.map_style,
            domain=dict(x=[0.0, 1.0], y=[0.48, 1.0]),
        ),
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor=theme.panel_background,
        plot_bgcolor="rgba(0, 0, 0, 0)",
        autosize=False,
        width=666,
        height=1024,
        font=dict(color=theme.text_primary, family=theme.font_family),
    )


def _add_logo_images(fig: go.Figure, logos: Optional[Sequence[dict]]) -> None:
    current_images = list(fig.layout.images) if fig.layout.images else []
    if logos is None:
        logos = [
            dict(
                source="https://raw.githubusercontent.com/awacero/grafana_plotly/main/images/logo_igepn.png",
                xref="paper",
                yref="paper",
                x=0.02,
                y=0.99,
                sizex=0.18,
                sizey=0.1,
                xanchor="left",
                yanchor="top",
                sizing="contain",
                opacity=1.0,
                layer="above",
            )
        ]
    fig.update_layout(images=current_images + list(logos))


def _apply_event_annotation(fig: go.Figure, event_annotation: str, theme: PanelTheme) -> None:
    if not event_annotation:
        return

    annotations = list(fig.layout.annotations) if fig.layout.annotations else []
    annotations.append(
        dict(
            xref="paper",
            yref="paper",
            x=0.98,
            y=0.97,
            text=event_annotation,
            showarrow=False,
            align="right",
            font=dict(size=14, color=theme.marker_text_color, family=theme.font_family),
            bgcolor="rgba(255, 255, 255, 0.92)",
            bordercolor="rgba(0, 0, 0, 0.35)",
            borderwidth=1,
            borderpad=6,
            opacity=0.95,
        )
    )
    fig.update_layout(annotations=annotations)


def _add_magnitude_marker(
    fig: go.Figure,
    event_longitude: float,
    event_latitude: float,
    text_info: SeismicTextInfo,
    theme: PanelTheme,
) -> None:
    fig.add_trace(
        go.Scattermapbox(
            lon=[event_longitude],
            lat=[event_latitude],
            mode="markers+text",
            marker=dict(
                size=48,
                color=text_info.magnitude_marker_color,
                opacity=0.92,
                line=dict(color=theme.marker_border_color, width=4),
            ),
            text=[text_info.magnitude_value],
            textfont=dict(size=20, color=theme.marker_text_color, family=theme.font_family),
            textposition="middle center",
            hoverinfo="skip",
            showlegend=False,
        )
    )


def _apply_text_panel(fig: go.Figure, text_info: SeismicTextInfo, theme: PanelTheme) -> None:
    panel_shapes: List[dict] = []
    annotations: List[dict] = list(fig.layout.annotations) if fig.layout.annotations else []

    # Base panel background
    panel_shapes.append(
        dict(
            type="rect",
            xref="paper",
            yref="paper",
            x0=0.0,
            x1=1.0,
            y0=0.0,
            y1=0.48,
            fillcolor=theme.panel_background,
            layer="below",
            line=dict(width=0),
        )
    )

    # Header banner
    panel_shapes.append(
        dict(
            type="rect",
            xref="paper",
            yref="paper",
            x0=0.03,
            x1=0.97,
            y0=0.40,
            y1=0.46,
            fillcolor=theme.header_background,
            layer="below",
            line=dict(width=0),
        )
    )

    if text_info.header_icon_text:
        panel_shapes.append(
            dict(
                type="circle",
                xref="paper",
                yref="paper",
                x0=0.05,
                x1=0.11,
                y0=0.41,
                y1=0.47,
                fillcolor=text_info.header_icon_background,
                line=dict(width=0),
            )
        )
        annotations.append(
            dict(
                xref="paper",
                yref="paper",
                x=0.08,
                y=0.44,
                text=f"<b>{text_info.header_icon_text}</b>",
                showarrow=False,
                font=dict(size=18, color=theme.text_primary, family=theme.font_family),
            )
        )

    annotations.append(
        dict(
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.435,
            text=f"<b>{text_info.header_title}</b>",
            showarrow=False,
            font=dict(size=24, color=theme.header_text_color, family=theme.font_family),
        )
    )

    if text_info.header_subtitle:
        annotations.append(
            dict(
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.405,
                text=text_info.header_subtitle,
                showarrow=False,
                font=dict(size=14, color=theme.header_subtext_color, family=theme.font_family),
            )
        )

    block_specs = [
        dict(
            title=text_info.magnitude_title,
            value=text_info.magnitude_value,
            subtitle=text_info.magnitude_subtitle,
            y0=0.31,
            y1=0.37,
        ),
        dict(
            title=text_info.depth_title,
            value=text_info.depth_text,
            subtitle=text_info.depth_subtitle,
            y0=0.23,
            y1=0.29,
        ),
        dict(
            title=text_info.location_title,
            value=text_info.location_text,
            subtitle=text_info.location_subtitle,
            y0=0.15,
            y1=0.21,
        ),
        dict(
            title=text_info.province_title,
            value=text_info.province_text,
            subtitle=text_info.province_subtitle,
            y0=0.07,
            y1=0.13,
        ),
    ]

    for block in block_specs:
        panel_shapes.extend(
            _build_block_shapes(
                block["y0"],
                block["y1"],
                theme.block_primary,
                theme.block_secondary,
                theme.block_border,
            )
        )
        annotations.extend(
            _build_block_annotations(
                block["title"],
                block["value"],
                block["subtitle"],
                block["y0"],
                block["y1"],
                theme,
            )
        )

    # Status and footer rows
    annotations.append(
        dict(
            xref="paper",
            yref="paper",
            x=0.05,
            y=0.038,
            text=f"<b>{text_info.status_title}</b> {text_info.status_text}",
            showarrow=False,
            xanchor="left",
            font=dict(size=13, color=theme.text_primary, family=theme.font_family),
        )
    )

    annotations.append(
        dict(
            xref="paper",
            yref="paper",
            x=0.95,
            y=0.038,
            text=f"<b>{text_info.date_title}:</b> {text_info.date_text}",
            showarrow=False,
            xanchor="right",
            font=dict(size=13, color=theme.text_primary, family=theme.font_family),
        )
    )

    if text_info.footer_text or text_info.hashtags_text:
        footer_text_parts = [text_info.footer_text, text_info.hashtags_text]
        footer_text = " \u2022 ".join([part for part in footer_text_parts if part])
        annotations.append(
            dict(
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.012,
                text=footer_text,
                showarrow=False,
                font=dict(size=12, color=theme.footer_text_color, family=theme.font_family),
            )
        )

    existing_shapes = list(fig.layout.shapes) if fig.layout.shapes else []
    fig.update_layout(shapes=existing_shapes + panel_shapes, annotations=annotations)


def _build_block_shapes(
    y0: float,
    y1: float,
    primary_color: str,
    secondary_color: str,
    border_color: str,
) -> List[dict]:
    shapes: List[dict] = []
    shapes.append(
        dict(
            type="rect",
            xref="paper",
            yref="paper",
            x0=0.03,
            x1=0.97,
            y0=y0,
            y1=y1,
            fillcolor=primary_color,
            layer="below",
            line=dict(color=border_color, width=1),
        )
    )
    shapes.append(
        dict(
            type="rect",
            xref="paper",
            yref="paper",
            x0=0.03,
            x1=0.55,
            y0=y0,
            y1=y1,
            fillcolor=secondary_color,
            layer="below",
            line=dict(width=0),
        )
    )
    return shapes


def _build_block_annotations(
    title: str,
    value: str,
    subtitle: str,
    y0: float,
    y1: float,
    theme: PanelTheme,
) -> List[dict]:
    annotations: List[dict] = []
    center_y = (y0 + y1) / 2
    block_height = y1 - y0

    title_y = y1 - block_height * 0.28
    value_y = center_y
    subtitle_y = y0 + block_height * 0.18

    annotations.append(
        dict(
            xref="paper",
            yref="paper",
            x=0.08,
            y=title_y,
            text=title,
            showarrow=False,
            xanchor="left",
            font=dict(size=13, color=theme.text_secondary, family=theme.font_family),
        )
    )

    annotations.append(
        dict(
            xref="paper",
            yref="paper",
            x=0.08,
            y=value_y,
            text=f"<b>{value}</b>",
            showarrow=False,
            xanchor="left",
            font=dict(size=22, color=theme.text_primary, family=theme.font_family),
        )
    )

    if subtitle:
        annotations.append(
            dict(
                xref="paper",
                yref="paper",
                x=0.08,
                y=subtitle_y,
                text=subtitle,
                showarrow=False,
                xanchor="left",
                font=dict(size=12, color=theme.text_muted, family=theme.font_family),
            )
        )

    return annotations
