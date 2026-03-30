"""Manual probe for iSolarCloud authentication.

Run:
    py Produzione/PortaleZilioService/tests_api/isolarcloud/probe_auth.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_APPS_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_APPS_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_APPS_ROOT))

from PortaleZilioService.API_inverter.API_iSolarCloud import login_ISC


def main() -> None:
    response = login_ISC()
    token = response.get("result_data", {}).get("token")

    print("== iSolarCloud auth probe ==")
    print(f"result_code: {response.get('result_code')}")
    print(f"result_msg: {response.get('result_msg')}")
    print(f"token_present: {bool(token)}")
    if token:
        print(f"token_prefix: {token[:16]}...")
    print("")
    print("full_response:")
    print(json.dumps(response, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
