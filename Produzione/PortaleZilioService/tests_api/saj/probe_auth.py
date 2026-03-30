"""Manual probe for SAJ authentication.

Run:
    python Produzione/PortaleZilioService/tests_api/saj/probe_auth.py
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

    print("== SAJ auth probe ==")
    print(f"token_present: {bool(token)}")
    print(f"token_prefix: {token[:12]}..." if token else "token_prefix: <missing>")
    print("headers:")
    print(json.dumps(headers, indent=2))


if __name__ == "__main__":
    main()
