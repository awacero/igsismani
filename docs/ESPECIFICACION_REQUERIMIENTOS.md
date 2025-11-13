# Especificación de Requerimientos del Software (SRS) – IGANIMA

## 1. Introducción
### 1.1 Propósito
El propósito de este documento es definir con precisión qué debe hacer IGANIMA, un conjunto de utilidades que genera mapas y barras informativas animadas a partir de catálogos sísmicos oficiales. El SRS describe el comportamiento funcional, las restricciones técnicas y las interfaces externas que deben respetarse para operar el script principal `run_igsismani.py` en entornos de producción o investigación.

### 1.2 Alcance
El alcance abarca la ingesta de parámetros mediante archivos INI/JSON, la conexión a servicios FDSN para recuperar la información del evento, la generación de cuadros (frames) de mapa con Plotly, la construcción de barras informativas con Manim y la composición final en video MP4. Quedan fuera de este alcance servicios de distribución o publicación web del material renderizado.

### 1.3 Definiciones, acrónimos y abreviaturas
- **FDSN**: Servicio estandarizado para el intercambio de metadatos sísmicos (FDSN Web Services).
- **Frame**: Imagen estática generada para un instante de la animación.
- **Mapbox**: API de mapas base utilizada para renderizar los fondos cartográficos.
- **Manim**: Motor de animación para componer escenas tipográficas.

### 1.4 Referencias
- Archivo `README.md` para prerrequisitos y configuración general.
- Código fuente en `run_igsismani.py`, `iganima/iganima_functions.py`, `iganima/iganima_utils.py` e `iganima/infobars_scene.py`.

### 1.5 Visión General
El resto del documento aborda la descripción general del producto (Sección 2) y los requerimientos funcionales/no funcionales específicos (Sección 3).

## 2. Descripción General
### 2.1 Perspectiva del Producto
IGANIMA es un ejecutable por línea de comandos que actúa como cliente de un servidor FDSN interno, produce mapas con Plotly y genera gráficos adicionales con Manim. La aplicación depende de archivos de configuración externos para instanciar clientes, rutas de recursos y parámetros visuales.

### 2.2 Funciones del Producto
- Validar parámetros entregados por CLI y cargar configuraciones INI/JSON.
- Limpiar directorios de trabajo y preparar carpetas para frames.
- Conectarse al servicio FDSN y recuperar datos del evento y estaciones.
- Construir anotaciones y atributos derivados (distancia a ciudades, hora local).
- Renderizar mapas secuenciales con Mapbox y anotaciones del evento.
- Renderizar barras informativas con Manim y exportarlas como PNG.
- Fusionar frames, generar video MP4 y dejar evidencia en disco.

### 2.3 Clases de Usuarios
- **Analistas sísmicos**: Ejecutan el script para generar productos oficiales.
- **Desarrolladores/DevOps**: Mantienen la integración con servicios FDSN y Mapbox.
- **Comunicadores científicos**: Consumen los videos para difusión pública.

### 2.4 Entorno Operativo
- Python 3.13+ con dependencias: `pandas`, `numpy`, `plotly`, `moviepy`, `obspy`, `manim`, `opencv-python` y `Pillow` instalados en una máquina con acceso a internet para Mapbox/FDSN.
- Sistema de archivos con permisos de lectura/escritura para los directorios de frames definidos en la configuración.

### 2.5 Restricciones de Diseño
- Requiere un token Mapbox válido; de lo contrario, la descarga de teselas falla.
- Necesita catálogos XML y endpoints FDSN accesibles por HTTP.
- La biblioteca `get_circle_color` no está presente en el repositorio, por lo que los colores concéntricos dependen de una implementación externa.

### 2.6 Suposiciones y Dependencias
- Se asume conectividad estable hacia los servicios de proximidad (`nearest_url`) para enriquecer la descripción del evento.
- Se presume que los inventarios XML tienen los metadatos necesarios para anexar coordenadas a las trazas.

## 3. Requerimientos Específicos
### 3.1 Requerimientos Funcionales
1. **Entrada por CLI**: El usuario debe proporcionar `--iganima_config` y `--event_id` al ejecutar el script; ambos son obligatorios y su ausencia termina en error.
2. **Lectura de configuración**: El sistema debe aceptar archivos INI con secciones `[fdsn]` y `[animation]`, y JSON con la tabla de servidores, expandiendo variables de entorno antes de su uso.
3. **Conexión a FDSN**: El sistema debe abrir un cliente HTTP hacia el host/puerto proporcionados y propagar errores de red en los logs.
4. **Recuperación de eventos**: Para cada `event_id`, debe solicitarse el catálogo correspondiente y convertirlo en un diccionario enriquecido (magnitud, ubicación, hora local).
5. **Enriquecimiento geográfico**: Se debe consultar el servicio `nearest_url` con latitud y longitud para obtener la ciudad/provincia más cercana; en caso de error se llenan campos con `--`.
6. **Gestión de directorios**: Los directorios `frames_map` y `frames_info` se limpian antes de crear nuevos archivos para evitar residuos de ejecuciones previas.
7. **Generación de frames de mapa**: Para cada iteración `t` hasta `frames_number`, se debe producir un archivo PNG que contenga el punto del epicentro, un círculo rojo semitransparente y el logo institucional sobre un mapa Mapbox.
8. **Generación de barras informativas**: Se debe renderizar una secuencia de `n_frames` PNG que contenga magnitud, profundidad, distancia, ciudad, fecha y hora usando el objeto `InfoBarsScene`.
9. **Composición final**: El sistema debe combinar verticalmente cada par de frames y generar un video MP4 usando OpenCV con el FPS definido en la configuración.
10. **Registro de errores**: Cada bloque crítico debe capturar excepciones, registrarlas y relanzarlas para facilitar diagnósticos en lotes automatizados.

### 3.2 Requerimientos de Datos
- **Archivos de configuración**: INI (parámetros generales) y JSON (catálogo de servidores). Deben permitir variables de entorno para rutas sensibles.
- **Inventarios XML**: Definen los metadatos de estaciones y se usan para adjuntar coordenadas cuando los servicios FDSN no proporcionan información completa.
- **Frames**: Imágenes PNG nombradas secuencialmente (`map_###.png`, `info_###.png`) almacenadas en carpetas configurables.

### 3.3 Requerimientos No Funcionales
- **Disponibilidad**: El sistema debe tolerar fallos transitorios en servicios externos registrando errores y continuando cuando sea seguro (por ejemplo, rellenando `--`).
- **Rendimiento**: La generación de frames debe completarse dentro de una sola ejecución secuencial; no hay paralelización implementada, por lo que el número de frames debe mantenerse moderado (20 por defecto).
- **Usabilidad**: La interacción es por CLI; la documentación debe describir los argumentos obligatorios y ejemplos de uso.
- **Portabilidad**: Compatible con cualquier sistema operativo que soporte Python 3.13 y las dependencias mencionadas.
- **Seguridad**: Los tokens y rutas sensibles se pasan mediante archivos de configuración que pueden residir fuera del repositorio y usar variables de entorno para ocultar credenciales.
