import os
import re
from PIL import Image, ImageDraw, ImageFont, TiffImagePlugin
import io

def convertir_racional_a_decimal(coord, ref):
    """Convierte coordenadas EXIF (grados, minutos, segundos) a decimal."""
    if not coord or not ref:
        return 'N/A'
    
    # Pillows EXIF parser returns a tuple of rationals
    # e.g., ((41, 1), (7, 1), (300, 10)) -> 41 deg, 7 min, 30 sec
    try:
        grados = float(coord[0])
        minutos = float(coord[1])
        segundos = float(coord[2])
        
        decimal = grados + (minutos / 60.0) + (segundos / 3600.0)
        if ref in ['S', 'W']:
            decimal = -decimal
        return f"{decimal:+.6f}"
    except (IndexError, TypeError, ZeroDivisionError):
        return 'N/A'

def obtener_metadatos_dji(path_or_bytes, debug_path=None):
    """
    Extrae metadatos DJI (Lat, Lon, Alt MSL, Rel Alt) de una imagen.
    Soporta XMP (regex) y EXIF (exhaustivo) con depuración opcional.
    """
    datos = {'lat': 'N/A', 'lon': 'N/A', 'alt_msl': 'N/A', 'rel_alt': 'N/A'}
    debug_log = []
    
    try:
        if isinstance(path_or_bytes, str):
            with open(path_or_bytes, 'rb') as f:
                # Leer solo el primer megabyte para XMP
                contenido = f.read(1024 * 1024)
        else:
            contenido = path_or_bytes[:1024 * 1024]

        debug_log.append("--- INICIO EXTRACCION METADATOS ---")

        # Patrones para metadatos XMP de DJI
        # Soportamos: Atributos="valor", <Elemento>valor</Elemento>, y errores de DJI como "GpsLongtitude"
        # Usamos regex insensibles a mayúsculas y prefijos de namespace opcionales
        
        search_configs = {
            'rel_alt': [
                rb'(?:[\w-]*:)?RelativeAltitude=["\']([^"\']+)["\']',
                rb'<(?:[\w-]*:)?RelativeAltitude>([^<]+)</(?:[\w-]*:)?RelativeAltitude>'
            ],
            'alt_msl': [
                rb'(?:[\w-]*:)?AbsoluteAltitude=["\']([^"\']+)["\']',
                rb'<(?:[\w-]*:)?AbsoluteAltitude>([^<]+)</(?:[\w-]*:)?AbsoluteAltitude>'
            ],
            'lat': [
                rb'(?:[\w-]*:)?GpsLatitude=["\']([^"\']+)["\']',
                rb'<(?:[\w-]*:)?GpsLatitude>([^<]+)</(?:[\w-]*:)?GpsLatitude>'
            ],
            'lon': [
                rb'(?:[\w-]*:)?GpsLong(?:i|ti)tude=["\']([^"\']+)["\']', # Soportamos typo "GpsLongtitude"
                rb'<(?:[\w-]*:)?GpsLong(?:i|ti)tude>([^<]+)</(?:[\w-]*:)?GpsLong(?:i|ti)tude>'
            ]
        }
        
        for clave, patrones in search_configs.items():
            for pattern in patrones:
                match = re.search(pattern, contenido, re.IGNORECASE)
                if match:
                    valor = match.group(1).decode('utf-8')
                    datos[clave] = valor
                    debug_log.append(f"XMP MATCH [{clave}]: {valor}")
                    break
        
        # --- Fallback a EXIF estándar exhaustivo ---
        try:
            from PIL import ExifTags
            with Image.open(io.BytesIO(path_or_bytes) if isinstance(path_or_bytes, bytes) else path_or_bytes) as img:
                exif = img.getexif()
                
                # Función interna para procesar un IFD entero
                def procesar_ifd(ifd_data, label):
                    debug_log.append(f"--- Escaneando {label} ---")
                    for tag, value in ifd_data.items():
                        tag_name = ExifTags.TAGS.get(tag, ExifTags.GPSTAGS.get(tag, f"Unknown_{tag}"))
                        debug_log.append(f"  Tag {tag} ({tag_name}): {value}")
                        
                        # Buscar coordenadas si aún no las tenemos
                        if "Latitude" in str(tag_name) and "Ref" not in str(tag_name):
                            if datos['lat'] == 'N/A':
                                ref = ifd_data.get(tag-1) # Asumir que el Ref está antes (estándar)
                                if not ref: ref = ifd_data.get(1) # Fallback al tag 1 global
                                res = convertir_racional_a_decimal(value, ref)
                                if res != 'N/A': datos['lat'] = res
                        
                        if "Longitude" in str(tag_name) and "Ref" not in str(tag_name):
                            if datos['lon'] == 'N/A':
                                ref = ifd_data.get(tag-1)
                                if not ref: ref = ifd_data.get(3)
                                res = convertir_racional_a_decimal(value, ref)
                                if res != 'N/A': datos['lon'] = res
                        
                        if "Altitude" in str(tag_name) and "Ref" not in str(tag_name):
                            if datos['alt_msl'] == 'N/A':
                                try:
                                    datos['alt_msl'] = f"{float(value):.1f}"
                                except: pass

                # Escanear IFD principal y sub-IFDs comunes
                procesar_ifd(exif, "IFD Principal")
                # El tag GPS es 0x8825
                gps_ifd = exif.get_ifd(0x8825)
                if gps_ifd: procesar_ifd(gps_ifd, "GPS IFD")
                
        except Exception as exif_e:
            debug_log.append(f"Error EXIF detallado: {exif_e}")

    except Exception as e:
        debug_log.append(f"Error General: {e}")
    
    if debug_path and debug_log:
        try:
            with open(debug_path, 'w') as df:
                df.write("\n".join(debug_log))
        except: pass
    
    return datos

def procesar_imagen_overlay(input_path, output_path, copyright_text="© RAS"):
    """
    Añade un overlay con metadatos a la imagen.
    """
    # Generar ruta de depuración automática en la misma carpeta que el output
    debug_path = output_path + ".debug.txt"
    meta = obtener_metadatos_dji(input_path, debug_path=debug_path)
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
