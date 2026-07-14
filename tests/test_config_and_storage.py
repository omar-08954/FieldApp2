import unittest

from config import SETTINGS
from database.storage import validate_report_image


class SettingsTests(unittest.TestCase):
    def test_security_and_upload_limits_are_sane(self):
        self.assertGreater(SETTINGS.session_timeout_seconds, 0)
        self.assertGreaterEqual(SETTINGS.max_login_attempts, 1)
        self.assertGreater(SETTINGS.max_upload_bytes, 0)


class ReportImageValidationTests(unittest.TestCase):
    def test_accepts_jpeg_magic_bytes(self):
        self.assertTrue(validate_report_image(b"\xff\xd8\xff\xe0test", "image/jpeg"))

    def test_accepts_png_magic_bytes(self):
        self.assertTrue(validate_report_image(b"\x89PNG\r\n\x1a\ntest", "image/png"))

    def test_rejects_mismatched_or_invalid_content(self):
        self.assertFalse(validate_report_image(b"not an image", "image/png"))
        self.assertFalse(validate_report_image(b"\xff\xd8\xff\xe0test", "application/pdf"))


if __name__ == "__main__":
    unittest.main()
