"""Configuration for the brand package."""

import os
from config2py import get_app_config_folder, process_path

APP_DIR = get_app_config_folder("brand")

PIPELINES_DIR = os.environ.get(
    "BRAND_PIPELINES_DIR",
    process_path(
        os.path.join(APP_DIR, "pipelines"),
        ensure_dir_exists=True,
    ),
)

DEFAULT_PIPELINE = os.environ.get("BRAND_DEFAULT_PIPELINE", "quick_screen")

# Domain search storage (backward compat with existing code)
DOMAIN_SEARCH_DIR = process_path(
    os.path.join(APP_DIR, "domain_search"),
    ensure_dir_exists=True,
)
