"""Jarvis Backend Package.

Global initialization for the backend lives here so it runs as soon as the
`src` package is imported (for example when `src.server` is loaded by Uvicorn).
"""

import os

from loguru import logger


def _configure_ssl_cert_bundle() -> None:
    """
    Configure the SSL certificate bundle for outbound HTTPS/WebSocket calls.

    Many third‑party SDKs (Deepgram, ElevenLabs, etc.) rely on the system's
    default certificate store. On some macOS setups this can lead to
    `CERTIFICATE_VERIFY_FAILED` errors. We point Python's SSL layer at the
    `certifi` CA bundle so that TLS verification succeeds without disabling
    security checks.
    """
    try:
        import certifi
        import ssl

        ca_path = certifi.where()

        # Respect any explicit overrides, otherwise set sensible defaults.
        os.environ.setdefault("SSL_CERT_FILE", ca_path)
        os.environ.setdefault("REQUESTS_CA_BUNDLE", ca_path)

        # Also set the default SSL context for urllib and other libraries
        # This is crucial for WebSocket connections on macOS
        os.environ.setdefault("WEBSOCKET_CLIENT_CA_BUNDLE", ca_path)

        # For Python's ssl module - create a proper default context
        ssl._create_default_https_context = ssl.create_default_context

        # Configure the default SSL context to use certifi's certificates
        try:
            ssl.get_default_verify_paths()
        except:
            pass

        logger.info(f"Configured SSL cert bundle: {ca_path}")
    except Exception as e:  # pragma: no cover - best‑effort safety net
        logger.warning(f"Could not configure SSL cert bundle automatically: {e}")


_configure_ssl_cert_bundle()
