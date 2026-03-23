import reflex as rx
import os

# Exclude processed assets from hot-reload to avoid worker kills during batch processing
os.environ["REFLEX_EXCLUDE_HOT_RELOAD_PATHS"] = os.path.join(os.getcwd(), "assets", "processed")

config = rx.Config(
    app_name="overlay_reflex",
    show_built_with_reflex=False,
    plugins=[
        rx.plugins.SitemapPlugin(),
        rx.plugins.TailwindV4Plugin(),
    ]
)