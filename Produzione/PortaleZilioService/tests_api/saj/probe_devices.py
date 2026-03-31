"""Manual probe for SAJ devices discovered from the live plant list.

Run:
    python Produzione/PortaleZilioService/tests_api/saj/probe_devices.py
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_APPS_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_APPS_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_APPS_ROOT))

from PortaleZilioService.API_inverter import saj_client


def main() -> None:
    token = saj_client.get_token()
    headers = saj_client.build_headers(token)
    
    # ENDPOINTS:
    plants = saj_client.get_plants(headers)
    plants_ids = [str(plant.get("plantId", "")).strip() for plant in plants if str(plant.get("plantId", "")).strip()]
    devices = saj_client.get_devices(headers, plant_id=plants_ids[0]) if plants_ids else []
    
    
    
    print("== SAJ devices probe ==")
    print(f"plants_found: {len(plants)}")
    i = 1
    for plant in plants: 
        print(  f"{i}) plantId: {plant.get('plantId')}, "
                f"plantNo: {plant.get('plantNo')}, "
                f"plantName: {plant.get('plantName')}")
        i += 1
    
    print(f"plants_ids: {plants_ids}")
    
    
    print("------------------------------------------------------------------------------------------------")
    for plant in plants_ids: 
        # print actual name of the plant correlated to the plant id 
        plant_name = next((p.get("plantName") for p in plants if p.get("plantId") == plant), "Unknown")
        print(f"plant name: {plant_name} (id: {plant})")
        for device in devices:
            if device.get('plantId') == plant:
                print(f"deviceSn: {device.get('deviceSn')}, "
                        f"deviceType: {device.get('deviceType')}, "
                        f"plantId: {device.get('plantId')}, "
                        f"plantName: {device.get('plantName')}, "
                        f"isOnline: {device.get('isOnline')}, "
                        f"isAlarm: {device.get('isAlarm')}, "
                        f"country: {device.get('country')}")
        print("------------------------------------------------------------------------------------------------")
    



if __name__ == "__main__":
    main()
