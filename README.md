<div align="center">
<img src="https://github.com/home-assistant/brands/blob/master/core_brands/ubiquiti/icon.png?raw=true" alt="Ubiquiti airOS Logo" width="150" />
<h1>python-airos</h1>
<p>An asynchronous Python module to interact with Ubiquiti airOS devices, emulating a web browser client.</p>
</div>

<div align="center">

</div>

[![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg)](https://github.com/python-airos)
[![CodeRabbit.ai is Awesome](https://img.shields.io/badge/AI-orange?label=CodeRabbit&color=orange&link=https%3A%2F%2Fcoderabbit.ai)](https://coderabbit.ai)
[![renovate maintained](https://img.shields.io/badge/maintained%20with-renovate-blue?logo=renovatebot)](https://github.com/compatech/python-airos/issues/8)

[![PyPI version fury.io](https://badge.fury.io/py/airos.svg)](https://pypi.python.org/pypi/airos/)
[![Latest release](https://github.com/compatech/python-airos/workflows/Latest%20release/badge.svg)](https://github.com/compatech/python-airos/actions)
[![Newest commit](https://github.com/compatech/python-airos/workflows/Latest%20commit/badge.svg)](https://github.com/compatech/python-airos/actions)

[![CodeFactor](https://www.codefactor.io/repository/github/compatech/python-airos/badge)](https://www.codefactor.io/repository/github/plugwise/python-airos)
[![codecov](https://codecov.io/gh/compatech/python-airos/branch/main/graph/badge.svg?token=WI5K2IZWNS)](https://codecov.io/gh/compatech/python-airos)

[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=CoMPaTech_python-airos&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=CoMPaTech_python-airos)
[![Technical Debt](https://sonarcloud.io/api/project_badges/measure?project=CoMPaTech_python-airos&metric=sqale_index)](https://sonarcloud.io/summary/new_code?id=CoMPaTech_python-airos)
[![Code Smells](https://sonarcloud.io/api/project_badges/measure?project=CoMPaTech_python-airos&metric=code_smells)](https://sonarcloud.io/summary/new_code?id=CoMPaTech_python-airos)

# Overview

`python-airos` or [`airos`](https://pypi.org/projects/airos) from pypi is an asynchronous Python library designed to programmatically interact with Ubiquiti airOS devices. It mimics a web browser client to fetch device status, configuration, and perform actions like kicking connected stations.

This library is a key component for a potential future core integration with [Home Assistant](https://www.home-assistant.io), with the initial pull request for core integration targeted for the 2025.8 release.

More details on the integration can be found on the [Ubiquiti UISP airOS](https://www.home-assistant.io/integrations/airos/) page. To add airOS directly feel free to use the button below:

[![Open your Home Assistant instance and show your integrations.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/_change/?redirect=config_flow_start%2F%3Fdomain%3Dairos)

## Features

- Asynchronous Operations: Built with `asyncio` and `aiohttp` for non-blocking I/O, which is perfect for integrations and background tasks.
- Client Emulation: Authenticates and interacts with airOS devices by emulating a client browser, ensuring a high degree of compatibility.
- Data Retrieval: Fetches comprehensive device status information, including:
- Wireless mode and signal strength.
- Connected stations and their statistics.
- System information and uptime.
- Device Control: Provides methods to perform actions, such as reconnecting/kicking a connected wireless station.
- Discovery of airOS devices on your local network (by listening to announcements these devices broadcast).

## Installation

You can install python-airos from PyPI using pip:

```Bash
pip install airos
```

## Usage

Here is a more detailed example of how to use the library to connect, fetch status, and perform an action on an airOS device.

```Python
import aiohttp
import asyncio
from airos.airos8 import AirOS

async def main():
    """Main function to demonstrate library usage."""
    # Create an aiohttp session with SSL verification disabled.
    # Be cautious with this setting; it's useful for self-signed certificates
    # but not recommended for production environments without proper validation.
    session = aiohttp.ClientSession(connector=aiohttp.TCPConnector(verify_ssl=False))

    # Initialize the AirOS device object.
    device = AirOS(
        host="192.168.1.2",
        username="ubnt",
        password="password",
        session=session
    )

    try:
        # Step 1: Login to the device.
        login_result = await device.login()
        print(f"Login successful: {login_result}")

        # Step 2: Fetch the device status.
        status_data = await device.status()
        print("\n--- Device Status ---")
        print(f"Device Name: {status_data.host.hostname}")
        print(f"Wireless Mode: {status_data.wireless.mode}")
        print(f"Firmware Version: {status_data.host.fwversion}")

        # Fetch and display connected stations if available
        if status_data.wireless.stations:
            print("\n--- Connected Stations ---")
            for station in status_data.wireless.stations:
                print(f"  - MAC: {station.mac}")
                print(f"    Signal: {station.signal} dBm")
                print(f"    Uptime: {station.uptime} seconds")

        # Step 3: Perform an action, e.g., kick a station.
        # Replace '01:23:45:67:89:AB' with the MAC address of a station to kick.
        # kick_result = await device.stakick("01:23:45:67:89:AB")
        # print(f"\nKick station result: {kick_result}")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # Ensure the aiohttp session is closed properly.
        await session.close()

if __name__ == "__main__":
    asyncio.run(main())
```

## Supported API Calls

The library currently supports the following methods:

- `login()`: Authenticates with the device.
- `status()`: Fetches a comprehensive dictionary of the device's status and statistics.
- `stakick(mac_address)`: Disconnects a specific station by its MAC address.

More features and API calls are planned for future releases.

## Contributing

We welcome contributions as well as additional codeowners to python-airos.
