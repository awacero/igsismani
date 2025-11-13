# IGANIMA Animation Toolkit

This repository contains utilities for generating seismic information animations. 


The following sections describe how to install, configure and execute the code. 

## Prerequisites

* **Python** 3.13.
* **OpenCV** 
* **Plotly**


* **FFmpeg** for encoding GIF/MP4 files (required by MoviePy and Manim).
* **Cairo/Pango** stack recommended by [Manim's installation guide](https://docs.manim.community/en/stable/installation.html) for video rendering.
* A **Mapbox access token** to render Mapbox tiles inside Plotly figures.
* Access credentials to an **FDSN web service** that provides seismic events and waveforms.

## Environment installation

1. Create and activate a conda environment:

   ```bash
    conda create -n igsismani python=3.13
    conda activate igsismani
    conda install obspy plotly manim 
   ```


## Configuration

### IGANIMA runtime configuration file
The running script expect an CFG configuration file passed through the `--iganima_config` flag. The file must provide the FDSN connection info, paths to auxiliary assets, and animation settings.

Example `config/iganima.cfg`:

```ini
[fdsn]
server_id = FDSN
server_config_file = $HOME/igsismani/config/server_configuration.json
xml_inventory_file =  $HOME/igsismani/data/igepn_LA.xml
nearest_url = http://DARCY.PEMBERLEY:1775/get_nearest_city?
nearest_token = mgoolilf

[animation]
mapbox_access_token = TOKEN_MAPBOX_
frames_map = $HOME/igsismani/frames_map
frames_info = $HOME/igsismani/frames_info
frames_number = 20
fps= 4
number_stations = 10

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

The modules use a standard logging configuration file if you want customized log formatting. A minimal example file is supplied. 



## Running the scripts

### 1. Legacy Plotly animation (`run_iganima.py`)

This script reproduces the original animation with the default overlay.

```bash
python run_igsismani.py --iganima_config ./config/iganima.cfg --event_id igepn2023dcsb
```

The frames are exported to the directory configured in `[animation] frames_map and frames_info`, and the resulting MP4 videos on `video_out`


