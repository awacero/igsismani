import sys, os

import pandas as pd
import numpy as np
import logging
import logging.config
import argparse
import configparser

from pathlib import Path

from iganima import iganima_utils as u
from iganima.iganima_functions import *

import json
from obspy import read_inventory
import requests
from manim import config

from iganima.pipeline import generate_map_frames

pd.set_option('display.max_colwidth', None)
pd.set_option('display.max_columns', None)




def read_parameters(file_path):
    """
    Read a configuration text file
    
    :param string file_path: path to configuration text file
    :returns: dict: dict of a parser object
    """
    parser = configparser.ConfigParser()
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
    logging.config.fileConfig(Path("./config/", 'logging.ini'),
                              disable_existing_loggers=True)
    logger = logging.getLogger(__name__)

    logger.info(f"Logger configured was: {logging.getLogger().handlers}")
    return logger



def load_runtime(args):


##LECTURA DE CONFIGURACIÓN 
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
        logger.error(f"Error reading configuration  file: {e}")
        raise Exception(f"Error reading configuration file: {e}")

    try:
        logger.info(f"Read configuration file {configuration_file}")
        run_param = read_parameters(configuration_file)

        print(run_param)
    except Exception as e:
        logger.error(f"Error reading configuration sets in file: {e}")
        raise Exception(f"Error reading configuration file: {e}")

    try:
        logger.info(f"Loaded configuration file {configuration_file}")
        
        fdsn_id = run_param['fdsn']['server_id']
        mseed_server_config_file = run_param['fdsn']['server_config_file']
        xml_inventory_file = run_param['fdsn']['xml_inventory_file']

        nearest_url = run_param['fdsn']['nearest_url']
        nearest_token = run_param['fdsn']['nearest_token']

        mapbox_access_token = run_param["animation"]["mapbox_access_token"]
        FRAMES_NUMBER = int(run_param["animation"]["frames_number"])
        FPS = int(run_param["animation"]["fps"])
        number_stations = run_param["animation"]["number_stations"]
        frames_out = run_param["animation"]['frames_out']
        video_out = run_param["animation"]["video_out"]

        # Nuevo: número de frames para la intro de columnas (opción A).
        # Si no está definido en el ini, se toma ~1/3 del total, mínimo 5.
        FRAMES_COLUMNS = int(
            run_param["animation"].get("frames_columns",
                                       max(5, FRAMES_NUMBER // 3))
        )

    except Exception as e:
        logger.error(f"Error loading configuration sets in file: {e}")
        raise Exception(f"Error loading configuration file: {e}")

    try:
        logger.info(f"Read miniseed server file {mseed_server_config_file}")
        # mseed_server_param = u.read_config_file(mseed_server_config_file)
        mseed_server_param = load_config_from_file(mseed_server_config_file)

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

    runtime = {'event_id':event_id,'frames_out':frames_out,
            "video_out":video_out, "fps":FPS,
            "frames_number":FRAMES_NUMBER, "frames_columns":FRAMES_COLUMNS,
            "mapbox_access_token":mapbox_access_token, "nearest_url":nearest_url, 
            "nearest_token":nearest_token, 'fdsn_server_ip':fdsn_server_ip,
            'fdsn_server_port':fdsn_server_port
            }

    return runtime

def load_event(runtime):

    ##CONNECT TO FDSN 
    try:
        logger.info(f"Connect to fdsn server info ")
        fdsn_client = u.connect_fdsn(runtime['fdsn_server_ip'], runtime['fdsn_server_port'])
    except Exception as e:
        logger.error(f"Error connecting configuration file: {e}")
        raise Exception(f"Error connecting configuration file: {e}")


    ### GET EVENT INFO FROM FDSN 
    try:
        logger.info(f"Get event info")
        # Conexión y obtención de datos del evento
        event_inventory = u.get_event_by_id(fdsn_client, runtime['event_id'])
        event_dict = u.event2dict(event_inventory[0])

        # Información del evento para la anotación
        annotation = (
            f"ID: {event_dict['event_id']} {event_dict['status']}<br>"
            f"{event_dict['time_local']} Hora Local<br>"
            f"Prof. {event_dict['depth']} Km.  Magnitud:  {event_dict['magnitude']}"
        )

        event_dict['annotation'] = annotation

        # Parámetros del evento
        latitude = event_dict['latitude']
        longitude = event_dict['longitude']

        
        logger.info("Get event info completed")

    except Exception as e:
        logger.error(f"Error getting event info {e}")
        raise Exception(f"Error getting event info: {e}")
    
    try:
        parameters = {
            "lat": latitude,
            "lon": longitude,
            "token": runtime['nearest_token'],
        }

        response = requests.get(f"{runtime['nearest_url']}", params=parameters)
        response.raise_for_status()
        event_dict['distance'], event_dict['city'], event_dict['province'] = eval(response.text.strip()        )

        event_dict['distance'] = round(event_dict['distance'], 1)

    except Exception as e:
        logger.error(f"Error getting event nearest {e}.Filling with emptiness")
        event_dict['distance'] = '--'
        event_dict['city'] = '--'
        event_dict['province'] = '--'

    event_context = {"data":event_dict, "annotation":event_dict['annotation'],
                    "latitude":event_dict['latitude'],"longitude":event_dict['longitude']}

    return event_context

def main(args):

    runtime = load_runtime(args)

    ### CLEAN FRAME DIRECTORY 
    try:
        logger.info(f"Clean frame directory")
        clean_frames_directory( runtime['frames_out'])
    except Exception as e:
        logger.error(f"Error in cleaning frame directory: {e}")
        raise Exception(f"Error in cleaning frame directory: {e}")
    
    event_context = load_event(runtime=runtime)

    generate_map_frames(runtime=runtime, event=event_context)

    sys.exit(0)


if __name__ == "__main__":

    logger = configure_logging()
    logger.info("Logging configurated")

    parser = argparse.ArgumentParser()
    parser.add_argument("--iganima_config", type=str, required=True)
    parser.add_argument("--event_id", type=str, required=True)

    args = parser.parse_args()
    print("OK:", args)

    # Configuración de Manim para las escenas internas (InfoBarsScene, etc.)
    config.pixel_width = 720
    config.pixel_height = 444
    config.frame_width = 14.0
    config.frame_height = 8.0

    main(args)
