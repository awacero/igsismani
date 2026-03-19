# Capítulo 2. Arquitectura del Sistema – IGSISMANI

## 2.1 Descripción general de la arquitectura
El sistema IGSISMANI se implementará como una aplicación web construida con FastAPI.  
La arquitectura sigue un modelo asíncrono basado en tickets, donde cada solicitud de generación de video crea una tarea en segundo plano y un directorio temporal asociado al ticket. El usuario consulta el estado y descarga el video final cuando esté listo.

Los componentes están desacoplados y organizados en módulos especializados según la responsabilidad: obtención de datos sísmicos, generación de animaciones, construcción del video, envío de correo y administración del ciclo de vida del ticket.

La estructura soporta dos entradas principales:
1. Entrada manual mediante `run_igsismani.py`.
2. Entrada mediante API web en `igsismani/api/main.py`.

## 2.2 Componentes principales del sistema
1. Componente API (FastAPI)  
2. Módulo de autenticación  
3. Módulo de obtención de datos sísmicos  
4. Módulo de animación  
5. Módulo de composición y exportación de video  
6. Módulo de correo electrónico  
7. Módulo de almacenamiento en repositorio institucional  
8. Servicio cron para limpieza de tickets  
9. Entry point local `run_igsismani.py`  

## 2.3 Diagramas de arquitectura

Los siguientes diagramas PlantUML se proporcionan como archivos separados:

- `component_diagram.puml`
- `deployment_diagram.puml`

## 2.4 Flujo interno de ejecución

El flujo del sistema se describe mediante un diagrama UML de secuencia incluido en `sequence_diagram.puml`.

## 2.5 Diseño del almacenamiento temporal

Cada solicitud genera un directorio `tmp/{ticket_id}/` y un archivo `status.json` que contiene información del progreso.

Ejemplo de `status.json`:

```json
{
  "ticket": "9570d3e2-82e1-4d8d-a193-732f1eaab02c",
  "status": "processing",
  "message": "Generando animación",
  "started_at": "2025-02-17T10:43:15",
  "updated_at": "2025-02-17T10:43:15"
}
```

## 2.6 Especificaciones de comunicación entre módulos

- Comunicación entre módulos mediante funciones internas.  
- Formato JSON para estados temporales.  
- Logs centralizados usando logging.ini.  
- Manejo de errores mediante excepciones controladas.  
- Uso de SMTP, FDSN y repositorio institucional como servicios externos.

## 2.7 Restricciones de diseño

- Prioridad a mantenibilidad.  
- Arquitectura modular.  
- Sin publicación automática en redes sociales.  
- FastAPI obligatorio.  
