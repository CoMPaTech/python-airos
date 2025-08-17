"""Request tests."""

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from airos.airos8 import AirOS
from airos.exceptions import (
    AirOSConnectionAuthenticationError,
    AirOSDataMissingError,
    AirOSDeviceConnectionError,
)

# pylint: disable=redefined-outer-name


@pytest.fixture
def mock_session() -> MagicMock:
    """Return a mock aiohttp ClientSession."""
    return MagicMock(spec=aiohttp.ClientSession)


@pytest.fixture
def mock_airos_device(mock_session: MagicMock) -> AirOS:
    """Return a mock AirOS instance with string host."""
    return AirOS(
        host="192.168.1.3",
        username="testuser",
        password="testpassword",
        session=mock_session,
    )


@pytest.mark.asyncio
async def test_request_json_success(
    mock_airos_device: AirOS,
    mock_session: MagicMock,
) -> None:
    """Test successful JSON request."""
    expected_response_data = {"key": "value"}
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.text = AsyncMock(return_value='{"key": "value"}')
    mock_response.raise_for_status = MagicMock()

    mock_session.request.return_value.__aenter__.return_value = mock_response

    with patch.object(mock_airos_device, "connected", True):
        response_data = await mock_airos_device._request_json("GET", "/test/path")  # noqa: SLF001

    assert response_data == expected_response_data
    mock_session.request.assert_called_once()
    mock_session.request.assert_called_once_with(
        "GET",
        "/test/path",
        json=None,
        data=None,
        headers={},
    )


@pytest.mark.asyncio
async def test_request_json_connection_error(
    mock_airos_device: AirOS,
    mock_session: MagicMock,
) -> None:
    """Test handling of a connection error."""
    mock_session.request.return_value.__aenter__.side_effect = (
        aiohttp.ClientConnectionError
    )

    with (
        patch.object(mock_airos_device, "connected", True),
        pytest.raises(AirOSDeviceConnectionError),
    ):
        await mock_airos_device._request_json("GET", "/test/path")  # noqa: SLF001


@pytest.mark.asyncio
async def test_request_json_http_error(
    mock_airos_device: AirOS,
    mock_session: MagicMock,
) -> None:
    """Test handling of a non-200 HTTP status code."""
    mock_response = AsyncMock()
    mock_response.status = 401
    mock_response.raise_for_status = MagicMock(
        side_effect=aiohttp.ClientResponseError(
            request_info=MagicMock(), history=(), status=401, message="Unauthorized"
        )
    )
    mock_response.text = AsyncMock(return_value="{}")

    mock_session.request.return_value.__aenter__.return_value = mock_response

    with (
        patch.object(mock_airos_device, "connected", True),
        pytest.raises(AirOSConnectionAuthenticationError),
    ):
        await mock_airos_device._request_json("GET", "/test/path")  # noqa: SLF001

    mock_response.raise_for_status.assert_called_once()


@pytest.mark.asyncio
async def test_request_json_non_json_response(
    mock_airos_device: AirOS,
    mock_session: MagicMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test handling of a response that is not valid JSON."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.text = AsyncMock(return_value="NOT-A-JSON-STRING")
    mock_response.raise_for_status = MagicMock()
    mock_session.request.return_value.__aenter__.return_value = mock_response

    with (
        patch.object(mock_airos_device, "connected", True),
        pytest.raises(AirOSDataMissingError),
        caplog.at_level(logging.DEBUG),
    ):
        await mock_airos_device._request_json("GET", "/test/path")  # noqa: SLF001

    assert "Failed to decode JSON from /test/path" in caplog.text


@pytest.mark.asyncio
async def test_request_json_with_params_and_data(
    mock_airos_device: AirOS,
    mock_session: MagicMock,
) -> None:
    """Test request with parameters and data."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.text = AsyncMock(return_value="{}")
    mock_response.raise_for_status = MagicMock()

    mock_session.request.return_value.__aenter__.return_value = mock_response

    params = {"param1": "value1"}
    data = {"key": "value"}

    with patch.object(mock_airos_device, "connected", True):
        await mock_airos_device._request_json(  # noqa: SLF001
            "POST", "/test/path", json_data=params, form_data=data
        )

    mock_session.request.assert_called_once_with(
        "POST",
        "/test/path",
        json=params,
        data=data,
        headers={},
    )
