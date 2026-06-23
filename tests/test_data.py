"""Tests for airos data module."""

from unittest.mock import patch

import pytest

from airos.data import Host, Security, Wireless, Wireless6


@pytest.mark.asyncio
async def test_unknown_enum_values() -> None:
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
            format_string, "unsupported_ieee".upper(), "Wireless", "ieeemode"
        )
        mock_warning.assert_any_call(
            format_string, "unsupported_security", "Wireless", "security"
        )


def test_wireless_security_none_is_supported() -> None:
    """Test that open/no-security wireless links are supported."""
    wireless_data = {
        "mode": "ap-ptp",
        "ieeemode": "11NGHT20",
        "security": "none",
        "other_field": "value",
    }

    with patch("airos.data.logger.warning") as mock_warning:
        processed_wireless = Wireless.__pre_deserialize__(wireless_data.copy())

    assert processed_wireless["security"] == "none"
    mock_warning.assert_not_called()


def test_wireless6_security_none_is_supported() -> None:
    """Test that airOS 6 open/no-security wireless links are supported."""
    wireless_data = {
        "essid": "OFFICE-LINK",
        "hide_essid": 0,
        "apmac": "9C:05:D6:90:5D:33",
        "countrycode": 840,
        "channel": 11,
        "frequency": "2462 MHz",
        "dfs": 0,
        "opmode": "11NGHT20",
        "antenna": "Built in - 8 dBi",
        "chains": "2X2",
        "signal": -59,
        "rssi": 0,
        "noisef": -93,
        "txpower": 23,
        "ack": 0,
        "distance": 600,
        "ccq": 0,
        "txrate": "",
        "rxrate": "6",
        "security": "none",
        "qos": "",
        "rstatus": 0,
        "cac_nol": 0,
        "nol_chans": 0,
        "wds": 1,
        "aprepeater": 0,
        "chanbw": 20,
        "mode": "sta",
    }

    with patch("airos.data.logger.warning") as mock_warning:
        wireless = Wireless6.from_dict(wireless_data)

    assert wireless.security is Security.NONE
    assert wireless.frequency == 2462
    assert wireless.polling.dl_capacity == 6000
    mock_warning.assert_not_called()
