from __future__ import annotations

import logging
import shutil
from pathlib import Path


log = logging.getLogger("mkdocs")
ROOT_DIR = Path(__file__).resolve().parent
IMAGE_DIR = ROOT_DIR / "image"


def on_post_build(config, **kwargs) -> None:
    """Expose the repo-root image directory as site/image."""
    if not IMAGE_DIR.is_dir():
        log.warning("Static image directory not found: %s", IMAGE_DIR)
        return

    site_dir = Path(config["site_dir"]).resolve()
    target_dir = site_dir / "image"

    if target_dir.exists():
        shutil.rmtree(target_dir)

    shutil.copytree(IMAGE_DIR, target_dir)
    log.info("Copied static assets: %s -> %s", IMAGE_DIR, target_dir)
