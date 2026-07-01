from django.core.exceptions import ValidationError
from PIL import Image, UnidentifiedImageError

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_BYTES = 2 * 1024 * 1024


def validate_image_file(file):
    if file.size > MAX_BYTES:
        raise ValidationError("La imagen excede 2 MB.")
    if getattr(file, "content_type", None) not in ALLOWED_CONTENT_TYPES:
        raise ValidationError("Tipo de archivo no permitido (usa jpg, png o webp).")
    try:
        Image.open(file).verify()
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError):
        raise ValidationError("El archivo no es una imagen válida.")
    finally:
        file.seek(0)
