from pathlib import Path

from app.core import config


def get_storage_root() -> Path:
    return Path(config.STORAGE_ROOT)
