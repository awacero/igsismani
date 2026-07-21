# Notas tecnicas 

## Cómo entender un proyecto nuevo

### Concepto

Cuando estudies un proyecto que no conoces, no leas todos los archivos de principio a fin. Primero identifica el punto de entrada del caso de uso que quieres entender y sigue el flujo paso a paso.

### Método

1. Identifica el framework (FastAPI, Flask, Django, etc.).
2. Busca el punto de entrada:
   - `main()`
   - `@app.get(...)`
   - `@app.post(...)`
   - `if __name__ == "__main__"`
3. Pregunta:
   - ¿Quién llama a esta función?
   - ¿Qué función llama después?
4. Repite el proceso hasta llegar al resultado final.

### Ejemplo (FastAPI)

```python
@app.get("/tickets")
def create_ticket(...):
```

Flujo:

```text
Cliente
    │
GET /tickets
    │
FastAPI
    │
create_ticket()
    │
start_video_job()
    │
...
```

### ¿Por qué funciona?

En lugar de intentar comprender miles de líneas de código, solo necesitas responder repetidamente:

> ¿Quién llamó a esta función y a quién llama ella?

Así construyes un modelo mental del sistema de forma natural.

### Regla práctica

> Comprende primero el recorrido de una petición; después estudia los detalles de cada función.

** Nunca refactorizamos un módulo que no entendemos. ** 

Decidir qué problema resolver primero para maximizar el progreso y minimizar el riesgo.

Nota técnica

Maximizar el progreso

Resolver primero el problema que desbloquea más trabajo.

Minimizar el riesgo

Hacer cambios pequeños.
No mezclar varios objetivos.
Trabajar sobre código estable.
Verificar cada cambio antes de continuar.


## Orden de archivos 
En la raíz van únicamente los archivos que describen cómo construir, ejecutar o entender el proyecto.

Por ejemplo:

README.md
LICENSE
Dockerfile
docker-compose.yml
environment.yml
.gitignore
.env.example
pyproject.toml
Makefile      (si existe)

Todo lo demás debería vivir dentro de un directorio.



## Context Object y desempaquetado

### Concepto

Agrupar información relacionada en un único objeto (`runtime`, `event`) reduce la cantidad de parámetros entre funciones.

### Recomendación

Al inicio de cada función, desempaqueta únicamente las variables que esa función necesita.

```python
def generate_map_frames(runtime, event):
    frames_out = runtime["frames_out"]
    frames_number = runtime["frames_number"]

    latitude = event["latitude"]
    longitude = event["longitude"]
```

### ¿Por qué?

- El código es más legible.
- Evita repetir `runtime["..."]` muchas veces.
- Deja claro qué datos utiliza la función.

### No hacer

Desempaquetar todas las claves si la función solo usa unas pocas.

### Nota

Cuando el proyecto evolucione a `dataclass`, el acceso será aún más limpio:

```python
runtime.frames_out
event.latitude
```

**Nota técnica**

Configuración vs. acciones

Configuración: leer archivos, parámetros, rutas, URLs, tokens.
Acciones: conectarse a un servidor, consultar una API, leer una base de datos, generar archivos.


## El conocimiento debe vivir donde pertenece

### Concepto

Cada función debe ser responsable del conocimiento que le corresponde. Evita que otras partes del programa conozcan detalles internos de su implementación.

### Ejemplo

En lugar de:

```python
event_dict = load_event(runtime)

event_context = {
    "data": event_dict,
    "annotation": event_dict["annotation"],
    "latitude": event_dict["latitude"],
    "longitude": event_dict["longitude"],
}
```

es preferible:

```python
event_context = load_event(runtime)
```

### ¿Por qué?

- `main()` solo coordina el flujo.
- La estructura de `event_context` queda encapsulada en `load_event()`.
- Si cambia la estructura del evento, solo se modifica una función.

### Regla práctica

> El código que crea o conoce una estructura de datos debe ser el responsable de devolverla lista para usar.



## Funciones orquestadoras

### Concepto

Una función orquestadora no realiza todo el trabajo; coordina el flujo llamando a otras funciones especializadas.

### Ejemplo

En lugar de:

```python
def generate_animation():
    # 500 líneas de código
```

es preferible:

```python
def generate_animation(runtime, event):
    create_map_frames(runtime, event)
    create_info_frames(runtime, event)
    create_combined_frames(runtime, event)
    create_video(runtime, event)
```

### ¿Por qué?

- El flujo del programa se entiende de un vistazo.
- Cada función tiene una única responsabilidad.
- Es más fácil probar, depurar y reutilizar el código.

### Regla práctica

> Una función orquestadora debe decir **qué** se hace, no **cómo** se hace.

### Señales de que una función debe ser un orquestador

- Su nombre describe un proceso completo.
- Llama a varias funciones especializadas.
- Tiene poco código propio y mucha coordinación.
- Es posible leerla de arriba hacia abajo como si fuera un diagrama del proceso.

## Pipeline

### Concepto

Un pipeline es una secuencia de etapas donde la salida de una etapa sirve como entrada para la siguiente.

### Ejemplo

```text
Evento
   ↓
Crear mapas
   ↓
Crear información
   ↓
Combinar imágenes
   ↓
Crear video
   ↓
Agregar audio
```

### ¿Cuándo usarlo?

Cuando un proceso puede dividirse en pasos independientes ejecutados en un orden definido.

### Beneficios

- Cada etapa tiene una responsabilidad.
- El flujo es fácil de entender.
- Permite modificar o reemplazar una etapa sin afectar las demás.

### Regla práctica

> Si puedes describir un proceso como "primero..., luego..., después...", probablemente estás frente a un pipeline.

