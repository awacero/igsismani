# IGANIMA Animation Toolkit

This repository contains utilities for generating seismic information animations. 


The following sections describe how to install, configure and execute the code. 

## Prerequisites

### Libraries
* **Python** 3.11
* **Plotly**
* **Manim**
* **OpenCV** 
* **Obspy**

### Data

* A **Mapbox access token** to render Mapbox tiles inside Plotly figures.
* Access credentials to an **FDSN web service** that provides seismic events and waveforms.

## Environment installation

1. Create and activate a conda environment:

   ```bash
    conda create -n igsismani python=3.11
    conda activate igsismani
    conda install manim plotly opencv obspy 
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
mapbox_access_token = TOKEN_MAPBOX
frames_out = PROJECT_PATH/igsismani/tmp/frames_out
frames_in = PROJECT_PATH/igsismani/config/
video_out = PROJECT_PATH/igsismani/tmp/
frames_number = 20
fps= 3
number_stations = 10


```

### FDSN server catalog

`server_config_file` must point to a JSON document describing the available servers. The key referenced by `server_id` is used to fetch the host and port.

```json
{
  "FDSN":{
          "name":"FDSN",
          "server_ip":"0.0.0.0",
          "port":"8080"
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
conda activate igsismani 

python run_igsismani.py --iganima_config ./config/iganima.cfg --event_id igepn2023dcsb
```

The frames are stored in a temporary directory and the resulting MP4 videos on `video_out`


### 2. Ejecutar el servicio 

```bash 
conda activate igsismani

$ python run_api_service.py  


```

#### 2.1 Arrancar la creación de un evento 

```javascript
curl http://192.168.1.180:8000/tickets?event_id=igepn2026dzcr 

```

### 3. Create the video going to the following  web 

http://192.168.1.180:8000/ui
