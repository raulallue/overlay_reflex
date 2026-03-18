import os
import re
from PIL import Image, ImageDraw, ImageFont
import io

def obtener_metadatos_dji(path_or_bytes):
    """
    Extrae metadatos DJI (Lat, Lon, Alt MSL, Rel Alt) de una imagen (ruta o bytes).
    """
    datos = {'lat': 'N/A', 'lon': 'N/A', 'alt_msl': 'N/A', 'rel_alt': 'N/A'}
    try:
        if isinstance(path_or_bytes, str):
            with open(path_or_bytes, 'rb') as f:
                contenido = f.read()
        else:
            contenido = path_or_bytes

        # Patrones para metadatos XMP de DJI
        patterns = {
            'rel_alt': b'RelativeAltitude="([^"]+)"',
            'alt_msl': b'AbsoluteAltitude="([^"]+)"',
            'lat': b'GpsLatitude="([^"]+)"',
            'lon': b'GpsLongitude="([^"]+)"'
        }
        
        for clave, pattern in patterns.items():
            match = re.search(pattern, contenido)
            if match:
                datos[clave] = match.group(1).decode('utf-8')
    except Exception as e:
        print(f"Error extrayendo metadatos: {e}")
    
    return datos

def procesar_imagen_overlay(input_path, output_path, copyright_text="© RAS"):
    """
    Añade un overlay con metadatos a la imagen.
    """
    meta = obtener_metadatos_dji(input_path)
    texto = f"LAT: {meta['lat']} | LON: {meta['lon']} | ALT (MSL): {meta['alt_msl']}m | RELATIVE ALT: {meta['rel_alt']}m | {copyright_text}"

    try:
        with Image.open(input_path) as img:
            # Corregir orientación EXIF si es necesario
            try:
                from PIL import ImageOps
                img = ImageOps.exif_transpose(img)
            except:
                pass

            img = img.convert("RGBA")
            w, h = img.size
            
            # Altura del banner (5% de la altura total)
            banner_h = int(h * 0.05)
            if banner_h < 30: banner_h = 30 # Mínimo razonable
            
            # Crear overlay semitransparente
            overlay = Image.new('RGBA', (w, h), (0, 0, 0, 0))
            draw_ov = ImageDraw.Draw(overlay)
            # Dibujar rectángulo en el fondo
            draw_ov.rectangle([0, h - banner_h, w, h], fill=(0, 0, 0, 170))
            
            # Combinar
            img = Image.alpha_composite(img, overlay)
            
            # Configurar fuente
            font_size = int(banner_h * 0.40)
            try:
                # Intentar cargar una fuente común en Mac/Linux/Windows
                font_paths = [
                    "/System/Library/Fonts/Supplemental/Arial Bold.ttf", # Mac
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", # Linux
                    "C:\\Windows\\Fonts\\arialbd.ttf" # Windows
                ]
                font = None
                for p in font_paths:
                    if os.path.exists(p):
                        font = ImageFont.truetype(p, font_size)
                        break
                if font is None:
                    font = ImageFont.load_default()
            except:
                font = ImageFont.load_default()

            draw = ImageDraw.Draw(img)
            
            # Calcular posición centrada
            bbox = draw.textbbox((0, 0), texto, font=font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
            
            tx = (w - text_w) // 2
            ty = h - banner_h + (banner_h - text_h) // 2 - bbox[1]
            
            draw.text((tx, ty), texto, fill="white", font=font)
            
            # Guardar como JPEG
            img.convert("RGB").save(output_path, quality=90, optimize=True)
            return True
    except Exception as e:
        print(f"Error procesando imagen {input_path}: {e}")
        return False
