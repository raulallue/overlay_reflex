import reflex as rx
import os
import uuid
import shutil
import zipfile
import io
import asyncio
from datetime import datetime
import time # Moved import time to the top level
from rxconfig import config
from .overlay_logic import procesar_imagen_overlay

import pydantic
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse, JSONResponse

class ProcessedImage(pydantic.BaseModel):
    name: str
    url: str
    selected: bool = True
    status: str = "success"

class State(rx.State):
    """The app state."""
    # The images being uploaded
    is_processing: bool = False
    progress: int = 0
    total_files: int = 0
    processed_count: int = 0
    processed_images: list[ProcessedImage] = []
    
    @rx.var
    def has_selection(self) -> bool:
        return any(getattr(img, "selected", True) for img in self.processed_images)

    def on_load(self):
        """Cleanup logic when the page loads."""
        # Clean up files older than 30 minutes in the processed directory
        import time
        processed_dir = os.path.join("assets", "processed")
        if os.path.exists(processed_dir):
            current_time = time.time()
            for sid_dir in os.listdir(processed_dir):
                dir_path = os.path.join(processed_dir, sid_dir)
                if os.path.isdir(dir_path):
                    # Check the folder modification time
                    if current_time - os.path.getmtime(dir_path) > 1800: # 30 mins
                        shutil.rmtree(dir_path)

    # List of filenames to skip during upload
    files_to_remove: list[str] = []

    def get_session_id(self) -> str:
        """Get a stable session identifier for the current client."""
        try:
            # Standard way in Reflex 0.8.x
            return self.router.session.client_token
        except (AttributeError, Exception):
            # Fallback for some versions or contexts
            return self.get_token()

    async def handle_upload(self, files: list[rx.UploadFile]):
        """Handle the upload and processing of multiple images."""
        if not files:
            return
        
        # Filter out files that were manually removed by the user
        valid_files = [f for f in files if f.filename not in self.files_to_remove]
        if not valid_files:
            return

        self.is_processing = True
        self.progress = 0
        self.processed_count = 0
        self.total_files = len(valid_files)
        yield
        
        # Ensure session-specific processed directory exists
        session_id = self.get_session_id()
        session_processed_dir = os.path.join("assets", "processed", session_id)
        if not os.path.exists(session_processed_dir):
            os.makedirs(session_processed_dir, exist_ok=True)

        self.processed_images = []
        
        # Ensure API_URL has a protocol for the browser to reach it correctly
        api_url = config.api_url
        if not api_url.startswith(("http://", "https://")):
            api_url = f"http://{api_url}"

        for file in valid_files:
            upload_data = await file.read()
            # Save uploaded file temporarily to process it
            temp_path = os.path.join("assets", f"{session_id}_{file.filename}")
            with open(temp_path, "wb") as f:
                f.write(upload_data)
            
            # Define output path
            output_filename = f"overlay_{file.filename}"
            output_path = os.path.join(session_processed_dir, output_filename)
            
            # Process the image
            success = procesar_imagen_overlay(temp_path, output_path)
            
            if success:
                # Cache-busting timestamp
                ts = int(time.time() * 1000)
                # Ensure API_URL has a protocol and is correctly resolved from environment
                api_url = os.environ.get("API_URL", config.api_url).rstrip("/")
                if not api_url.startswith(("http://", "https://")):
                    api_url = f"http://{api_url}"
                
                # If it's still localhost but we're in Docker, we warn
                print(f"Processing for image {file.filename} using API_URL: {api_url}")
                
                self.processed_images.append(
                    ProcessedImage(
                        name=file.filename,
                        # Use absolute URL to reach the backend static mount directly
                        url=f"{api_url}/processed/{session_id}/{output_filename}?t={ts}",
                        selected=True
                    )
                )
            
            # Clean up temporary uploaded file
            if os.path.exists(temp_path):
                os.remove(temp_path)
            
            self.processed_count += 1
            self.progress = int((self.processed_count / self.total_files) * 100)
            yield

        self.is_processing = False

    def toggle_select(self, name: str):
        """Toggle the selection of a specific image."""
        self.processed_images = [
            ProcessedImage(
                name=img.name,
                url=img.url,
                selected=not getattr(img, "selected", True) if img.name == name else getattr(img, "selected", True),
                status=img.status
            )
            for img in self.processed_images
        ]

    def select_all(self):
        """Select all processed images."""
        self.processed_images = [
            ProcessedImage(name=img.name, url=img.url, selected=True, status=img.status)
            for img in self.processed_images
        ]

    def select_none(self):
        """Deselect all processed images."""
        self.processed_images = [
            ProcessedImage(name=img.name, url=img.url, selected=False, status=img.status)
            for img in self.processed_images
        ]

    def remove_from_upload(self, name: str):
        """Add a filename to the list of files to skip during processing."""
        self.files_to_remove.append(name)

    def clear_processed(self):
        """Clear all processed images and files for the current session."""
        self.processed_images = []
        self.files_to_remove = []
        self.progress = 0
        self.processed_count = 0
        session_id = self.get_session_id()
        session_processed_dir = os.path.join("assets", "processed", session_id)
        if os.path.exists(session_processed_dir):
            shutil.rmtree(session_processed_dir)
            os.makedirs(session_processed_dir)
        return rx.clear_selected_files("upload_images")

    async def download_selected(self):
        """Download all selected images one by one using JavaScript to avoid browser navigation issues."""
        urls = [img.url for img in self.processed_images if getattr(img, "selected", False)]
        if not urls:
            return
        
        # Trigger multiple downloads via client-side script
        # We use a small delay between each to bypass some browser security limitations
        urls_json = str(urls).replace("'", '"') # Simple JSON-safe list
        script = f"""
        const urls = {urls_json};
        urls.forEach((url, i) => {{
            setTimeout(() => {{
                const link = document.body.appendChild(document.createElement('a'));
                link.href = url;
                link.setAttribute('download', '');
                link.click();
                document.body.removeChild(link);
            }}, i * 800); // 800ms delay for stability
        }});
        """
        return rx.call_script(script)

    async def download_zip(self):
        """Compress selected images into a ZIP and download it asynchronously."""
        selected_images = [img for img in self.processed_images if getattr(img, "selected", False)]
        if not selected_images:
            return
        
        # Update UI to show we are zipping
        self.is_processing = True
        self.progress = 0
        yield

        # Ensure session-specific processed directory exists
        session_id = self.get_session_id()
        session_processed_dir = os.path.join("assets", "processed", session_id)
        zip_filename = f"images_{session_id}.zip"
        zip_path = os.path.join(session_processed_dir, zip_filename)
        
        # Build image list
        images_to_zip = []
        for img in selected_images:
            clean_url = img.url.split('?')[0]
            image_filename = os.path.basename(clean_url)
            real_image_path = os.path.join(session_processed_dir, image_filename)
            if os.path.exists(real_image_path):
                images_to_zip.append((real_image_path, image_filename))

        # Perform zipping in a background thread to keep backend responsive
        def create_zip():
            with zipfile.ZipFile(zip_path, 'w') as zipf:
                for path, name in images_to_zip:
                    zipf.write(path, arcname=name)
        
        import asyncio
        await asyncio.to_thread(create_zip)
        
        self.progress = 100
        self.is_processing = False
        yield

        # Ensure API_URL has a protocol
        api_url = os.environ.get("API_URL", config.api_url)
        if not api_url.startswith(("http://", "https://")):
            api_url = f"http://{api_url}"

        # Using a hard redirect to bypass the Reflex router for direct downloads
        yield rx.call_script(f"window.location.href = '{api_url}/processed/{session_id}/{zip_filename}'")

def index() -> rx.Component:
    return rx.box(
        rx.center(
            rx.vstack(
                # Header Section
                rx.vstack(
                    rx.heading("Image Overlay", size="9", weight="bold", color_scheme="blue", letter_spacing="-0.02em"),
                    rx.text("Procesamiento por lotes de metadatos en imágenes", size="4", color_scheme="gray", opacity=0.8, text_align="center"),
                    rx.link(
                        rx.hstack(
                            rx.icon("monitor", size=16),
                            rx.text("Software para windows", weight="medium"),
                            spacing="2",
                            align_items="center",
                        ),
                        href="/Overlay.zip",
                        is_external=True,
                        variant="soft",
                        color_scheme="blue",
                        size="1",
                        margin_top="0.5em",
                        padding_x="12px",
                        padding_y="4px",
                        border_radius="full",
                    ),
                    spacing="2",
                    align_items="center",
                    text_align="center",
                    padding_y="3em",
                    width="100%",
                ),
                
                # Main Tool Card
                rx.card(
                    rx.vstack(
                        # Upload Area
                        rx.upload(
                            rx.vstack(
                                rx.icon("upload", size=30, color="blue"),
                                rx.text("Arrastra las imágenes o haz clic", font_weight="500"),
                                rx.text(".jpg, .jpeg", size="2", color_scheme="gray"),
                                spacing="2",
                                align_items="center",
                                padding="3em",
                            ),
                            id="upload_images",
                            border="2px dashed rgba(66, 153, 225, 0.3)",
                            bg="rgba(66, 153, 225, 0.05)",
                            border_radius="xl",
                            multiple=True,
                            width="100%",
                            accept={"image/jpeg": [".jpg", ".jpeg"]},
                        ),
                        
                        rx.hstack(
                            rx.button(
                                "Procesar",
                                on_click=State.handle_upload(rx.upload_files(upload_id="upload_images")),
                                loading=State.is_processing,
                                color_scheme="blue",
                                flex="1",
                                size="3",
                            ),
                            rx.button(
                                "Limpiar",
                                on_click=State.clear_processed,
                                variant="outline",
                                color_scheme="red",
                                flex="1",
                                size="3",
                            ),
                            spacing="3",
                            width="100%",
                            margin_top="1.5em",
                        ),

                        # Progress Indicator
                        rx.cond(
                            State.is_processing,
                            rx.vstack(
                                rx.progress(value=State.progress, width="100%", size="1", color_scheme="blue"),
                                rx.text(f"Completado {State.progress}%", size="1", color_scheme="gray"),
                                width="100%",
                                spacing="1",
                                padding_top="1em",
                            )
                        ),
                        
                        width="100%",
                        padding="1.5em",
                    ),
                    width="100%",
                    variant="ghost",
                    box_shadow="0 4px 20px rgba(0,0,0,0.05)",
                    border="1px solid rgba(0,0,0,0.05)",
                    border_radius="2xl",
                ),

                # Selected Files List with removal
                rx.cond(
                    rx.selected_files("upload_images"),
                    rx.vstack(
                        rx.text("Archivos listos para procesar:", size="2", weight="bold", margin_top="1.5em", width="100%"),
                        rx.flex(
                            rx.foreach(
                                rx.selected_files("upload_images"),
                                lambda name: rx.cond(
                                    ~State.files_to_remove.contains(name),
                                    rx.badge(
                                        rx.hstack(
                                            rx.text(name, size="1"),
                                            rx.icon(
                                                "x", 
                                                size=12, 
                                                color="red", 
                                                cursor="pointer",
                                                on_click=lambda: State.remove_from_upload(name)
                                            ),
                                            spacing="1",
                                            align_items="center",
                                        ),
                                        variant="soft",
                                        color_scheme="gray",
                                        radius="full",
                                        padding_x="10px",
                                    ),
                                    rx.fragment()
                                )
                            ),
                            spacing="2",
                            flex_wrap="wrap",
                            width="100%",
                        ),
                        width="100%",
                    )
                ),
                
                # Results Section
                rx.cond(
                    State.processed_images,
                    rx.vstack(
                        rx.hstack(
                            rx.text(f"{State.processed_images.length()} imágenes procesadas", weight="bold"),
                            rx.spacer(),
                            rx.menu.root(
                                rx.menu.trigger(
                                    rx.button(
                                        rx.hstack(
                                            rx.text("Acciones"),
                                            rx.icon("chevron-down", size=16),
                                            spacing="2",
                                            align_items="center",
                                        ),
                                        variant="soft", 
                                        size="2",
                                    )
                                ),
                                rx.menu.content(
                                    rx.menu.item("Seleccionar Todas", on_click=State.select_all),
                                    rx.menu.item("Deseleccionar Todas", on_click=State.select_none),
                                    rx.menu.separator(),
                                    rx.menu.item("Descargar ZIP", on_click=State.download_zip),
                                    rx.menu.item("Descargar Individuales", on_click=State.download_selected),
                                ),
                            ),
                            width="100%",
                            align_items="center",
                            margin_top="3em",
                            margin_bottom="1em",
                        ),
                        
                        rx.grid(
                            rx.foreach(
                                State.processed_images,
                                lambda img: rx.card(
                                    rx.vstack(
                                        rx.box(
                                            rx.image(src=img.url, width="100%", aspect_ratio="1", object_fit="cover", border_radius="lg"),
                                            rx.checkbox(
                                                checked=img.selected,
                                                on_change=lambda _: State.toggle_select(img.name),
                                                position="absolute",
                                                top="8px",
                                                left="8px",
                                                size="2",
                                                bg="white",
                                                border_radius="md",
                                            ),
                                            position="relative",
                                            width="100%",
                                        ),
                                        rx.hstack(
                                            rx.text(img.name, size="1", weight="medium", overflow="hidden", white_space="nowrap", text_overflow="ellipsis"),
                                            rx.spacer(),
                                            rx.link(
                                                rx.icon("download", size=14, color="blue"),
                                                href=img.url,
                                                is_external=True,
                                                cursor="pointer",
                                            ),
                                            width="100%",
                                            padding_x="4px",
                                        ),
                                        spacing="2",
                                    ),
                                    variant="ghost",
                                    padding="0.5em",
                                    border_radius="xl",
                                )
                            ),
                            columns=rx.breakpoints(initial="2", sm="3", md="4"),
                            spacing="4",
                            width="100%",
                        ),
                        width="100%",
                    ),
                    # Empty state (Subtle)
                    rx.fragment()
                ),
                
                # Footer Section
                rx.hstack(
                    rx.text(f"© {datetime.now().year} Image Overlay. Todos los derechos reservados.", size="1", color_scheme="gray"),
                    rx.spacer(),
                    rx.text("v1.0.0", size="1", color_scheme="gray"),
                    width="100%",
                    padding_y="2em",
                    border_top="1px solid rgba(0,0,0,0.05)",
                    margin_top="3em",
                ),
                
                max_width="700px",
                width="100%",
                padding_x="2em",
                padding_bottom="5em",
                align_items="center",
            ),
        ),
        min_height="100vh",
        bg="white",
    )

app = rx.App(
    stylesheets=[
        "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap",
        "custom.css", # Local CSS for watermark removal and tweaks
    ],
    style={
        "font_family": "Inter, sans-serif",
    },
    admin_dash=None,
    overlay_component=None,
)
app.add_page(index, title="Image Overlay", on_load=State.on_load)

# Custom Starlette route to serve processed files and force downloads
# This replaces the static mount to provide correct Content-Disposition headers
async def download_processed_file(request):
    session_id = request.path_params.get("session_id")
    filename = request.path_params.get("filename")
    file_path = os.path.join("assets", "processed", session_id, filename)
    if os.path.exists(file_path):
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type='application/octet-stream'
        )
    return JSONResponse({"error": "File not found"}, status_code=404)

app._api.add_route("/processed/{session_id}/{filename}", download_processed_file, methods=["GET"])

# Custom Starlette route to serve the Windows software directly from assets
async def download_software(request):
    file_path = os.path.join("assets", "Overlay.zip")
    if os.path.exists(file_path):
        return FileResponse(
            path=file_path,
            filename="Overlay.zip",
            media_type='application/octet-stream'
        )
    return JSONResponse({"error": "Software for Windows not found in assets/"}, status_code=404)

app._api.add_route("/Overlay.zip", download_software, methods=["GET"])
