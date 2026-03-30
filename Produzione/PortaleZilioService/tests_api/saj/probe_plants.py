"""Manual probe for SAJ plant discovery.

Run:
    python Produzione/PortaleZilioService/tests_api/saj/probe_plants.py
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

    print("== SAJ plants probe ==")
    print(f"plants_found: {len(plants)}")
    print("")

    for index, plant in enumerate(plants, start=1):
        excerpt = {
            "plantId": plant.get("plantId"),
            "plantName": plant.get("plantName"),
            "deviceCount": plant.get("deviceCount"),
            "plantStatus": plant.get("plantStatus"),
            "country": plant.get("country"),
            "installer": plant.get("installer"),
        }
        print(f"[{index}] {json.dumps(excerpt, ensure_ascii=False)}")

    if plants:
        print("")
        print("first_payload_full:")
        print(json.dumps(plants[0], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
