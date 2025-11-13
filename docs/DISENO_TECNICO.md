# Diseño Técnico del Sistema – IGANIMA

## 1. Objetivo
Este documento describe la arquitectura lógica y las decisiones de diseño que permiten a IGANIMA generar animaciones sísmicas. Se detallan componentes, contratos de datos y flujos para facilitar mantenimiento y futuras extensiones.

## 2. Arquitectura Lógica
### 2.1 Capas
1. **Capa de Configuración y Entrada**: Procesa argumentos CLI y archivos INI/JSON. Proporciona valores normalizados (rutas, tokens, servidores) al orquestador.
2. **Capa de Datos Sísmicos**: Se conecta al servidor FDSN, recupera el catálogo del evento y construye estructuras enriquecidas (`event_dict`, DataFrames). Incluye utilidades para adjuntar coordenadas y distancias.
3. **Capa de Visualización**: Produce frames de mapa con Plotly/Mapbox y frames de texto con Manim; encapsula la lógica de geometrías y animaciones.
4. **Capa de Composición/Salida**: Usa PIL/OpenCV para combinar imágenes y escribir el video final en disco.

### 2.2 Diagrama de Flujo (descrito)
1. Usuario ejecuta `python run_igsismani.py --iganima_config <cfg> --event_id <id>`.
2. Se leen archivos INI/JSON; se construye el cliente FDSN.
3. Se descarga el evento, se genera `event_dict` y se solicita información de proximidad.
4. Se limpian carpetas de frames y se renderizan mapas (`map_###.png`).
5. Se invoca `InfoBarsScene` para renderizar barras (`info_###.png`).
6. Se combinan los pares de imágenes y se genera `EVENTO.mp4`.

## 3. Componentes y Responsabilidades
### 3.1 `run_igsismani.py`
- **Entradas**: CLI (`argparse`), archivo INI, archivo JSON, inventario XML, servicios HTTP.
- **Salidas**: Directorios de frames (`frames_map`, `frames_info`, `frames_combined`), video MP4 nombrado con el `event_id`.
- **Responsabilidades**: Validar configuración, coordinar módulos, registrar errores, definir dimensiones globales (pixel/frame width/height) para Manim.

### 3.2 `iganima/iganima_utils.py`
- **Funciones clave**: `connect_fdsn`, `get_event_by_id`, `event2dict`, `attach_coordinates_from_inventory`, `create_stations_dict`.
- **Contratos**: Devuelven objetos ObsPy enriquecidos o estructuras de Python puras listas/diccionarios; lanzan excepciones ante fallas en servicios FDSN.
- **Decisiones de diseño**: Uso de `AttribDict` para almacenar coordenadas, conversión de fechas a hora local mediante `pytz` y normalización de estados (`status`).

### 3.3 `iganima/iganima_functions.py`
- **Funciones clave**: `clean_frames_directory`, `create_initial_point_frame`, `save_frame`, `compile_animation` (opcional).
- **Decisiones**: Se usa Plotly Scattermapbox con `style="outdoors"`, se superpone un círculo rojo generado trigonométricamente y un logo remoto; las imágenes se guardan mediante `fig.write_image`. El zoom se interpola linealmente entre 4.5 y 9.5 para simular acercamiento.

### 3.4 `iganima/infobars_scene.py`
- **Estructura**: Clase `InfoBarsScene` que hereda de `Scene`, crea barras (`RoundedRectangle`) y textos (`Text`) en colores alternados, y captura los frames manualmente usando PIL para guardarlos como PNG.
- **Parámetros**: `event_info` (dict), `output_dir`, `n_frames`. Los tamaños de fuente y textos se formatean en español para uso institucional.

### 3.5 Composición de Frames
- `frames_map` y `frames_info` se combinan verticalmente con `PIL.Image.new` y `paste`. Luego `cv2.VideoWriter` usa codec `avc1` y FPS configurados para producir el MP4.

## 4. Modelos de Datos
### 4.1 `event_dict`
| Clave | Descripción | Fuente |
| --- | --- | --- |
| `event_id` | Identificador corto derivado de `resource_id`. | ObsPy `event.resource_id`. |
| `latitude`, `longitude`, `depth` | Coordenadas epicentrales (km). | `preferred_origin`. |
| `magnitude` | Magnitud redondeada (dos decimales). | `preferred_magnitude`. |
| `status` | Traducción (Preliminar/Revisado). | `status()` utilitaria. |
| `time_local`, `local_date`, `local_time` | Fecha/hora en `America/Guayaquil`. | `get_local_datetime`. |
| `distance`, `city`, `province` | Enriquecimiento de `nearest_url` o `--` por defecto. | Servicio HTTP adicional. |

### 4.2 Configuración INI
- `[fdsn]`: `server_id`, `server_config_file`, `xml_inventory_file`, `nearest_url`, `nearest_token`.
- `[animation]`: `mapbox_access_token`, `frames_map`, `frames_info`, `frames_number`, `fps`, `number_stations` (usado para otras variantes de animación).

### 4.3 Configuración JSON
Estructura `{"id": {"server_ip": "host", "port": 8080}}` usada para construir el cliente FDSN. Se expanden variables de entorno para rutas dinámicas.

## 5. Estrategia de Ejecución
1. **Preparación**: Crear entorno Conda, instalar dependencias y preparar archivos `logging.ini`, `iganima.cfg` y catálogo JSON.
2. **Ejecución**: Invocar el script con argumentos requeridos. El ancho/alto de píxel para Manim se fija antes de llamar a `main`.
3. **Resultados**: Directorios `frames_map`, `frames_info`, `frames_combined` y video final en el directorio actual.

## 6. Extensibilidad
- **Nuevos canales de salida**: Se puede reutilizar `frames_combined` para generar GIFs con `compile_animation` ya implementado en `iganima_functions` si se expone desde el orquestador.
- **Soporte multi-evento**: Encapsular `main` en una función que acepte una lista de eventos permitiría ejecuciones por lotes.
- **Tematización**: Parametrizar colores, fuentes y logos mediante la configuración permitiría adaptar la identidad visual sin modificar código.

## 7. Consideraciones Operativas
- Mantener tokens y rutas fuera del control de versiones usando variables de entorno (`$HOME`, etc.) como ya soporta `load_config_from_file`.
- Verificar espacio en disco antes de generar frames; cada ejecución produce al menos `3 * frames_number` archivos PNG temporales.
- Automatizar la limpieza de `frames_combined` tras exportar el video para ahorrar almacenamiento.
