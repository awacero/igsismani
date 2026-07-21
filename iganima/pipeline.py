import logging
from iganima.iganima_functions import *
from PIL import Image, ImageDraw

import cv2
from moviepy.editor import VideoFileClip, AudioFileClip, afx

from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESOURCES_DIR = PROJECT_ROOT / "resources"

logger = logging.getLogger(__name__)


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


def create_map_frames(runtime,event):

    ###CREAR FRAMES DEL MAPA 
    try:
        logger.info(f"Create the map animation")

        from iganima import iganima_functions

        colors_list = ['red','red','red']
        radius_list = [runtime["frames_number"]*0.1, runtime["frames_number"]*0.07, runtime["frames_number"]*0.05]
        scale_list = [0.1, 0.07, 0.05]
        circle_zip = zip(colors_list,radius_list)

        for color,radius in circle_zip:
            lat_circle,lon_circle = generate_circle(event["latitude"],event["longitude"], radius)
            

        # TRY DO IT IN PARALLEL 
        frame_names = []
        for t in range(0, runtime["frames_number"]):
            ###Quitar el punto central del evento 
            #frame_data = create_initial_point_frame(event["longitude"], event["latitude"])
            frame_data = []
            # ondas crecientes
            for color, scale in zip(colors_list, scale_list):
                radius = t * scale
                lat_circ, lon_circ = generate_circle(event["latitude"], event["longitude"], radius)

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
            frame_name = f"{runtime['frames_out']}/map_{t:03}.png"
            frame_names.append(frame_name)
            fig = go.Figure(data=frame_data)
            zoom_start = 4.5
            zoom_end = 9.5
            zoom_level = zoom_start + (zoom_end - zoom_start) * (t / runtime["frames_number"])
            save_frame(
                fig,
                frame_name,
                runtime["mapbox_access_token"],
                event["latitude"],
                event["longitude"],
                event["annotation"],
                zoom_level,
            )


    except Exception as e:
        logger.error(f"Error while creating the map frames: {e}")
        raise Exception(f"Error while creating the map frames: {e}")


def create_info_frames(runtime,event):

    # 2. Crear frames de info (barras inferiores, etc.)
    try:
        logger.info("Create info frames")
        from iganima.infobars_scene import InfoBarsScene

        scene = InfoBarsScene(event["data"], output_dir=runtime['frames_out'], n_frames=runtime["frames_number"])

        scene.generate_frames()

    except Exception as e:
        logger.error(f"Error while creating the info frames: {e}")
        raise Exception(f"Error while creating the info frames: {e}")

def create_combined_frames(runtime,event):


    # 3. Combinar: intro de columnas + mapa + info
    try:
        logger.info("Create combined frames (columns intro + map + info)")
        os.makedirs(f"{runtime['frames_out']}", exist_ok=True)

        # Usar el primer frame de mapa e info como referencia de tamaño
        sample_map_path = f"{runtime['frames_out']}/map_000.png"
        sample_info_path = f"{runtime['frames_out']}/info_000.png"

        map_sample = Image.open(sample_map_path)
        info_sample = Image.open(sample_info_path)

        combined_width = map_sample.width
        map_height = map_sample.height
        info_height = info_sample.height
        combined_height = map_height + info_height

        map_sample.close()
        info_sample.close()

        # Total de frames del video final: intro columnas + mapa+info
        total_frames = runtime["frames_columns"] + runtime["frames_number"]

        # Colores de las columnas (aprox)
        azul_oscuro = (46, 95, 168)
        rojo_quemado = (128, 0, 32)
        azul_oscuro =(3,13,69)
        azul_claro = (12,79,158)
        blanco = (255, 255, 255)
        colors = [azul_oscuro, azul_claro, blanco]

        
        for i in range(total_frames):

            if i < runtime["frames_columns"]:
                # Intro de columnas sobre el primer frame real del mapa + info
                t = i / max(runtime["frames_columns"] - 1, 1)

                #combined = background_combined.copy().convert("RGBA")

                # Usar frames dinámicos durante la intro:
                # mapa fijo en map_000, pero info avanza con la animación
                info_index = min(i, runtime["frames_number"] - 1)

                map_background = Image.open(f"{runtime['frames_out']}/map_000.png")
                info_background = Image.open(f"{runtime['frames_out']}/info_{info_index:03}.png")

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
                combined.save(f"{runtime['frames_out']}/frame_{i:03}.png")

            else:
                # Fase de mapa + info como antes
                j = i - runtime["frames_columns"]

                info_index = min(i,runtime["frames_number"] -1)


                map_img = Image.open(f"{runtime['frames_out']}/map_{j:03}.png")
                info_img = Image.open(f"{runtime['frames_out']}/info_{info_index:03}.png")

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

                combined.save(f"{runtime['frames_out']}/frame_{i:03}.png")

                map_img.close()
                info_img.close()
    except Exception as e:
        logger.error(f"Error while creating the combined frames: {e}")
        raise Exception(f"Error while creating the combined frames: {e}")

def create_video(runtime,event):

    try:
        total_frames = runtime["frames_columns"] + runtime["frames_number"]
        # 4. Crear el video final a partir de los frames combinados
        logger.info("Create video from frames_combined")
        logger.info("Fusion columns intro + map + info")


        logger.info("Create video using opencv")

        # Ruta del video corto que quieres anexar
        outro_video_path = RESOURCES_DIR / "outro_xs.mp4"
        # Leer primer frame para obtener size
        first_frame_path = f"{runtime['frames_out']}/frame_000.png"
        first_frame = cv2.imread(first_frame_path)

        if first_frame is None:
            raise FileNotFoundError(f"Could not read first frame: {first_frame_path}")

        height, width, layers = first_frame.shape
        size = (width, height)

        out = cv2.VideoWriter(
            f'{runtime["video_out"]}/{event["data"]["event_id"]}.mp4',
            cv2.VideoWriter_fourcc(*'avc1'),
            runtime["fps"],
            size,
        )

        # 1. Escribir los frames principales
        last_frame = None

        for i in range(total_frames):
            frame_path = f"{runtime['frames_out']}/frame_{i:03}.png"
            img = cv2.imread(frame_path)

            if img is None:
                raise FileNotFoundError(f"Could not read frame: {frame_path}")

            img = cv2.resize(img, size)
            out.write(img)
            last_frame = img.copy()

        # 2. Mantener el último frame durante 3 segundos
        hold_frames = runtime["fps"] * 3

        if last_frame is not None:
            for _ in range(hold_frames):
                out.write(last_frame)

        # 3. Anexar video corto al final
        outro_skip_seconds = 3
        outro_skip_frames = int(outro_skip_seconds*runtime["fps"])

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

        silent_video_path = f'{runtime["video_out"]}/{event["data"]["event_id"]}.mp4'
        final_video_path = f'{runtime["video_out"]}/{event["data"]["event_id"]}_audio.mp4'
        audio_path = RESOURCES_DIR / "backsound.mp3"
        logger.info("Adding background audio using MoviePy")

        video_clip = VideoFileClip(silent_video_path)
        audio_clip = AudioFileClip(str(audio_path))

        audio_loop = afx.audio_loop(
            audio_clip,
            duration=video_clip.duration
        )

        final_clip = video_clip.set_audio(audio_loop)

        final_clip.write_videofile(
            final_video_path,
            codec="libx264",
            audio_codec="aac",
            fps=runtime["fps"]
        )

        video_clip.close()
        audio_clip.close()
        final_clip.close()

        logger.info(f"Final video with audio created: {final_video_path}")


    except Exception as e:
        logger.error(f"Error while creating the video: {e}")
        raise Exception(f"Error while creating the video: {e}")



def generate_map_frames(runtime,event):

    create_map_frames( runtime=runtime,event=event)

    create_info_frames(runtime=runtime, event=event)

    create_combined_frames(runtime=runtime, event=event)

    create_video(runtime=runtime, event=event)


