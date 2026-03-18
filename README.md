# Image Overlay

Una aplicación web moderna y profesional construida con **Reflex** para añadir overlays informativos a imágenes (optimizada para drones DJI). Extrae metadatos técnicos y los presenta de forma elegante en un banner integrado.

![Interfaz Principal](file:///Users/raul/.gemini/antigravity/brain/ee598613-069b-4a9f-9a23-c3aff42c3d90/verify_buttons_alignment_1773862197803.png)

## Características

- 📸 **Carga Inteligente**: Arrastra y suelta múltiples imágenes.
- ✂️ **Curación Previa**: Lista de archivos con la opción de eliminar elementos individuales antes de procesar.
- 🔍 **Extracción de Metadatos**: Obtiene automáticamente Latitud, Longitud, Altitud MSL y Altitud Relativa.
- 🖼️ **Overlay Premium**: Banner con diseño limpio, tipografía moderna y transparencia.
- ⚡ **Feedback en Tiempo Real**: Barra de progreso y cuadrícula de resultados instantánea.
- 📥 **Exportación Flexible**: 
  - Selección individual y masiva.
  - Descarga de archivos individuales con su extensión correcta (.JPG).
  - Descarga masiva en formato **ZIP**.
- 🔒 **Privacidad y Seguridad**: 
  - Sesiones aisladas por usuario.
  - Limpieza automática de archivos temporales cada 30 minutos.
  - Sincronización perfecta de miniaturas mediante cache-busting.

## Requisitos

- Python 3.12 o superior
- Reflex 0.8.28+
- Pillow (PIL)

## Instalación

1. Clona el repositorio.
2. Crea un entorno virtual e instálalo:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Ejecución

Para iniciar la aplicación:

```bash
reflex run
```

La aplicación estará disponible en `http://localhost:3000`.

## Despliegue con Docker (Producción)

Si deseas ejecutar la aplicación en un contenedor Docker, sigue estos pasos:

1. **Construir y levantar**:

```bash
docker-compose up --build -d
```

2. **Acceso**:
   - Frontend: `http://localhost:3002`
   - Backend API: `http://localhost:8002`

> [!NOTE]
> En entornos de producción, asegúrate de actualizar la variable `API_URL` en el archivo `docker-compose.yml` con la IP pública o dominio de tu servidor.

## Construir y Subir a Docker Hub

Sigue estos pasos para empaquetar y subir tu imagen a Docker Hub:

1. **Iniciar sesión**:
   ```bash
   docker login
   ```

2. **Construir la imagen**:
   ```bash
   docker build -t <tu-usuario>/image-overlay:latest .
   ```

3. **Subir la imagen**:
   ```bash
   docker push <tu-usuario>/image-overlay:latest
   ```

## Estructura del Proyecto

- `overlay_reflex/overlay_reflex.py`: Frontend de Reflex y gestión de estado.
- `overlay_reflex/overlay_logic.py`: Extracción de metadatos XMP y motor de procesamiento de imágenes.
- `assets/`: Recursos estáticos (favicon, estilos) y almacenamiento temporal de sesiones.
- `rxconfig.py`: Configuración global del proyecto.

## Créditos

Desarrollado por **Raúl Allué Sánchez**.
© 2026 RAS
