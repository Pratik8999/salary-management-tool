import os


def _env(key: str, default: str) -> str:
    value = os.getenv(key)
    return value if value not in (None, "") else default


JWT_SECRET: str = _env("JWT_SECRET", "dev-insecure-change-me-dev-insecure-change-me")
JWT_ALGORITHM: str = _env("JWT_ALGORITHM", "HS256")
JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = int(_env("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

STORAGE_ROOT: str = _env("STORAGE_ROOT", "storage/documents")
DOCUMENT_MAX_BYTES: int = int(_env("DOCUMENT_MAX_BYTES", str(5 * 1024 * 1024)))
DOCUMENT_ALLOWED_CONTENT_TYPES: frozenset[str] = frozenset(
    {"application/pdf", "image/png", "image/jpeg"}
)
