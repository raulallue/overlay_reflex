# Image Overlay 🚀

**Image Overlay** es una herramienta web profesional diseñada para el procesamiento por lotes de imágenes, especializada en la superposición de metadatos (específicamente datos DJI como altura, coordenadas y fecha).

![Favicon](assets/favicon.ico)

## ✨ Características

- **Procesamiento Masivo**: Sube múltiples imágenes `.jpg` / `.jpeg` simultáneamente.
- **Extracción de Metadatos**: Lee automáticamente la altitud, fecha y coordenadas de los metadatos EXIF de drones DJI.
- **Superposición Elegante**: Añade un banner semitransparente con tipografía profesional (*DejaVu Sans Bold*).
- **Gestión de Sesiones**: Aislamiento total de archivos por sesión de usuario.
- **Descargas Flexibles**: 
  - Descarga de imágenes individuales procesadas.
  - Generación de archivos ZIP para descargas por lotes.
  - Enlace directo a software de escritorio complementario (`Overlay.zip`).
- **Arquitectura de Producción**: Totalmente preparada para Docker (multi-plataforma) y proxy Nginx con SSL.

## 🛠️ Tecnologías

- **Reflex**: Framework web de alto rendimiento basado en Python y Next.js.
- **Pillow (PIL)**: Motor de procesamiento de imágenes.
- **FastAPI / Starlette**: Gestión de rutas personalizadas para descargas seguras.
- **Docker**: Despliegue en contenedores optimizado.
- **Nginx**: Proxy inverso para seguridad y SSL.

## 🚀 Despliegue Rápido (Docker)

### 1. Construir la Imagen (Multi-plataforma)
```bash
docker buildx build --platform linux/amd64,linux/arm64 -t rallue/image-overlay:latest --push .
```

### 2. Configuración en Portainer / Docker Compose
Asegúrate de configurar las siguientes variables de entorno:
- `API_URL`: `https://tu-dominio.com` (IMPORTANTE: Sin barra final).

### 3. Proxy Nginx (Recomendado)
Asegúrate de configurar Nginx para manejar WebSockets y aumentar el límite de subida:
```nginx
client_max_body_size 100M;
location /_event {
    proxy_pass http://ip-servidor:8002;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
}
```

## 📂 Estructura del Proyecto

- `overlay_reflex/`: Carpeta principal de la aplicación.
  - `overlay_reflex.py`: Lógica principal del estado y UI.
  - `overlay_logic.py`: Motor de procesamiento de imágenes.
- `assets/`: Archivos estáticos, iconos y software complementario.
- `Dockerfile`: Configuración del contenedor de producción.
- `rxconfig.py`: Configuración global de Reflex.

## 📝 Licencia
© 2026 Image Overlay. Todos los derechos reservados.
