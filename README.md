# IGANIMA Animation Toolkit

This repository contains utilities for generating seismic information animations used by the IGANIMA project. There are two primary animation workflows:

* **Plotly-based map animations** with styled textual overlays (`run_iganima.py` and `run_iganima_text_panel.py`).
* **Manim-based information bars** for quick social media updates (`run_iganima_manim_panel.py`).

The following sections describe how to install the Python environment, configure the required services, and run each workflow.

## Prerequisites

* **Python** 3.9 or newer (3.10 recommended).
* **FFmpeg** for encoding GIF/MP4 files (required by MoviePy and Manim).
* **Cairo/Pango** stack recommended by [Manim's installation guide](https://docs.manim.community/en/stable/installation.html) for video rendering.
* A **Mapbox access token** to render Mapbox tiles inside Plotly figures.
* Access credentials to an **FDSN web service** that provides seismic events and waveforms.

## Python installation

1. Create and activate a virtual environment:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

2. Upgrade pip and install the Python dependencies used across the scripts:

   ```bash
   pip install --upgrade pip
   pip install manim pandas numpy plotly moviepy obspy pytz
   ```

   *Depending on your platform, Manim might pull additional system packages. Follow the official Manim instructions if the installation reports missing libraries.*

3. (Optional) To export Plotly figures as static images you may also need `kaleido`:

   ```bash
   pip install kaleido
   ```

## Configuration

### IGANIMA runtime configuration file

`run_iganima.py` and `run_iganima_text_panel.py` expect an INI configuration file passed through the `--iganima_config` flag. The file must provide the FDSN connection info, paths to auxiliary assets, and animation settings.

Example `config/iganima.ini`:

```ini
[fdsn]
server_id = igepn
server_config_file = ./config/fdsn_servers.json
xml_inventory_file = ./config/stations.xml

[animation]
mapbox_access_token = pk.your-mapbox-token
frames_number = 120
number_stations = 12
frame_directory = ./frames

# Optional overrides for the styled text panel
text_panel_header_title = INFORMATIVO SISMO
text_panel_header_subtitle = Actualización
text_panel_footer_text = Fuente: IG-EPN
text_panel_logos_json = ./config/text_panel_logos.json
```

### FDSN server catalog

`server_config_file` must point to a JSON document describing the available servers. The key referenced by `server_id` is used to fetch the host and port.

```json
{
  "igepn": {
    "server_ip": "fdsn.example.org",
    "port": 8080
  }
}
```

### Mapbox access token

Store your Mapbox token inside the `[animation]` section as `mapbox_access_token`. You can generate tokens from the Mapbox dashboard. The Plotly animations will fail without a valid token.

### Logging configuration

`run_iganima.py` and `run_iganima_text_panel.py` load their logging settings from `./config/logging.ini`. Provide a standard logging configuration file if you want customized log formatting. A minimal example:

```ini
[loggers]
keys=root

[handlers]
keys=console

[formatters]
keys=simple

[logger_root]
level=INFO
handlers=console

[handler_console]
class=StreamHandler
level=INFO
formatter=simple
destination=stdout

[formatter_simple]
format=%(asctime)s - %(levelname)s - %(name)s - %(message)s
```

## Running the scripts

### 1. Legacy Plotly animation (`run_iganima.py`)

This script reproduces the original animation with the default overlay.

```bash
python run_iganima.py --iganima_config ./config/iganima.ini --event_id igepn2024abcd
```

The frames are exported to the directory configured in `[animation] frame_directory`, and the resulting GIF/MP4 files are written next to it.

### 2. Styled text panel animation (`run_iganima_text_panel.py`)

This entry point reuses the Plotly frames but renders the textual panel described in `iganima/iganima_text_panel.py`.

```bash
python run_iganima_text_panel.py --iganima_config ./config/iganima.ini --event_id igepn2024abcd
```

Additional `text_panel_*` keys inside the INI file let you override colors, labels, logos, and hashtags without modifying the code.

### 3. Manim information bar (`run_iganima_manim_panel.py`)

Use this command to render the Manim-based info bar animation. It does **not** require the IGANIMA configuration file; instead you control the output via CLI flags.

```bash
python run_iganima_manim_panel.py \
  --text "Magnitud 4.8" \
  --bar-color "#3287C8" \
  --text-color "#FFFFFF" \
  --font-size 36 \
  --output ./output/info_animation.mp4
```

You can also customize the canvas size with `--pixel-size WIDTH HEIGHT` and Manim's logical frame dimensions with `--frame-size WIDTH HEIGHT`.

## Output

* Plotly-based scripts create numbered PNG frames in the configured directory and compile them into both GIF and MP4 animations.
* The Manim runner exports a single MP4 file (and Manim's default auxiliary files) in the requested output directory.

## Troubleshooting

* Ensure FFmpeg is on your system `PATH`; MoviePy and Manim rely on it for video encoding.
* If Mapbox tiles fail to load, verify the token and that the machine has network access.
* When connecting to the FDSN service, confirm the host, port, and any firewall requirements; connection failures raise descriptive exceptions in the console logs.

