"""Manual probe for iSolarCloud plant list.

Run:
    py Produzione/PortaleZilioService/tests_api/isolarcloud/probe_plants.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_APPS_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_APPS_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_APPS_ROOT))

from PortaleZilioService.API_inverter.API_iSolarCloud import get_all_plants, login_ISC
from PortaleZilioService.API_inverter.api_config import PAGE_SIZE


def _ensure_utf8_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main() -> None:
    _ensure_utf8_stdout()

    login_response = login_ISC()
    token = login_response.get("result_data", {}).get("token")
    if not token:
        raise RuntimeError("Login ISC failed: token missing")

    plants = get_all_plants(token=token, size=PAGE_SIZE)

    print("== iSolarCloud plants probe ==")
    print(f"plants_found: {len(plants)}")
    print("")

    for index, plant in enumerate(plants, start=1):
        excerpt = {
            "ps_id": plant.get("ps_id"),
            "ps_name": plant.get("ps_name"),
            "ps_status": plant.get("ps_status"),
            "installed_power": plant.get("installed_power"),
            "equivalent_hour": plant.get("equivalent_hour"),
        }
        print(f"[{index}] {json.dumps(excerpt, ensure_ascii=False)}")

    if plants:
        print("")
        print("first_payload_full:")
        print(json.dumps(plants[0], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
