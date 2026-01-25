"""Unit tests for the UispAirOSProductMapper class in model_map.py."""

import re

import pytest

from airos.exceptions import AirOSMultipleMatchesFoundException
from airos.model_map import UispAirOSProductMapper


class TestUispAirOSProductMapper:
    """Unit tests for the UispAirOSProductMapper class."""

    mapper = UispAirOSProductMapper()

    def test_get_sku_by_devmodel_exact_match(self):
        """Test to return the correct SKU for a full, exact model name."""
        sku = self.mapper.get_sku_by_devmodel("Wave MLO5")
        assert sku == "Wave-MLO5"

    def test_get_sku_by_devmodel_partial_single_match(self):
        """Test to return the correct SKU for a partial model name that matches only one product."""
        sku = self.mapper.get_sku_by_devmodel("NanoBeam 5AC")
        assert sku == "NBE-5AC-GEN2"

    def test_get_sku_by_devmodel_case_insensitivity(self):
        """Test to work regardless of the case of the input model name."""
        sku = self.mapper.get_sku_by_devmodel("nanostation 5ac loco")
        assert sku == "Loco5AC"

    def test_get_sku_by_devmodel_not_found_raises_keyerror(self):
        """Test to raise KeyError when no match (exact or partial) is found."""
        with pytest.raises(
            KeyError, match="No product found for devmodel: NonExistent"
        ):
            self.mapper.get_sku_by_devmodel("NonExistent Model 123")

    def test_get_sku_by_devmodel_multiple_matches_raises_exception_dynamic(self):
        """Test to raise AirOSMultipleMatchesFoundException when partial match is ambiguous."""
        with pytest.raises(AirOSMultipleMatchesFoundException) as excinfo:
            self.mapper.get_sku_by_devmodel("LiteBeam")

        exception_message = str(excinfo.value)
        expected_matches = 5

        match = re.search(r"matched multiple \((\d+)\) products", exception_message)
        assert match is not None
        actual_matches_int = int(match.group(1))
        assert actual_matches_int == expected_matches

    def test_get_devmodel_by_sku_exact_match(self):
        """Test to return the full model name for an exact SKU."""
        model = self.mapper.get_devmodel_by_sku("Loco5AC")
        assert model == "airMAX NanoStation 5AC Loco"

    def test_get_devmodel_by_sku_not_found_raises_keyerror(self):
        """Test to raise KeyError when the exact SKU is not found."""
        with pytest.raises(KeyError, match="No product found for SKU: FAKE-SKU"):
            self.mapper.get_devmodel_by_sku("FAKE-SKU")
