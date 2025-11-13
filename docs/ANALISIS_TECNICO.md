# Análisis Técnico – Sistema de Animación Sísmica IGANIMA

## 1. Resumen Ejecutivo
IGANIMA es una tubería offline que transforma metadatos sísmicos en recursos audiovisuales. Su fortaleza radica en apoyarse en bibliotecas especializadas (ObsPy, Plotly, Manim, OpenCV) pero requiere configuraciones externas consistentes para operar. Este análisis describe la arquitectura actual, los flujos de datos, dependencias clave y riesgos técnicos.

## 2. Arquitectura Actual
### 2.1 Componentes Principales
1. **CLI y orquestador (`run_igsismani.py`)**: Gestiona argumentos, lee configuraciones, coordina conexiones y encapsula el flujo completo desde la adquisición de datos hasta la exportación del video.
2. **Utilidades de datos (`iganima/iganima_utils.py`)**: Proveen funciones para conectarse a servidores FDSN, obtener eventos, convertirlos en diccionarios/tablas y adjuntar metadatos (coordenadas, distancias).
3. **Funciones de visualización (`iganima/iganima_functions.py`)**: Manipulan directorios de frames, generan geometrías (puntos, círculos, ondas) y renderizan figuras Plotly guardadas como PNG.
4. **Escena de barras (`iganima/infobars_scene.py`)**: Define una escena Manim reusable que genera frames con texto y barras animadas sobre datos del evento.
5. **Configuraciones**: Archivos INI y JSON que describen servidores, rutas y parámetros visuales.

### 2.2 Patrón de Integración
El orquestador actúa como secuenciador: valida la configuración, delega al módulo de utilidades para conectar y enriquecer datos, llama a las funciones de animación para producir frames y usa PIL/OpenCV para la composición final. No existe un sistema de colas; todo se ejecuta secuencialmente en memoria única.

### 2.3 Flujo de Datos
1. **Entrada**: Argumentos CLI → lectura INI/JSON → valores expanden variables de entorno.
2. **Catálogo sísmico**: Cliente FDSN obtiene el evento → `event2dict` lo transforma → se calcula fecha/hora local.
3. **Enriquecimiento externo**: Servicio HTTP adicional devuelve ciudad/provincia/distancia; en caso de fallo se registran valores nulos.
4. **Frames**: `create_initial_point_frame` y `save_frame` generan PNG con Mapbox; `InfoBarsScene` produce PNG con datos textualizados.
5. **Salida**: PIL combina mapas + barras; OpenCV compila el video MP4 que se nombra con el `event_id`.

## 3. Dependencias y Servicios
- **ObsPy FDSN Client**: descarga eventos/inventarios; requiere conectividad HTTP y certificados adecuados.
- **Requests**: consulta de localidad más cercana; depende de un endpoint personalizado (`nearest_url`).
- **Plotly + Mapbox**: renderizan mapas de fondo; necesitan token activo (`mapbox_access_token`).
- **Manim + Cairo/Pango**: renderizado de barras informativas; exige stack gráfico instalado según instrucciones de Manim.
- **PIL/OpenCV**: composición final y codificación MP4 con codec `avc1`.

## 4. Calidad del Código y Observaciones
- **Manejo de errores**: Uso sistemático de bloques `try/except` con registros detallados; sin embargo, el script termina con `sys.exit(0)` incluso ante fallas tardías, lo cual dificulta distinguir ejecuciones fallidas en pipelines automatizados.
- **Acoplamiento**: El módulo principal importa todo (`from iganima.iganima_functions import *`), lo que oculta dependencias explícitas y dificulta pruebas unitarias.
- **Configuración**: `load_config_from_file` expande variables de entorno recursivamente, lo cual es robusto, pero el archivo INI no es validado contra un esquema, permitiendo errores silenciosos en claves faltantes.
- **Recursos externos**: La función `save_frame` embebe un logo remoto (GitHub raw). Una caída de red bloquearía la generación del frame, por lo que conviene incorporar el recurso localmente.
- **Dependencia faltante**: Se importa `get_circle_color` sin implementación dentro del repositorio, lo que provocará `ImportError` si el paquete no se instala como dependencia adicional.

## 5. Riesgos Técnicos
1. **Disponibilidad de servicios externos**: FDSN y `nearest_url` son puntos únicos de fallo; no existe reintento ni caché local.
2. **Rendimiento**: El renderizado secuencial de frames puede tardar minutos en eventos de alta resolución; no hay paralelización ni control de progreso.
3. **Gestión de secretos**: Tokens Mapbox y credenciales FDSN se leen desde archivos sin cifrado; deben protegerse mediante permisos del sistema operativo.
4. **Compatibilidad gráfica**: Manim depende de Cairo/Pango; servidores sin entorno gráfico pueden requerir dependencias adicionales (fonts, libs).

## 6. Oportunidades de Mejora
- Añadir validaciones formales de esquema para los archivos INI/JSON y mensajes de error más orientados al usuario.
- Incluir una implementación local de `get_circle_color` o eliminar la dependencia si no se usa.
- Parametrizar la ruta del logo para evitar dependencias en recursos remotos e incrementar la resiliencia offline.
- Exponer una interfaz programática (funciones) para permitir pruebas unitarias sin ejecutar todo el pipeline CLI.
- Registrar métricas (tiempo por frame, duración de descargas) para monitorear rendimiento y detectar cuellos de botella.
