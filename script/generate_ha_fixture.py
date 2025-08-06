"""Generate mock airos fixture for testing."""

import json
import logging
import os
import sys

_LOGGER = logging.getLogger(__name__)

current_script_dir = os.path.dirname(os.path.abspath(__file__))
project_root_dir = os.path.abspath(os.path.join(current_script_dir, os.pardir))

if project_root_dir not in sys.path:
    sys.path.append(project_root_dir)

from airos.airos8 import AirOS, AirOSData  # noqa: E402

# Define the path to save the fixture
fixture_dir = os.path.join(os.path.dirname(__file__), "../fixtures")
userdata_dir = os.path.join(os.path.dirname(__file__), "../fixtures/userdata")
new_fixture_path = os.path.join(fixture_dir, "airos_loco5ac_ap-ptp.json")
base_fixture_path = os.path.join(userdata_dir, "loco5ac_ap-ptp.json")

with open(base_fixture_path) as source, open(new_fixture_path, "w") as new:
    source_data = json.loads(source.read())
    derived_data = AirOS.derived_data(None, source_data)
    new_data = AirOSData.from_dict(derived_data)
    json.dump(new_data.to_dict(), new, indent=2, sort_keys=True)

new_fixture_path = os.path.join(fixture_dir, "airos_loco5ac_sta-ptp.json")
base_fixture_path = os.path.join(userdata_dir, "loco5ac_sta-ptp.json")

with open(base_fixture_path) as source, open(new_fixture_path, "w") as new:
    source_data = json.loads(source.read())
    derived_data = AirOS.derived_data(None, source_data)
    new_data = AirOSData.from_dict(derived_data)
    json.dump(new_data.to_dict(), new, indent=2, sort_keys=True)

new_fixture_path = os.path.join(fixture_dir, "airos_mocked_sta-ptmp.json")
base_fixture_path = os.path.join(userdata_dir, "mocked_sta-ptmp.json")

with open(base_fixture_path) as source, open(new_fixture_path, "w") as new:
    source_data = json.loads(source.read())
    derived_data = AirOS.derived_data(None, source_data)
    new_data = AirOSData.from_dict(derived_data)
    json.dump(new_data.to_dict(), new, indent=2, sort_keys=True)

new_fixture_path = os.path.join(fixture_dir, "airos_liteapgps_ap_ptmp_40mhz.json")
base_fixture_path = os.path.join(userdata_dir, "liteapgps_ap_ptmp_40mhz.json")

with open(base_fixture_path) as source, open(new_fixture_path, "w") as new:
    source_data = json.loads(source.read())
    derived_data = AirOS.derived_data(None, source_data)
    new_data = AirOSData.from_dict(derived_data)
    json.dump(new_data.to_dict(), new, indent=2, sort_keys=True)

new_fixture_path = os.path.join(fixture_dir, "airos_nanobeam5ac_sta_ptmp_40mhz.json")
base_fixture_path = os.path.join(userdata_dir, "nanobeam5ac_sta_ptmp_40mhz.json")

with open(base_fixture_path) as source, open(new_fixture_path, "w") as new:
    source_data = json.loads(source.read())
    derived_data = AirOS.derived_data(None, source_data)
    new_data = AirOSData.from_dict(derived_data)
    json.dump(new_data.to_dict(), new, indent=2, sort_keys=True)
