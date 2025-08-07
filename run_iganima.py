
import pandas as pd
import numpy as np

import logging
import logging.config
import argparse 
import configparser

from iganima import iganima_utils as u
from iganima.iganima_functions import *
from iganima import get_circle_color


import json
from obspy import read_inventory



pd.set_option('display.max_colwidth', None)
pd.set_option('display.max_columns', None)


def read_parameters(file_path):
    """
    Read a configuration text file
    
    :param string file_path: path to configuration text file
    :returns: dict: dict of a parser object
    """
    parser=configparser.ConfigParser()
    parser.read(file_path)
    return parser._sections


def load_config_from_file(json_file_path):
    """
    Read a JSON configuration file and return it as a dictionary.
    Expands environment variables in string values.
    """
    with open(os.path.expandvars(json_file_path), 'r') as f:
        config_data = json.load(f)

    # Expand env vars recursively (optional but useful)
    def expand_env(value):
        if isinstance(value, str):
            return os.path.expandvars(value)
        elif isinstance(value, dict):
            return {k: expand_env(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [expand_env(v) for v in value]
        else:
            return value

    return expand_env(config_data)




def configure_logging():

    print("Start of logging configuration")
    logging.config.fileConfig(Path("./config/",'logging.ini'), disable_existing_loggers=True)
    logger = logging.getLogger(__name__)

    logger.info(f"Logger configured was: {logging.getLogger().handlers}")
    return logger


def main(args):

    try:

        configuration_file = args.iganima_config
        event_id = args.event_id
    except Exception as e:
        logger.error(f"Error charging parameters from args: {e}")
        raise Exception(f"Error charging parameters from args: {e}")

    try:
        logger.info(f"Check if configuration file {configuration_file} exists")
        if os.path.isfile(configuration_file):
            logger.info(f"Config file: {configuration_file} OK.Continue")
    except Exception as e:
        logger.error(f"Error reading configuration  file: {e}" )
        raise Exception(f"Error reading configuration file: {e}" )

    try:
        logger.info(f"Read configuration file {configuration_file}")
        run_param = read_parameters(configuration_file)
    except Exception as e:
        logger.error(f"Error reading configuration sets in file: {e}")
        raise Exception(f"Error reading configuration file: {e}")

    try:
        logger.info(f"Loaded configuration file {configuration_file}")
        
        fdsn_id = run_param['fdsn']['server_id']
        mseed_server_config_file = run_param['fdsn']['server_config_file']
        xml_inventory_file = run_param['fdsn']['xml_inventory_file']

        mapbox_access_token = run_param["animation"]["mapbox_access_token"]
        FRAMES_NUMBER = int(run_param["animation"]["frames_number"])
        number_stations = run_param["animation"]["number_stations"]
        frame_directory = run_param["animation"]["frame_directory"]

    except Exception as e:
        logger.error(f"Error loading configuration sets in file: {e}")
        raise Exception(f"Error loading configuration file: {e}")

    try:
        logger.info(f"Read miniseed server file {mseed_server_config_file}")
        ###mseed_server_param = u.read_config_file(mseed_server_config_file)
        mseed_server_param = load_config_from_file(mseed_server_config_file)

        print(f"##### mseed server {mseed_server_param}")
    except Exception as e:
        logger.error(f"Error reading configuration file: {e}")
        raise Exception(f"Error reading configuration file: {e}")

    try:
        logger.info(f"Get fdsn server info ")
        
        fdsn_server_ip = mseed_server_param[fdsn_id]["server_ip"]
        fdsn_server_port = mseed_server_param[fdsn_id]["port"]

    except Exception as e:
        logger.error(f"Error reading miniseed server file: {e}")
        raise Exception(f"Error reading miniseed server file: {e}")


    try:
        logger.info(f"Connect to fdsn server info ")
        fdsn_client = u.connect_fdsn(fdsn_server_ip, fdsn_server_port)
    except Exception as e:
        logger.error(f"Error connecting configuration file: {e}")
        raise Exception(f"Error connecting configuration file: {e}")


    try:
        logger.info(f"Clean frame directory")
        clean_frame_directory(frame_directory)
    except Exception as e:
        logger.error(f"Error in cleaning frame directory: {e}")
        raise Exception(f"Error in cleaning frame directory: {e}")
    
    try:
        logger.info(f"Get event info")
        # Conexión y obtención de datos del evento

        event_inventory = u.get_event_by_id(fdsn_client, event_id)
        event_dict = u.event2dict(event_inventory[0])

        # Información del evento para la anotación
        event_annotation = f"""ID: {event_dict['event_id']} {event_dict['status']}<br>{event_dict['time_local']} Hora Local<br>Prof. {event_dict['depth']} Km.  Magnitud:  {event_dict['magnitude']}"""

        # Parámetros del evento
        event_latitude = event_dict['latitude']
        event_longitude = event_dict['longitude']
        intensity = event_dict['magnitude']
    except Exception as e:
        logger.error(f"Error getting event info {e}")
        raise Exception(f"Error getting event info: {e}")

    try:
        logger.info(f"Read inventory file ")
        # Carga de inventario y datos de estaciones
        inventory = read_inventory(xml_inventory_file)
    except Exception as e:
        logger.error(f"Error reading inventory file: {e}")
        raise Exception(f"Error reading inventory file: {e}")


    try:
        logger.info(f"Process event information")
        event_df = u.event2dataframe(event_inventory)
        picks_df = u.picks2dataframe(event_inventory)
        stations_set = set(picks_df[:].apply(lambda row: f"{row['network']}.{row['station']}", axis=1))

        stations_dict, stations_list = u.create_stations_dict(stations_set, inventory)

        # Procesamiento de estaciones
        station_list_temp = []
        for station_dict in stations_list:
            station_dict = u.attach_distance_dict(station_dict, event_inventory[0])
            station_list_temp.append(station_dict)

        station_list_sorted = sorted(station_list_temp, key=lambda x: x['distance'])

        # Preparación de datos para visualización
        station_lat_lon_list_ordered = [(station['latitude'], station['longitude']) for station in station_list_sorted]
        station_name_list_ordered = [(station['station_id'].split('.')[1]) for station in station_list_sorted]
        lat_stations, lon_stations = zip(*station_lat_lon_list_ordered)

    except Exception as e:
        logger.error(f"Error processing event information: {e}")
        raise Exception(f"Error processing event information: {e}")


    try:
        logger.info(f"Create the animation")
        text_magnitude = [f'{intensity}']
        circle_colors = get_circle_color.get_colors_from_intensity(intensity)
        sinewave_color = get_circle_color.get_color_from_intensity(intensity)

        # Configuración de la onda sísmica
        vertical_scale = get_circle_color.get_value_from_intensity(intensity)
        horizontal_scale = 0.3
        seismic_wave_time = np.linspace(-1, 1, 100)
        lon_total = np.linspace(event_longitude - horizontal_scale, event_longitude + horizontal_scale, len(seismic_wave_time))
        waveform = np.exp(-seismic_wave_time**2) * np.sin(13 * seismic_wave_time)

        # Parámetros de animación
        MAX_LEN = len(seismic_wave_time)
        SEISMIC_WAVE_GROW = 10
        SEISMIC_WAVE_SHRINK = 10
        LINE_2_POINT_FRAMES = 5
        POINT_FRAMES = 2
        LINE_GROWTH_FRAMES = 3
        WAVE_GROWTH_FRAMES = 5

        # Generación de frames
        frames = []
        frame_names = []

        for t in range(1, FRAMES_NUMBER + 1):
            frame_data = []

            if t <= POINT_FRAMES + 1:
                frame_data = create_initial_point_frame(event_longitude, event_latitude, lon_stations, lat_stations, station_name_list_ordered)
            elif POINT_FRAMES - 1 <= t <= POINT_FRAMES + LINE_GROWTH_FRAMES:
                frame_data = create_line_growth_frame(t, POINT_FRAMES, LINE_GROWTH_FRAMES, MAX_LEN, lon_total, event_latitude, lon_stations, lat_stations, station_name_list_ordered)
            elif POINT_FRAMES + LINE_GROWTH_FRAMES <= t < POINT_FRAMES + LINE_GROWTH_FRAMES + WAVE_GROWTH_FRAMES:
                frame_data = create_sine_wave_frame(t, POINT_FRAMES, LINE_GROWTH_FRAMES, WAVE_GROWTH_FRAMES, waveform, vertical_scale, lon_total, event_latitude, lon_stations, lat_stations, station_name_list_ordered, is_growing=True)
            elif POINT_FRAMES + LINE_GROWTH_FRAMES + WAVE_GROWTH_FRAMES <= t <= POINT_FRAMES + LINE_GROWTH_FRAMES + WAVE_GROWTH_FRAMES*2:
                frame_data = create_sine_wave_frame(t, POINT_FRAMES, LINE_GROWTH_FRAMES, WAVE_GROWTH_FRAMES, waveform, vertical_scale, lon_total, event_latitude, lon_stations, lat_stations, station_name_list_ordered, is_growing=False)
            elif POINT_FRAMES + LINE_GROWTH_FRAMES + WAVE_GROWTH_FRAMES*2 <= t <= POINT_FRAMES + LINE_GROWTH_FRAMES*2 + WAVE_GROWTH_FRAMES*2:
                # Fase de reducción de línea (similar a create_line_growth_frame pero inversa)
                shrink_time = t - (POINT_FRAMES + LINE_GROWTH_FRAMES + WAVE_GROWTH_FRAMES*2)
                length = int(np.interp(shrink_time, [0, LINE_2_POINT_FRAMES], [MAX_LEN, 1]))
                mid = MAX_LEN // 2
                idx_range = slice(mid - length//2, mid + length//2)
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
            elif t > POINT_FRAMES + LINE_GROWTH_FRAMES*2 + WAVE_GROWTH_FRAMES*2:
                frame_data = create_circle_frames(t, SEISMIC_WAVE_GROW, SEISMIC_WAVE_SHRINK, event_latitude, event_longitude, circle_colors, station_lat_lon_list_ordered, lon_stations, lat_stations, station_name_list_ordered, text_magnitude)

            # Guardar el frame
            frame_name = f'frames/frame_{t:03}.png'
            frame_names.append(frame_name)
            fig = go.Figure(data=frame_data)
            zoom_start = 4.5
            zoom_end = 10.5
            zoom_level = zoom_start + (zoom_end - zoom_start) * (t / FRAMES_NUMBER)
            save_frame(fig, frame_name, mapbox_access_token, event_latitude, event_longitude, event_annotation,zoom_level)

        # Compilar la animación
        compile_animation("./frames", f"{event_id}.gif", f"{event_id}.mp4", fps=2)


    except Exception as e:
        logger.error(f"Error reading inventory file: {e}")
        raise Exception(f"Error reading inventory file: {e}")





    sys.exit(0)






if __name__ == "__main__":

    logger = configure_logging()
    logger.info("Logging configurated")

    parser = argparse.ArgumentParser()
    parser.add_argument("--iganima_config", type=str, required=True)
    parser.add_argument("--event_id", type=str, required=True)

    args = parser.parse_args()
    print("OK:", args)

    main(args)