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
from PIL import Image, ImageDraw
import cv2

from moviepy.editor import VideoFileClip, AudioFileClip, afx

pd.set_option('display.max_colwidth', None)
pd.set_option('display.max_columns', None)


def resize_with_padding(frame, target_size, background_color=(255, 255, 255)):
    """
    Resize a frame keeping its aspect ratio and add padding
    to fit the target video size.

    Parameters
    ----------
    frame : np.ndarray
        Input image/frame in BGR format.
    target_size : tuple
        Target size as (width, height).
    background_color : tuple
        Background color in BGR format.

    Returns
    -------
    np.ndarray
        Frame resized with padding.
    """

    target_width, target_height = target_size
    original_height, original_width = frame.shape[:2]

    scale = min(
        target_width / original_width,
        target_height / original_height
    )

    new_width = int(original_width * scale)
    new_height = int(original_height * scale)

    resized_frame = cv2.resize(
        frame,
        (new_width, new_height),
        interpolation=cv2.INTER_AREA
    )

    canvas = np.full(
        (target_height, target_width, 3),
        background_color,
        dtype=np.uint8
    )

    x_offset = (target_width - new_width) // 2
    y_offset = (target_height - new_height) // 2

    canvas[
        y_offset:y_offset + new_height,
        x_offset:x_offset + new_width
    ] = resized_frame

    return canvas

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
        frames_out = run_param["animation"]["frames_out"]
        frames_in = run_param["animation"]["frames_in"]
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
        clean_frames_directory(frames_out)
    except Exception as e:
        logger.error(f"Error in cleaning frame directory: {e}")
        raise Exception(f"Error in cleaning frame directory: {e}")
    
    try:
        logger.info(f"Get event info")
        # Conexión y obtención de datos del evento
        event_inventory = u.get_event_by_id(fdsn_client, event_id)
        event_dict = u.event2dict(event_inventory[0])

        # Información del evento para la anotación
        event_annotation = (
            f"ID: {event_dict['event_id']} {event_dict['status']}<br>"
            f"{event_dict['time_local']} Hora Local<br>"
            f"Prof. {event_dict['depth']} Km.  Magnitud:  {event_dict['magnitude']}"
        )

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
            "lat": event_latitude,
            "lon": event_longitude,
            "token": nearest_token,
        }

        response = requests.get(f"{nearest_url}", params=parameters)
        response.raise_for_status()
        event_dict['distance'], event_dict['city'], event_dict['province'] = eval(response.text.strip()        )

        event_dict['distance'] = round(event_dict['distance'], 1)

    except Exception as e:
        logger.error(f"Error getting event nearest {e}.Filling with emptiness")
        event_dict['distance'] = '--'
        event_dict['city'] = '--'
        event_dict['province'] = '--'

    # 1. Crear frames del mapa
    try:
        logger.info(f"Create the map animation")

        from iganima import iganima_functions

        colors_list = ['red','red','red']
        radius_list = [FRAMES_NUMBER*0.1, FRAMES_NUMBER*0.07, FRAMES_NUMBER*0.05]
        scale_list = [0.1, 0.07, 0.05]
        circle_zip = zip(colors_list,radius_list)

        for color,radius in circle_zip:
            lat_circle,lon_circle = generate_circle(event_latitude,event_longitude, radius)
            

        # TRY DO IT IN PARALLEL 
        frame_names = []
        for t in range(0, FRAMES_NUMBER):
            ###Quitar el punto central del evento 
            #frame_data = create_initial_point_frame(event_longitude, event_latitude)
            frame_data = []
            # ondas crecientes
            for color, scale in zip(colors_list, scale_list):
                radius = t * scale
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

  
            # Guardar el frame
            frame_name = f'{frames_out}/map_{t:03}.png'
            frame_names.append(frame_name)
            fig = go.Figure(data=frame_data)
            zoom_start = 4.5
            zoom_end = 9.5
            zoom_level = zoom_start + (zoom_end - zoom_start) * (t / FRAMES_NUMBER)
            save_frame(
                fig,
                frame_name,
                mapbox_access_token,
                event_latitude,
                event_longitude,
                event_annotation,
                zoom_level,
            )


    except Exception as e:
        logger.error(f"Error while creating the map frames: {e}")
        raise Exception(f"Error while creating the map frames: {e}")

    # 2. Crear frames de info (barras inferiores, etc.)
    try:
        logger.info("Create info frames")
        from iganima.infobars_scene import InfoBarsScene

        #scene = InfoBarsScene(event_dict, output_dir=frames_out, n_frames=FRAMES_NUMBER, input_dir=frames_in)
        scene = InfoBarsScene(
        event_dict,
        output_dir=frames_out,
        n_frames=FRAMES_NUMBER,
        input_dir=frames_in,
        pixel_width=INFOBARS_PIXEL_WIDTH,
        pixel_height=INFOBARS_PIXEL_HEIGHT,
        frame_width=INFOBARS_FRAME_WIDTH,
        frame_height=INFOBARS_FRAME_HEIGHT,
    )
        scene.generate_frames()

    except Exception as e:
        logger.error(f"Error while creating the info frames: {e}")
        raise Exception(f"Error while creating the info frames: {e}")

    # 3. Combinar: intro de columnas + mapa + info, y generar video
    try:
        logger.info("Create combined frames (columns intro + map + info)")
        os.makedirs(f"{frames_out}", exist_ok=True)

        # Usar el primer frame de mapa e info como referencia de tamaño
        sample_map_path = f"{frames_out}/map_000.png"
        sample_info_path = f"{frames_out}/info_000.png"

        map_sample = Image.open(sample_map_path)
        info_sample = Image.open(sample_info_path)

        combined_width = map_sample.width
        map_height = map_sample.height
        info_height = info_sample.height
        combined_height = map_height + info_height

        map_sample.close()
        info_sample.close()

        # Total de frames del video final: intro columnas + mapa+info
        total_frames = FRAMES_COLUMNS + FRAMES_NUMBER

        # Colores de las columnas (aprox)
        azul_oscuro = (46, 95, 168)
        rojo_quemado = (128, 0, 32)
        azul_oscuro =(3,13,69)
        azul_claro = (12,79,158)
        blanco = (255, 255, 255)
        colors = [azul_oscuro, azul_claro, blanco]

        '''
        # Crear fondo para la intro usando el primer frame real del mapa + info
        map_background = Image.open(f"{frames_out}/map_000.png")
        info_background = Image.open(f"{frames_out}/info_000.png")

        if info_background.height != info_height:
            info_background = info_background.resize(
                (combined_width, info_height),
                Image.LANCZOS
            )

        background_combined = Image.new(
            "RGB",
            (combined_width, combined_height),
            color="white"
        )

        background_combined.paste(map_background, (0, 0))
        background_combined.paste(info_background, (0, map_height))

        map_background.close()
        info_background.close()

        '''
        for i in range(total_frames):

            if i < FRAMES_COLUMNS:
                # Intro de columnas sobre el primer frame real del mapa + info
                t = i / max(FRAMES_COLUMNS - 1, 1)

                #combined = background_combined.copy().convert("RGBA")

                # Usar frames dinámicos durante la intro:
                # mapa fijo en map_000, pero info avanza con la animación
                info_index = min(i, FRAMES_NUMBER - 1)

                map_background = Image.open(f"{frames_out}/map_000.png")
                info_background = Image.open(f"{frames_out}/info_{info_index:03}.png")

                if info_background.height != info_height:
                    info_background = info_background.resize(
                        (combined_width, info_height),
                        Image.LANCZOS
                    )

                combined_rgb = Image.new(
                    "RGB",
                    (combined_width, combined_height),
                    color="white"
                )

                combined_rgb.paste(map_background, (0, 0))
                combined_rgb.paste(info_background, (0, map_height))

                map_background.close()
                info_background.close()

                combined = combined_rgb.convert("RGBA")


                base_width = combined_width / 3.0
                stripe_width = int(base_width * max(0.0, 1.0 - t))

                # Opacidad: 255 al inicio, 0 al final
                alpha = int(255 * max(0.0, 1.0 - t))

                overlay = Image.new(
                    "RGBA",
                    (combined_width, combined_height),
                    (255, 255, 255, 0)
                )

                draw = ImageDraw.Draw(overlay)

                current_x = 0

                for color in colors:
                    if stripe_width <= 0 or alpha <= 0:
                        break

                    x0 = int(current_x)
                    x1 = int(current_x + stripe_width)

                    r, g, b = color

                    draw.rectangle(
                        [(x0, 0), (x1, combined_height)],
                        fill=(r, g, b, alpha)
                    )

                    current_x = x1

                combined = Image.alpha_composite(combined, overlay).convert("RGB")
                combined.save(f"{frames_out}/frame_{i:03}.png")

            else:
                # Fase de mapa + info como antes
                j = i - FRAMES_COLUMNS

                info_index = min(i,FRAMES_NUMBER -1)


                map_img = Image.open(f"{frames_out}/map_{j:03}.png")
                info_img = Image.open(f"{frames_out}/info_{info_index:03}.png")

                if info_img.height != info_height:
                    info_img = info_img.resize(
                        (combined_width, info_height),
                        Image.LANCZOS
                    )

                combined = Image.new(
                    "RGB",
                    (combined_width, combined_height),
                    color="white"
                )

                combined.paste(map_img, (0, 0))
                combined.paste(info_img, (0, map_height))

                combined.save(f"{frames_out}/frame_{i:03}.png")

                map_img.close()
                info_img.close()
        # 4. Crear el video final a partir de los frames combinados
        logger.info("Create video from frames_combined")
        logger.info("Fusion columns intro + map + info")

        frame_array = []

        logger.info("Create video using opencv")

        # Ruta del video corto que quieres anexar
        outro_video_path = f"{frames_in}/outro_xs.mp4"

        # Leer primer frame para obtener size
        first_frame_path = f"{frames_out}/frame_000.png"
        first_frame = cv2.imread(first_frame_path)

        if first_frame is None:
            raise FileNotFoundError(f"Could not read first frame: {first_frame_path}")

        height, width, layers = first_frame.shape
        size = (width, height)

        out = cv2.VideoWriter(
            f'{video_out}/{event_dict["event_id"]}.mp4',
            cv2.VideoWriter_fourcc(*'avc1'),
            FPS,
            size,
        )

        # 1. Escribir los frames principales
        last_frame = None

        for i in range(total_frames):
            frame_path = f"{frames_out}/frame_{i:03}.png"
            img = cv2.imread(frame_path)

            if img is None:
                raise FileNotFoundError(f"Could not read frame: {frame_path}")

            img = cv2.resize(img, size)
            out.write(img)
            last_frame = img.copy()

        # 2. Mantener el último frame durante 3 segundos
        hold_frames = FPS * 3

        if last_frame is not None:
            for _ in range(hold_frames):
                out.write(last_frame)

        # 3. Anexar video corto al final
        outro_skip_seconds = 3
        outro_skip_frames = int(outro_skip_seconds*FPS)

        cap = cv2.VideoCapture(outro_video_path)

        if not cap.isOpened():
            raise FileNotFoundError(f"Could not open outro video: {outro_video_path}")

        frame_counter = 0
        while True:
            ret, outro_frame = cap.read()

            if not ret:
                break

            if frame_counter < outro_skip_frames:
                frame_counter +=1
                continue
            #outro_frame = cv2.resize(outro_frame, size)
            outro_frame = resize_with_padding(outro_frame, size)
            out.write(outro_frame)
            frame_counter +=1

        cap.release()
        out.release()

        silent_video_path = f'{video_out}/{event_dict["event_id"]}.mp4'
        final_video_path = f'{video_out}/{event_dict["event_id"]}_audio.mp4'
        audio_path = f"{frames_in}/backsound.mp3"

        logger.info("Adding background audio using MoviePy")

        video_clip = VideoFileClip(silent_video_path)
        audio_clip = AudioFileClip(audio_path)

        audio_loop = afx.audio_loop(
            audio_clip,
            duration=video_clip.duration
        )

        final_clip = video_clip.set_audio(audio_loop)

        final_clip.write_videofile(
            final_video_path,
            codec="libx264",
            audio_codec="aac",
            fps=FPS
        )

        video_clip.close()
        audio_clip.close()
        final_clip.close()

        logger.info(f"Final video with audio created: {final_video_path}")


        """        
        for i in range(total_frames):
            img = cv2.imread(f"{frames_out}/frame_{i:03}.png")
            height, width, layers = img.shape
            size = (width, height)
            frame_array.append(img)
          
        
        ##Keep information displayed for 3 segoncds 
        hold_frames = FPS * 3
        if frame_array:
            last_frame = frame_array[-1].copy()
            for _ in range(hold_frames):
                frame_array.append(last_frame.copy())


        ## Remover el outro y remplazar x un video corto
        '''
        outro_img = cv2.imread(f"{frames_in}/outro_qr.png")
        outro_img = cv2.resize(outro_img,(size[0],size[1]))

        for _ in range(FPS *2):
            frame_array.append(outro_img)

        '''
        outro_video_path = f"{frames_in}/outro_xs.mp4"
        cap


        ##Remover la imagen de anuncio. 
        
        '''
        outro_img = cv2.imread(f"{frames_in}/doc_anuncio_1.png")
        outro_img = cv2.resize(outro_img,(size[0],size[1]))

        for _ in range(FPS*2):
            frame_array.append(outro_img)
        '''
        
        logger.info("Create video using opencv")
        out = cv2.VideoWriter(
            f'{video_out}/{event_dict["event_id"]}.mp4',
            cv2.VideoWriter_fourcc(*'avc1'),
            FPS,  # fps
            size,
        )

        for frame in frame_array:
            #print(frame)
            out.write(frame)
        out.release()


        """

    except Exception as e:
        logger.error(f"Error while creating the combined frames / video: {e}")
        raise Exception(f"Error while creating the combined frames / video: {e}")

    sys.exit(0)


if __name__ == "__main__":

    logger = configure_logging()
    logger.info("Logging configurated")

    parser = argparse.ArgumentParser()
    parser.add_argument("--iganima_config", type=str, required=True)
    parser.add_argument("--event_id", type=str, required=True)

    args = parser.parse_args()
    print("OK:", args)

    # Configuración para las escenas internas (InfoBarsScene, etc.)

    INFOBARS_PIXEL_WIDTH = 720
    INFOBARS_PIXEL_HEIGHT = 444
    INFOBARS_FRAME_WIDTH = 14.0
    INFOBARS_FRAME_HEIGHT = 8.0

    main(args)
