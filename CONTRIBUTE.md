# Contributing

It would be very helpful if you would share your configuration data to this project. This way we can make sure that the data returned by your airOS devices is processed correctly.

## Current fixtures

We currently have data on

- Nanostation 5AC (LOCO5AC) - PTP - both AP and Station output of `/status.cgi` present (by @CoMPaTech)

## Secure your data

The best way to share your data is to remove any data that is not necessary for processing. To ensure you don't share any data by accident please follow the following

- Log in to your device
- Note down the following options set
  - Is it a station or access point
  - Is it PTP (or PTMP)
  - Channel width in Mhz
- Manually update the url to `/status.cgi`, e.g. `https://192.168.1.10/status.cgi`
- Store the output (for instance in an editor, even notepad would be fine) for processing

**NOTE**: when redacting, redact in a meaningful way by changing parameters, don't put text in number fields or vice-versa!

- First and foremost: find any `lat` and `lon` information and redact these but keep them as floats. (I.e. a value with decimals)!
  - There are potentially multiple of these (so keep searching)
  - If you are unsure, apply them as `(...)"lat":52.379894,"lon":4.901608,(...)` to point to Amsterdam
- Redact your IP addresses, especially public IPs (if present),
  - Search/replace your range, say your AP is at `192.168.1.10` then search for `192.168.1.` and replace with `127.0.0.`
  - Set them to `127.0.0.xxx` leaving the actual last octet what it was, just so devices are still different from **and** coheren to each other.
- Redact your SSID, just name it WirelessABC (as long as it's still coherent)
- Make sure your `hostname`s don't disclose unwanted information
- You may redact your MAC addresses (hwaddr, mac, etc) just make sure they are still valid (`00:11:22:33:44:55`) and coherent (so make sure local and remote(s) still differ)

### Examples

See `fixtures/userdata` for examples of shared information
