"""
Unit tests for S3StorageService.

Covers:
- Storage failures: every operation wraps a raw boto3 ClientError into the
  application's typed StorageError subclasses instead of leaking
  botocore internals up the stack
- The exists() 404-vs-other-error distinction
- Concurrency: multiple operations run concurrently via asyncio.to_thread
  without interfering with one another
"""

from __future__ import annotations

import asyncio
import io
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from app.infrastructure.storage.exceptions import (
    StorageDeleteError,
    StorageDownloadError,
    StorageNotFoundError,
    StorageUploadError,
)
from app.infrastructure.storage.s3 import S3StorageService
from botocore.exceptions import ClientError


def _fake_settings() -> SimpleNamespace:
    return SimpleNamespace(
        aws_s3_bucket="test-bucket",
        aws_region="us-east-1",
        aws_s3_endpoint_url=None,
        aws_access_key_id=None,
        aws_secret_access_key=None,
        aws_session_token=None,
    )


def _client_error(code: str = "InternalError") -> ClientError:
    return ClientError(
        error_response={"Error": {"Code": code, "Message": "simulated failure"}},
        operation_name="TestOperation",
    )


@pytest.fixture()
def mock_boto_client():
    with patch("app.infrastructure.storage.s3.boto3.client") as client_factory:
        client = MagicMock()
        client_factory.return_value = client
        yield client


@pytest.fixture()
def storage(mock_boto_client: MagicMock) -> S3StorageService:
    return S3StorageService(_fake_settings())  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Storage failures
# ---------------------------------------------------------------------------


class TestUploadFailures:
    async def test_client_error_wrapped_as_storage_upload_error(
        self,
        storage: S3StorageService,
        mock_boto_client: MagicMock,
    ) -> None:
        mock_boto_client.upload_fileobj.side_effect = _client_error()

        with pytest.raises(StorageUploadError):
            await storage.upload(
                key="documents/owner/doc/original.pdf",
                file=io.BytesIO(b"data"),
                content_type="application/pdf",
            )


class TestDownloadFailures:
    async def test_client_error_wrapped_as_storage_download_error(
        self,
        storage: S3StorageService,
        mock_boto_client: MagicMock,
    ) -> None:
        mock_boto_client.download_fileobj.side_effect = _client_error()

        with pytest.raises(StorageDownloadError):
            await storage.download(key="missing-key")


class TestDeleteFailures:
    async def test_client_error_wrapped_as_storage_delete_error(
        self,
        storage: S3StorageService,
        mock_boto_client: MagicMock,
    ) -> None:
        mock_boto_client.delete_object.side_effect = _client_error()

        with pytest.raises(StorageDeleteError):
            await storage.delete(key="documents/owner/doc/original.pdf")


class TestExistsSemantics:
    async def test_404_returns_false_without_raising(
        self,
        storage: S3StorageService,
        mock_boto_client: MagicMock,
    ) -> None:
        mock_boto_client.head_object.side_effect = _client_error(code="404")

        assert await storage.exists(key="missing") is False

    async def test_non_404_client_error_raises_storage_not_found_error(
        self,
        storage: S3StorageService,
        mock_boto_client: MagicMock,
    ) -> None:
        mock_boto_client.head_object.side_effect = _client_error(code="403")

        with pytest.raises(StorageNotFoundError):
            await storage.exists(key="forbidden")

    async def test_existing_object_returns_true(
        self,
        storage: S3StorageService,
        mock_boto_client: MagicMock,
    ) -> None:
        mock_boto_client.head_object.return_value = {}

        assert await storage.exists(key="present") is True


# ---------------------------------------------------------------------------
# Concurrency
# ---------------------------------------------------------------------------


class TestConcurrency:
    async def test_concurrent_uploads_all_reach_the_client(
        self,
        storage: S3StorageService,
        mock_boto_client: MagicMock,
    ) -> None:
        await asyncio.gather(
            *(
                storage.upload(
                    key=f"documents/owner/doc-{i}/original.pdf",
                    file=io.BytesIO(f"data-{i}".encode()),
                    content_type="application/pdf",
                )
                for i in range(10)
            )
        )

        assert mock_boto_client.upload_fileobj.call_count == 10

    async def test_concurrent_downloads_with_one_failure_do_not_affect_others(
        self,
        storage: S3StorageService,
        mock_boto_client: MagicMock,
    ) -> None:
        call_count = 0

        def _flaky_download(bucket, key, buffer):
            nonlocal call_count
            call_count += 1
            if call_count == 3:
                raise _client_error()
            buffer.write(b"chunk")

        mock_boto_client.download_fileobj.side_effect = _flaky_download

        results = await asyncio.gather(
            *(storage.download(key=f"k{i}") for i in range(6)),
            return_exceptions=True,
        )

        failures = [r for r in results if isinstance(r, Exception)]
        successes = [r for r in results if not isinstance(r, Exception)]

        assert len(failures) == 1
        assert isinstance(failures[0], StorageDownloadError)
        assert len(successes) == 5
