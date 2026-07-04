from django.core.exceptions import ValidationError
from PIL import Image, UnidentifiedImageError

IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
IMAGE_MAX_BYTES = 2 * 1024 * 1024
PDF_MAX_BYTES = 10 * 1024 * 1024


def validate_attachment(file):
    content_type = getattr(file, "content_type", None)
    if content_type in IMAGE_TYPES:
        if file.size > IMAGE_MAX_BYTES:
            raise ValidationError("La imagen excede 2 MB.")
        try:
            Image.open(file).verify()
        except (UnidentifiedImageError, OSError, SyntaxError, ValueError):
            raise ValidationError("El archivo no es una imagen válida.")
        finally:
            file.seek(0)
    elif content_type == "application/pdf":
        if file.size > PDF_MAX_BYTES:
            raise ValidationError("El PDF excede 10 MB.")
        head = file.read(5)
        file.seek(0)
        if head != b"%PDF-":
            raise ValidationError("El archivo no es un PDF válido.")
    else:
        raise ValidationError("Tipo de archivo no permitido (imágenes o PDF).")
