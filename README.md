# Drone Overlay Reflex Tool

Una aplicación web moderna construida con **Reflex** para añadir overlays informativos a imágenes capturadas por drones DJI. Extrae metadatos directamente de las etiquetas XMP (Extensible Metadata Platform) incrustadas en las fotos.

## Características

- 📸 **Carga Multiple**: Sube varias imágenes simultáneamente.
- 🔍 **Extracción de Metadatos**: Obtiene automáticamente Latitud, Longitud, Altitud MSL y Altitud Relativa de DJI.
- 🖼️ **Overlay Automático**: Genera un banner semitransparente con toda la información técnica.
- 📥 **Gestión de Descargas**: 
  - Selección individual y en lote (Seleccionar Todo/Nada).
  - Descarga de imágenes seleccionadas.
  - Previsualización en cuadrícula interactiva.

## Requisitos

- Python 3.8 o superior
- Reflex
- Pillow (PIL)

## Instalación

1. Clona el repositorio o descarga los archivos.
2. Instala las dependencias:

```bash
pip install -r requirements.txt
```

## Ejecución

Para iniciar el servidor de desarrollo:

```bash
reflex run
```

La aplicación estará disponible por defecto en `http://localhost:3000`.

## Estructura del Proyecto

- `overlay_reflex/overlay_reflex.py`: Interfaz de usuario (Frontend) y lógica de estado.
- `overlay_reflex/overlay_logic.py`: Motor de procesamiento de imágenes y extracción de metadatos.
- `assets/`: Carpeta para recursos estáticos e imágenes procesadas.
- `rxconfig.py`: Configuración del proyecto Reflex.

## Créditos

Desarrollado por **Raúl Allué Sánchez**.
© 2026 RAS
