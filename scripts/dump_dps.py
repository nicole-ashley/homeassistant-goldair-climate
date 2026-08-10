#!/usr/bin/env python3
"""
Dump and watch the raw Tuya DPS state of a device, to work out the DPS mapping
for a model this integration doesn't support yet.

This talks to the device the same way `custom_components/goldair_climate/device.py`
does, including trying the same protocol versions in the same order (3.2 is
deliberately excluded -- tinytuya's set_version(3.2) does blocking network I/O).

Usage:

    pip install tinytuya
    python3 scripts/dump_dps.py --id <device id> --key <local key> --ip <ip address>

It prints the full payload once (formatted so it can be pasted straight into
`tests/const.py`), then polls and prints only the DPS values that change. Walk
through every control on the appliance one at a time -- power, each mode, each
fan/power level, target temperature up and down, swing, timer, child lock,
display light -- and note what you pressed against each printed change.

Ctrl-C prints a summary of every value each DPS was ever seen to hold, which is
what the enum maps (HVAC_MODE_TO_DPS_MODE, PRESET_MODE_TO_DPS_MODE, ...) are
built from.
"""

import argparse
import json
import sys
from datetime import datetime
from time import sleep

# Same list, same order as custom_components/goldair_climate/const.py.
API_PROTOCOL_VERSIONS = [3.3, 3.4, 3.5, 3.1]


def _fail(message):
    print(f"error: {message}", file=sys.stderr)
    sys.exit(1)


def _read_dps(api):
    """Return the dps dict, or None if the device reported an error."""
    try:
        response = api.status()
    except Exception as error:  # noqa: BLE001 - tinytuya raises a variety of these
        return None, str(error)

    if response is None or not isinstance(response, dict):
        return None, f"unusable response: {response!r}"
    if "Err" in response:
        return None, f"{response.get('Err')}: {response.get('Error')}"
    if "dps" not in response:
        return None, f"no dps in response: {response!r}"

    return response["dps"], None


def connect(device_id, local_key, address, version=None):
    """Connect, rotating protocol versions until one returns a real payload."""
    import tinytuya

    versions = [version] if version else API_PROTOCOL_VERSIONS

    for candidate in versions:
        api = tinytuya.Device(device_id, address, local_key)
        api.set_version(candidate)
        dps, error = _read_dps(api)
        if dps is not None:
            print(f"connected using protocol {candidate}\n")
            return api, dps
        print(f"protocol {candidate} failed ({error})", file=sys.stderr)

    _fail(
        "could not read the device with any protocol version. Check the IP, "
        "device id and local key, and that nothing else (the Goldair/Tuya app, "
        "another HA integration) is holding the device's single local connection."
    )


def format_payload(dps):
    """Format a payload the way tests/const.py holds them."""
    lines = ["{"]
    for key in sorted(dps, key=lambda k: (len(k), k)):
        lines.append(f"    {json.dumps(key)}: {dps[key]!r},")
    lines.append("}")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Dump and watch a Tuya device's DPS state."
    )
    parser.add_argument("--id", required=True, help="device id")
    parser.add_argument("--key", required=True, help="local key")
    parser.add_argument("--ip", required=True, help="device IP address")
    parser.add_argument(
        "--version",
        type=float,
        default=None,
        help="pin a protocol version instead of trying each in turn",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=2.0,
        help="seconds between polls (default: 2)",
    )
    args = parser.parse_args()

    api, dps = connect(args.id, args.key, args.ip, args.version)

    print("initial payload:\n")
    print(format_payload(dps))
    print("\nwatching for changes -- exercise each control on the appliance.")
    print("Ctrl-C to stop and print a summary.\n")

    seen = {key: {repr(value)} for key, value in dps.items()}
    previous = dict(dps)

    try:
        while True:
            sleep(args.interval)
            current, error = _read_dps(api)
            if current is None:
                print(f"  (read failed: {error})", file=sys.stderr)
                continue

            changes = [
                (key, previous.get(key, "<absent>"), value)
                for key, value in current.items()
                if key not in previous or previous[key] != value
            ]
            changes.extend(
                (key, value, "<absent>")
                for key, value in previous.items()
                if key not in current
            )

            if changes:
                timestamp = datetime.now().strftime("%H:%M:%S")
                for key, before, after in sorted(
                    changes, key=lambda c: (len(c[0]), c[0])
                ):
                    print(f"{timestamp}  dps {key}: {before!r} -> {after!r}")

            for key, value in current.items():
                seen.setdefault(key, set()).add(repr(value))
            previous = current
    except KeyboardInterrupt:
        print("\n\nvalues observed per DPS:\n")
        for key in sorted(seen, key=lambda k: (len(k), k)):
            values = ", ".join(sorted(seen[key]))
            print(f"  dps {key}: {values}")
        print()


if __name__ == "__main__":
    main()
