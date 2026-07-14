"""Streamlit entrypoint.

The application implementation is isolated under ``pages`` so this file is
kept free from page and business logic.
"""

import pages.application  # noqa: F401 - importing runs the registered router
