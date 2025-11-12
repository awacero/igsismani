
import sys, os

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
import requests
from PIL import Image
import cv2
from manim import config
import shutil

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


        print("HOLIII")
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
        frames_map = run_param["animation"]["frames_map"]
        frames_info = run_param["animation"]["frames_info"]

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
        clean_frames_directory(frames_map)
        clean_frames_directory(frames_info)
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
        logger.info("Get event info completed")
        print(event_dict)
    except Exception as e:
        logger.error(f"Error getting event info {e}")
        raise Exception(f"Error getting event info: {e}")


    try:
        parameters = {
            "lat":event_latitude,
            "lon":event_longitude,
            "token":nearest_token
        }

        response = requests.get(f"{nearest_url}", params=parameters)
        response.raise_for_status()
        event_dict ['distance'],event_dict['city'],event_dict['province'] = eval(response.text.strip())
        
    except Exception as e:
        logger.error(f"Error getting event nearest {e}.Filling with emptiness")
        event_dict ['distance'] = '--'
        event_dict ['city'] = '--'
        event_dict ['province'] = '--'



    try:
        logger.info(f"Create the map animation")
        # TRY DO IT IN PARALLEL 
        frame_names = []
        for t in range(0, FRAMES_NUMBER ):

            frame_data = create_initial_point_frame(event_longitude, event_latitude)

            # Guardar el frame
            frame_name = f'{frames_map}/map_{t:03}.png'
            frame_names.append(frame_name)
            fig = go.Figure(data=frame_data)
            zoom_start = 4.5
            zoom_end = 9.5
            zoom_level = zoom_start + (zoom_end - zoom_start) * (t / FRAMES_NUMBER)
            save_frame(fig, frame_name, mapbox_access_token, event_latitude, event_longitude, event_annotation,zoom_level)

        # Compilar la animación
        ##compile_animation("./frames", f"{event_id}.gif", f"{event_id}.mp4", fps=3)

        
    except Exception as e:
        logger.error(f"Error while creating the map frames: {e}")
        raise Exception(f"Error while creating the map frames: {e}")


    try:
        logger.info("Create info frames")
        from iganima.infobars_scene import InfoBarsScene
        scene = InfoBarsScene(event_dict, output_dir=frames_info, n_frames=FRAMES_NUMBER)
        scene.generate_frames()
        

    except Exception as e:
        logger.error(f"Error while creating the info frames: {e}")
        raise Exception(f"Error while creating the info frames: {e}")

    try:

        os.makedirs("frames_combined", exist_ok=True)

        for i in range(FRAMES_NUMBER):
            map_img = Image.open(f"{frames_map}/map_{i:03}.png")
            info_img = Image.open(f"{frames_info}/info_{i:03}.png")

            # Combinar verticalmente
            combined = Image.new("RGB", (map_img.width, map_img.height + info_img.height),color="white")
            combined.paste(map_img, (0, 0))
            combined.paste(info_img, (0, map_img.height))
            combined.save(f"frames_combined/frame_{i:03}.png")
        shutil.copy2(f"frames_combined/frame_019.png", f"frames_combined/frame_000.png")

        # 4. Crear el video final a partir de los frames combinados
        # ---------------------------------------------------------------------
        
        logger.info("Create video from frames_combined")
        logger.info("Fusion map and info")
        frame_array = []


        for i in range(FRAMES_NUMBER):
            img = cv2.imread(f"frames_combined/frame_{i:03}.png")
            height, width, layers = img.shape
            size = (width, height)
            frame_array.append(img)

        logger.info("Create video using opencv")
        out = cv2.VideoWriter(f'{event_dict["event_id"]}.mp4',
                            cv2.VideoWriter_fourcc(*'avc1'),
                            FPS,  # fps
                            size)

        for frame in frame_array:
            out.write(frame)
        out.release()



    except Exception as e:
        logger.error(f"Error while creating the info frames: {e}")
        raise Exception(f"Error while creating the info frames: {e}")

    












    sys.exit(0)






if __name__ == "__main__":

    logger = configure_logging()
    logger.info("Logging configurated")

    parser = argparse.ArgumentParser()
    parser.add_argument("--iganima_config", type=str, required=True)
    parser.add_argument("--event_id", type=str, required=True)

    args = parser.parse_args()
    print("OK:", args)

    config.pixel_width = 720
    config.pixel_height = 640
    config.frame_width = 14.0
    config.frame_height = 8.0

    main(args)