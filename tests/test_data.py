"""Tests for airos data module."""

from unittest.mock import patch

from airos.data import Host, Wireless
import pytest


@pytest.mark.asyncio
async def test_unknown_enum_values():
    """Test that unknown enum values are handled gracefully."""
    # 1. Test for Host.netrole
    host_data = {"netrole": "unsupported_role", "other_field": "value"}
    format_string = (
        "Unknown value '%s' for %s.%s. Please report at "
        "https://github.com/CoMPaTech/python-airos/issues so we can add support."
    )
    with patch("airos.data.logger.warning") as mock_warning:
        processed_host = Host.__pre_deserialize__(host_data.copy())
        # Verify the unknown value was removed
        assert "netrole" not in processed_host
        # Verify the other fields remain
        assert "other_field" in processed_host
        # Verify a warning was logged
        mock_warning.assert_called_once_with(
            format_string, "unsupported_role", "Host", "netrole"
        )

    # 2. Test for Wireless (all enums)
    wireless_data = {
        "mode": "unsupported_mode",
        "ieeemode": "unsupported_ieee",
        "security": "unsupported_security",
        "other_field": "value",
    }
    with patch("airos.data.logger.warning") as mock_warning:
        processed_wireless = Wireless.__pre_deserialize__(wireless_data.copy())
        # Verify the unknown values were removed
        assert "mode" not in processed_wireless
        assert "ieeemode" not in processed_wireless
        assert "security" not in processed_wireless
        # Verify the other field remains
        assert "other_field" in processed_wireless
        # Verify warnings were logged for each unknown enum
        assert mock_warning.call_count == 3
        mock_warning.assert_any_call(
            format_string, "unsupported_mode", "Wireless", "mode"
        )
        mock_warning.assert_any_call(
            format_string, "unsupported_ieee", "Wireless", "ieeemode"
        )
        mock_warning.assert_any_call(
            format_string, "unsupported_security", "Wireless", "security"
        )
