import os
import uuid
from pathlib import Path

ALLOWED_MIME_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
}

MAGIC_SIGNATURES = [
    (b"\x89PNG\r\n\x1a\n", ".png"),
    (b"\xff\xd8\xff", ".jpg"),
    (b"GIF87a", ".gif"),
    (b"GIF89a", ".gif"),
    (b"RIFF", ".webp"),
]

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


class MediaValidationError(Exception):
    pass


class MediaService:

    def __init__(self, base_upload_dir: str | None = None):
        if base_upload_dir is None:
            base_upload_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "uploads",
                "media"
            )
        self.upload_dir = Path(base_upload_dir).resolve()
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    def validate_and_save_image(self, file_bytes: bytes, filename: str, content_type: str | None = None) -> tuple[str, Path]:
        """
        Validates image payload size, signature, and safe naming.
        Returns: (web_accessible_relative_path, absolute_disk_path)
        """
        # 1. Size check
        if len(file_bytes) == 0:
            raise MediaValidationError("Uploaded file is empty.")
        if len(file_bytes) > MAX_FILE_SIZE:
            raise MediaValidationError(f"File size exceeds maximum allowed limit of {MAX_FILE_SIZE // (1024 * 1024)} MB.")

        # 2. Magic byte signature check
        matched_ext = None
        for sig, ext in MAGIC_SIGNATURES:
            if file_bytes.startswith(sig):
                matched_ext = ext
                break

        if not matched_ext:
            # Check webp signature variant (RIFF....WEBP)
            if file_bytes[:4] == b"RIFF" and file_bytes[8:12] == b"WEBP":
                matched_ext = ".webp"

        if not matched_ext:
            raise MediaValidationError("Invalid file format. Only JPEG, PNG, GIF, and WEBP images are supported.")

        # 3. Content type check if provided
        if content_type and content_type.lower() not in ALLOWED_MIME_TYPES:
            raise MediaValidationError(f"Disallowed content type: {content_type}")

        # 4. Safe random filename generation to prevent path traversal
        unique_name = f"{uuid.uuid4().hex}{matched_ext}"
        destination = (self.upload_dir / unique_name).resolve()

        # Path traversal guard
        if not str(destination).startswith(str(self.upload_dir)):
            raise MediaValidationError("Path traversal attempt detected.")

        with open(destination, "wb") as f:
            f.write(file_bytes)

        relative_web_path = f"/uploads/media/{unique_name}"
        return relative_web_path, destination
