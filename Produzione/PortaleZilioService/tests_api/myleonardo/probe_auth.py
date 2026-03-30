"""Manual probe for MyLeonardo authentication.

Run:
    py Produzione/PortaleZilioService/tests_api/myleonardo/probe_auth.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_APPS_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_APPS_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_APPS_ROOT))

from MonitoraggioImpianti.API_MyLeo import login_LEO


def main() -> None:
    response = login_LEO()
    token = response.get("token")

    print("== MyLeonardo auth probe ==")
    print(f"token_present: {bool(token)}")
    if token:
        print(f"token_prefix: {token[:16]}...")
    print("")
    print("full_response:")
    print(json.dumps(response, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
