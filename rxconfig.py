import reflex as rx

config = rx.Config(
    app_name="overlay_reflex",
    show_built_with_reflex=False,
    plugins=[
        rx.plugins.SitemapPlugin(),
        rx.plugins.TailwindV4Plugin(),
    ]
)