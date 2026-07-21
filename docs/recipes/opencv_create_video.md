# Crear un video con OpenCV

## ¿Para qué sirve?

Crear un MP4 a partir de una secuencia de imágenes.

## Código

```python
...

    frame_array = []
    for i in range(total_frames):
        img = cv2.imread(f"{runtime['frames_out']}/frame_{i:03}.png")
        height, width, layers = img.shape
        size = (width, height)
        frame_array.append(img)

    logger.info("Create video using opencv")
    out = cv2.VideoWriter(
        f'{runtime["video_out"]}/{event["data"]["event_id"]}.mp4',
        cv2.VideoWriter_fourcc(*'avc1'),
        runtime["fps"],  # fps
        size,
    )

    for frame in frame_array:
        #print(frame)
        out.write(frame)
    out.release()


```

## Cuándo usarlo

- Videos cortos.
- Cuando ya existen los frames.

## Observaciones

Fue reemplazado por otra implementación porque... no me acuerdo :( 
```