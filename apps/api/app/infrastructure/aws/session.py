"""
AWS session management.
"""

from __future__ import annotations

import boto3
from app.core.settings import Settings


class AwsSession:
    """Factory for AWS service clients."""

    def __init__(self, settings: Settings) -> None:
        self._session = boto3.session.Session(
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            aws_session_token=settings.aws_session_token,
        )

        self._endpoint_url = settings.aws_s3_endpoint_url

    def s3(self):
        """Create an Amazon S3 client."""

        return self._session.client(
            "s3",
            endpoint_url=self._endpoint_url,
        )
