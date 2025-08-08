# IGANIMA Animation Tool – Engineering Requirements Specification

## Overview
IGANIMA is a command-line tool for generating animated visualizations of seismic
events. It retrieves event and station information from an FDSN web service,
creates Plotly frames illustrating wave propagation and station response, and
produces GIF and MP4 animations.

## Functional Requirements
1. **Logging configuration**
   - The application configures logging using a `logging.ini` file during
     startup【F:run_iganima.py†L60-L67】.

2. **Command-line interface**
   - Users must supply the path to a configuration file and an event identifier
     via `--iganima_config` and `--event_id` arguments【F:run_iganima.py†L302-L307】.

3. **Configuration handling**
   - The tool reads INI-style configuration files to obtain FDSN server
     settings and animation options【F:run_iganima.py†L24-L33】【F:run_iganima.py†L95-L106】.
   - FDSN server connection details are read from a JSON file with environment
     variable expansion【F:run_iganima.py†L36-L55】.

4. **Data acquisition**
   - The system connects to an FDSN server to fetch event data by ID and load
     station inventory information【F:run_iganima.py†L121-L170】.
   - Utilities include functions to open JSON configs, query events, and attach
     coordinates to traces【F:iganima/iganima_utils.py†L22-L50】【F:iganima/iganima_utils.py†L236-L253】.

5. **Event processing**
   - Event and pick information are converted to Pandas DataFrames for further
     processing【F:iganima/iganima_utils.py†L67-L87】【F:iganima/iganima_utils.py†L383-L467】.
   - Stations are sorted by distance to the event for visualization
     preparation【F:run_iganima.py†L173-L192】.

6. **Animation generation**
   - Frames are created depicting the initial epicenter, line growth, sine-wave
     propagation, and concentric circles that interact with station markers
     【F:iganima/iganima_functions.py†L16-L170】【F:run_iganima.py†L200-L243】.
   - Individual frames are saved with event annotations and compiled into GIF
     and MP4 animations【F:iganima/iganima_functions.py†L185-L262】【F:iganima/iganima_functions.py†L24-L30】.

7. **Map rendering**
   - Each frame uses a Mapbox base map and includes an epicentral zone overlay
     with configurable zoom levels【F:iganima/iganima_functions.py†L209-L261】.

8. **Color mapping**
   - Circle and waveform colors are determined by a `get_circle_color` module.
     This module is expected to provide color schemes based on event intensity
     but is currently absent from the repository【F:run_iganima.py†L200-L207】.

## Non-functional Requirements
- **Dependencies:** The application relies on external libraries including
  `pandas`, `numpy`, `plotly`, `moviepy`, and `obspy`.
- **Environment:** A Mapbox access token is required for map rendering. Paths in
  configuration files may contain environment variables.
- **Output:** Generated frames and compiled animations are written to a
  directory specified in the configuration.
- **Error handling:** Exceptions are logged and re-raised to ensure failures are
  visible during batch runs【F:run_iganima.py†L72-L173】.

## Future Considerations
- Implement the missing `get_circle_color` module to provide consistent color
  mappings based on seismic intensity.
- Add automated tests or dependency checks to facilitate continuous
  integration.
