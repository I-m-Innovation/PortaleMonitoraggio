"""Manual probe for SAJ devices discovered from the live plant list.

Run:
    python Produzione/PortaleZilioService/tests_api/saj/probe_devices.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_APPS_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_APPS_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_APPS_ROOT))

from PortaleZilioService.API_inverter import saj_client


def main() -> None:
    token = saj_client.get_token()
    headers = saj_client.build_headers(token)
    plants = saj_client.get_plants(headers)

    print("== SAJ devices probe ==")
    print(f"plants_found: {len(plants)}")

    for plant in plants:
        plant_id = str(plant.get("plantId", "")).strip()
        plant_name = str(plant.get("plantName", "")).strip() or "<unnamed plant>"
        if not plant_id:
            print("")
            print(f"plant_name: {plant_name}")
            print("plant_id: <missing>")
            print("devices_found: skipped, plantId missing")
            continue

        devices = saj_client.get_devices(headers, plant_id=plant_id)
        print("")
        print(f"plant_name: {plant_name}")
        print(f"plant_id: {plant_id}")
        print(f"devices_found: {len(devices)}")

        for device in devices:
            excerpt = {
                "deviceSn": device.get("deviceSn"),
                "deviceType": device.get("deviceType"),
                "deviceName": device.get("deviceName"),
                "isOnline": device.get("isOnline"),
                "isAlarm": device.get("isAlarm"),
                "plantId": device.get("plantId"),
            }
            print(json.dumps(excerpt, ensure_ascii=False))

        if devices:
            print("first_device_full:")
            print(json.dumps(devices[0], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
