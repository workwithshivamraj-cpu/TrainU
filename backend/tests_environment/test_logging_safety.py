from __future__ import annotations

import logging

from app.core.logging import configure_logging


def test_debug_configuration_keeps_external_client_logs_redacted() -> None:
    configure_logging(debug=True)
    for name in ("boto3", "botocore", "s3transfer", "httpx", "httpcore", "urllib3"):
        assert logging.getLogger(name).getEffectiveLevel() >= logging.WARNING
