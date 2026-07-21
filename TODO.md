# TODO

## Robustez

- [ ] Crear automáticamente los directorios de trabajo (`logs/`, `tmp/`, `cache/`) si no existen.
- [ ] Validar los recursos obligatorios al iniciar la aplicación.
- [ ] Mejorar los mensajes de error cuando falten archivos de configuración.

## Mantenibilidad

- [ ] Centralizar la creación de directorios en una función `ensure_directories()`.


## Configuración y portabilidad

### Alta prioridad

- [ ] Eliminar rutas absolutas del proyecto (`/home/...`).
- [ ] Resolver automáticamente la raíz del proyecto usando `pathlib.Path`.
- [ ] Convertir todas las rutas internas (logs, resources, templates, fonts, videos, etc.) en rutas relativas a la raíz del proyecto.
- [ ] Mantener en `iganima.cfg` únicamente la configuración dependiente del entorno (inventarios, directorios de salida, URLs de servicios, etc.).
- [ ] Crear un archivo `config/iganima.example.cfg` con valores de ejemplo para nuevas instalaciones.
- [ ] Documentar el proceso de instalación para que el proyecto pueda desplegarse únicamente con:
  1. `git clone`
  2. `conda env create -f environment.yml`
  3. Copiar `iganima.example.cfg` a `iganima.cfg`
  4. Ejecutar la aplicación


  ## Organización de recursos

### Alta prioridad

- [ ] Centralizar todos los recursos multimedia en `resources/`.
- [ ] Eliminar rutas absolutas hacia imágenes, videos, sonidos y fuentes.
- [ ] Acceder a los recursos utilizando rutas relativas a la raíz del proyecto.
- [ ] Versionar en Git todos los recursos necesarios para ejecutar la aplicación.
- [ ] Separar claramente los recursos de la aplicación (`resources/`) de los datos de entrada y salida (`data/` y `output/`).



## Portabilidad e instalación

### Alta prioridad

- [ ] Eliminar rutas absolutas (`/home/...`) del archivo `.env`.
- [ ] Resolver automáticamente la raíz del proyecto (`PROJECT_ROOT`) y construir las rutas internas desde ella.
- [ ] Mantener en `.env` únicamente parámetros que cambian entre entornos (número de jobs, timeouts, puertos, etc.).
- [ ] Reemplazar `.env` por `.env.example` en el repositorio y agregar `.env` al `.gitignore`.
- [ ] Revisar si `IGSISMANI_REPO_DIR` deja de ser necesario al usar `PROJECT_ROOT`.

## Organización de recursos

### Alta prioridad

- [ ] Crear `resources/` para centralizar todos los recursos multimedia.
- [ ] Mover `background.jpeg` a `resources/images/`.
- [ ] Mover `outro_xs.mp4` a `resources/videos/`.
- [ ] Mover `backsound.mp3` a `resources/audio/`.
- [ ] Versionar en Git todos los recursos necesarios para ejecutar IGSISMANI.
- [ ] Actualizar el código para usar rutas relativas a `PROJECT_ROOT` en lugar de rutas absolutas.

