"""List of airOS products."""

from .exceptions import AirOSMultipleMatchesFoundException

MODELS: dict[str, str] = {
    "Wave MLO5": "Wave-MLO5",
    "airMAX Rocket Prism 5AC": "RP-5AC-Gen2",
    "airFiber 5XHD": "AF-5XHD",
    "airMAX Lite AP GPS": "LAP-GPS",
    "airMAX PowerBeam 5AC": "PBE-5AC-Gen2",
    "airMAX PowerBeam 5AC ISO": "PBE-5AC-ISO-Gen2",
    "airMAX PowerBeam 5AC 620": "PBE-5AC-620",
    "airMAX LiteBeam 5AC": "LBE-5AC-GEN2",
    "airMAX LiteBeam 5AC Long-Range": "LBE-5AC-LR",
    "airMAX NanoBeam 5AC": "NBE-5AC-GEN2",
    "airMAX NanoStation 5AC": "NS-5AC",
    "airMAX NanoStation 5AC Loco": "Loco5AC",
    "LTU Rocket": "LTU-Rocket",
    "LTU Instant (5-pack)": "LTU-Instant",
    "LTU Pro": "LTU-PRO",
    "LTU Long-Range": "LTU-LR",
    "LTU Extreme-Range": "LTU-XR",
    "airMAX NanoBeam 2AC": "NBE-2AC-13",
    "airMAX PowerBeam 2AC 400": "PBE-2AC-400",
    "airMAX Rocket AC Lite": "R5AC-LITE",
    "airMAX LiteBeam M5": "LBE-M5-23",
    "airMAX PowerBeam 5AC 500": "PBE-5AC-500",
    "airMAX PrismStation 5AC": "PS-5AC",
    "airMAX IsoStation 5AC": "IS-5AC",
    "airMAX Lite AP": "LAP-120",
    "airMAX PowerBeam M5 400": "PBE-M5-400",
    "airMAX PowerBeam M5 300 ISO": "PBE-M5-300-ISO",
    "airMAX PowerBeam M5 300": "PBE-M5-300",
    "airMAX PowerBeam M2 400": "PBE-M2-400",
    "airMAX Bullet AC": "B-DB-AC",
    "airMAX Bullet AC IP67": "BulletAC-IP67",
    "airMAX Bullet M2": "BulletM2-HP",
    "airMAX IsoStation M5": "IS-M5",
    "airMAX NanoStation M5": "NSM5",
    "airMAX NanoStation M5 loco": "LocoM5",
    "airMAX NanoStation M2 loco": "LocoM2",
    "UISP Horn": "UISP-Horn",
    "UISP Dish": "UISP-Dish",
    "UISP Dish Mini": "UISP-Dish-Mini",
    "airMAX AC 5 GHz, 31 dBi RocketDish": "RD-5G31-AC",
    "airMAX 5 GHz, 30 dBi RocketDish LW": "RD-5G30-LW",
    "airMAX AC 5 GHz, 30/34 dBi RocketDish": "RD-5G",
    "airPRISM 3x30° HD Sector": "AP-5AC-90-HD",
    "airMAX 5 GHz, 16/17 dBi Sector": "AM-5G1",
    "airMAX PrismStation Horn": "Horn-5",
    "airMAX 5 GHz, 10 dBi Omni": "AMO-5G10",
    "airMAX 5 GHz, 13 dBi, Omni": "AMO-5G13",
    "airMAX Sector 2.4 GHz Titanium": "AM-V2G-Ti",
    "airMAX AC 5 GHz, 21 dBi, 60º Sector": "AM-5AC21-60",
    "airMAX AC 5 GHz, 22 dBi, 45º Sector": "AM-5AC22-45",
    "airMAX 2.4 GHz, 16 dBi, 90º Sector": "AM-2G16-90",
    "airMAX 900 MHz, 13 dBi, 120º Sector": "AM-9M13-120",
    "airMAX 900 MHz, 16 dBi Yagi": "AMY-9M16x2",
    "airMAX NanoBeam M5": "NBE-M5-16",
    "airMAX Rocket Prism 2AC": "R2AC-PRISM",
    "airFiber 5 Mid-Band": "AF-5",
    "airFiber 5 High-Band": "AF-5U",
    "airFiber 24": "AF-24",
    "airFiber 24 Hi-Density": "AF-24HD",
    "airFiber 2X": "AF-2X",
    "airFiber 11": "AF-11",
    "airFiber 11 Low-Band Backhaul Radio with Dish Antenna": "AF11-Complete-LB",
    "airFiber 11 High-Band Backhaul Radio with Dish Antenna": "AF11-Complete-HB",
    "airMAX LiteBeam 5AC Extreme-Range": "LBE-5AC-XR",
    "airMAX PowerBeam M5 400 ISO": "PBE-M5-400-ISO",
    "airMAX NanoStation M2": "NSM2",
    "airFiber X 5 GHz, 23 dBi, Slant 45": "AF-5G23-S45",
    "airFiber X 5 GHz, 30 dBi, Slant 45": "AF-5G30-S45",
    "airFiber X 5 GHz, 34 dBi, Slant 45": "AF-5G34-S45",
    "airMAX 5 GHz, 19/20 dBi Sector": "AM-5G2",
    "airMAX 2.4 GHz, 10 dBi Omni": "AMO-2G10",
    "airMAX 2.4 GHz, 15 dBi, 120º Sector": "AM-2G15-120",
}


class UispAirOSProductMapper:
    """Utility class to map product model names to SKUs and vice versa."""

    def __init__(self) -> None:
        """Provide reversed map for SKUs."""
        self._SKUS = {v: k for k, v in MODELS.items()}

    def get_sku_by_devmodel(self, devmodel: str) -> str:
        """Retrieves the SKU for a given device model name."""
        if devmodel in MODELS:
            return MODELS[devmodel]

        match_key = None
        matches_found = 0

        lower_devmodel = devmodel.lower()

        for model_name in MODELS:
            if lower_devmodel in model_name.lower():
                match_key = model_name
                matches_found += 1

        if match_key is None or matches_found == 0:
            raise KeyError(f"No product found for devmodel: {devmodel}")

        if match_key and matches_found == 1:
            return MODELS[match_key]

        raise AirOSMultipleMatchesFoundException(
            f"Partial model '{devmodel}' matched multiple ({matches_found}) products."
        )

    def get_devmodel_by_sku(self, sku: str) -> str:
        """Retrieves the full device model name for an exact SKU match."""
        if sku in self._SKUS:
            return self._SKUS[sku]
        raise KeyError(f"No product found for SKU: {sku}")
