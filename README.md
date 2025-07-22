# Ubiquity airOS Module

## Main usage

Via [Home-Assistant](https://www.home-assistant.io) - initial core integration [pending](https://github.com/home-assistant/core/pull/148989).

## Working

Emulating client browser

```example.py
from airos.airos8 import AirOS
import aiohttp
import asyncio

async def test_airos():
    session = aiohttp.ClientSession(connector=aiohttp.TCPConnector(verify_ssl=False))
    device = AirOS(host="192.168.1.2",username="ubnt",password="password",session=session)
    # Login
    result = await device.login()
    print(f"Result: {result}")
    # Fetch status (large dict, including connected stations)
    result = await device.status()
    print(f"Result: {result}")
    print(f"Result: {result.wireless.mode}")
    # Reconnect 'other side'
    result = await device.stakick("01:23:45:67:89:AB")
    print(f"Result: {result}")

def async_loop(loop: asyncio.AbstractEventLoop) -> int:
    return loop.run_until_complete(test_airos())

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    result = async_loop(loop)
```
