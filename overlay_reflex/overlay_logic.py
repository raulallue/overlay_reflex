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
                # Leer solo el primer megabyte (XMP está en la cabecera)
                # Esto ahorra lectura de disco masiva en archivos de 30MB+
                contenido = f.read(1024 * 1024)
        else:
            # Si son bytes, tomamos solo el inicio por coherencia
            contenido = path_or_bytes[:1024 * 1024]

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

            # Mantener la imagen en RGB para ahorrar memoria (RGBA duplica el consumo)
            if img.mode != "RGB":
                img = img.convert("RGB")
            
            w, h = img.size
            
            # Altura del banner (6% de la altura total)
            banner_h = int(h * 0.06)
            if banner_h < 50: banner_h = 50
            
            # Crear el banner SOLO para la parte inferior (ahorro radical de RAM)
            banner = Image.new('RGBA', (w, banner_h), (0, 0, 0, 170))
            draw_bn = ImageDraw.Draw(banner)
            
            # Configurar fuente
            font_size = int(banner_h * 0.3)
            try:
                font_paths = [
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
                    "C:\\Windows\\Fonts\\arialbd.ttf"
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

            # Calcular posición centrada en el banner
            bbox = draw_bn.textbbox((0, 0), texto, font=font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
            
            tx = (w - text_w) // 2
            ty = (banner_h - text_h) // 2 - bbox[1]
            
            # Dibujar texto en el banner
            draw_bn.text((tx, ty), texto, fill="white", font=font)
            
            # Pegar el banner en la imagen original usando el propio banner como máscara para la transparencia
            img.paste(banner, (0, h - banner_h), banner)
            
            # Guardar como JPEG eficiente
            # Quitamos optimize=True porque en imágenes 4K/8K es extremadamente lento y causa timeouts
            img.save(output_path, "JPEG", quality=90)
            return True
    except Exception as e:
        print(f"Error procesando imagen {input_path}: {e}")
        return False
