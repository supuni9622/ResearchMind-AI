from __future__ import annotations

import asyncio
import time
from typing import BinaryIO

import boto3
import structlog
from app.core.settings import Settings
from app.infrastructure.storage.exceptions import (
    StorageDeleteError,
    StorageDownloadError,
    StorageListError,
    StorageNotFoundError,
    StorageUploadError,
)
from app.infrastructure.storage.interfaces import DocumentStorage
from botocore.exceptions import ClientError

logger = structlog.get_logger()


class S3StorageService(DocumentStorage):
    """Amazon S3 implementation."""

    def __init__(self, settings: Settings) -> None:
        self._bucket = settings.aws_s3_bucket

        self._client = boto3.client(
            "s3",
            region_name=settings.aws_region or None,
            endpoint_url=settings.aws_s3_endpoint_url or None,
            aws_access_key_id=settings.aws_access_key_id or None,
            aws_secret_access_key=settings.aws_secret_access_key or None,
            aws_session_token=settings.aws_session_token or None,
        )

        logger.debug("s3.client_initialised", bucket=self._bucket)

    async def upload(
        self,
        *,
        key: str,
        file: BinaryIO,
        content_type: str,
    ) -> None:
        start = time.perf_counter()
        try:
            await asyncio.to_thread(
                self._client.upload_fileobj,
                file,
                self._bucket,
                key,
                ExtraArgs={"ContentType": content_type},
            )
        except ClientError as exc:
            logger.warning("s3.upload_failed", key=key, reason=str(exc))
            raise StorageUploadError(str(exc)) from exc

        logger.debug(
            "s3.upload_complete",
            key=key,
            duration_ms=round((time.perf_counter() - start) * 1000, 2),
        )

    async def download(
        self,
        *,
        key: str,
    ) -> bytes:
        from io import BytesIO

        buffer = BytesIO()
        start = time.perf_counter()

        try:
            await asyncio.to_thread(
                self._client.download_fileobj,
                self._bucket,
                key,
                buffer,
            )
        except ClientError as exc:
            logger.warning("s3.download_failed", key=key, reason=str(exc))
            raise StorageDownloadError(str(exc)) from exc

        data = buffer.getvalue()

        logger.debug(
            "s3.download_complete",
            key=key,
            bytes=len(data),
            duration_ms=round((time.perf_counter() - start) * 1000, 2),
        )

        return data

    async def delete(
        self,
        *,
        key: str,
    ) -> None:
        start = time.perf_counter()
        try:
            await asyncio.to_thread(
                self._client.delete_object,
                Bucket=self._bucket,
                Key=key,
            )
        except ClientError as exc:
            logger.warning("s3.delete_failed", key=key, reason=str(exc))
            raise StorageDeleteError(str(exc)) from exc

        logger.debug(
            "s3.delete_complete",
            key=key,
            duration_ms=round((time.perf_counter() - start) * 1000, 2),
        )

    async def exists(
        self,
        *,
        key: str,
    ) -> bool:
        try:
            await asyncio.to_thread(
                self._client.head_object,
                Bucket=self._bucket,
                Key=key,
            )
            return True
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code")

            if code == "404":
                return False

            logger.warning("s3.exists_check_failed", key=key, reason=str(exc))
            raise StorageNotFoundError(str(exc)) from exc

    async def generate_presigned_url(
        self,
        *,
        key: str,
        expires_in: int = 3600,
    ) -> str:
        url: str = await asyncio.to_thread(
            self._client.generate_presigned_url,
            "get_object",
            Params={
                "Bucket": self._bucket,
                "Key": key,
            },
            ExpiresIn=expires_in,
        )

        logger.debug("s3.presigned_url_generated", key=key, expires_in=expires_in)

        return url

    async def list_keys(
        self,
        *,
        prefix: str,
    ) -> list[str]:
        start = time.perf_counter()

        try:
            paginator = self._client.get_paginator("list_objects_v2")

            def _collect() -> list[str]:
                keys: list[str] = []

                for page in paginator.paginate(Bucket=self._bucket, Prefix=prefix):
                    keys.extend(obj["Key"] for obj in page.get("Contents", []))

                return keys

            keys = await asyncio.to_thread(_collect)
        except ClientError as exc:
            logger.warning("s3.list_keys_failed", prefix=prefix, reason=str(exc))
            raise StorageListError(str(exc)) from exc

        logger.debug(
            "s3.list_keys_complete",
            prefix=prefix,
            count=len(keys),
            duration_ms=round((time.perf_counter() - start) * 1000, 2),
        )

        return keys
