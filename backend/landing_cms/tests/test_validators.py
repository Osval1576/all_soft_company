from io import BytesIO
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image

from landing_cms.validators import validate_image_file


def _png_bytes(w=10, h=10):
    buf = BytesIO()
    Image.new("RGB", (w, h), "white").save(buf, format="PNG")
    return buf.getvalue()


class ValidateImageFileTests(TestCase):
    def test_accepts_small_png(self):
        f = SimpleUploadedFile("ok.png", _png_bytes(), content_type="image/png")
        validate_image_file(f)  # must not raise

    def test_rejects_non_image(self):
        f = SimpleUploadedFile("evil.txt", b"hello", content_type="text/plain")
        with self.assertRaises(ValidationError):
            validate_image_file(f)

    def test_rejects_oversize(self):
        big = b"\x00" * (2 * 1024 * 1024 + 1)
        f = SimpleUploadedFile("big.png", big, content_type="image/png")
        with self.assertRaises(ValidationError):
            validate_image_file(f)

    def test_rejects_corrupt_image(self):
        f = SimpleUploadedFile("corrupt.png", b"\x89PNG\r\n\x1a\nGARBAGE_NOT_A_REAL_PNG", content_type="image/png")
        with self.assertRaises(ValidationError):
            validate_image_file(f)
