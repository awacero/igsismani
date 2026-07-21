# Agregar una imagen PNG al final del video

## ¿Para qué sirve?

Mostrar un anuncio o una pantalla final durante algunos segundos.

## Código

```python
...

        ##Remover la imagen de anuncio. 
        
        '''
        outro_img = cv2.imread(f"{runtime['frames_out']}/doc_anuncio_1.png")
        outro_img = cv2.resize(outro_img,(size[0],size[1]))

        for _ in range(runtime["fps"]*2):
            frame_array.append(outro_img)
        '''

```

## Observaciones

Actualmente el proyecto usa un video (`outro_xs.mp4`), pero esta técnica puede reutilizarse en otros proyectos.