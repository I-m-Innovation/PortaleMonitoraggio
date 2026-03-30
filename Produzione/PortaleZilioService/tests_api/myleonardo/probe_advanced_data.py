"""Manual probe for MyLeonardo advanced data endpoint.

Optional:
    py Produzione/PortaleZilioService/tests_api/myleonardo/probe_advanced_data.py
    py Produzione/PortaleZilioService/tests_api/myleonardo/probe_advanced_data.py 2026-03-30T00:00:00 2026-03-30T23:59:59
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests

PROJECT_APPS_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_APPS_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_APPS_ROOT))

from MonitoraggioImpianti.API_MyLeo import login_LEO


ADVANCED_URL = "https://myleonardo.western.it/api/external/advanced/0019816425961B0C/"


def _parse_cli_datetime(raw_value: str) -> datetime:
    try:
        return datetime.fromisoformat(raw_value)
    except ValueError as error:
        raise RuntimeError(
            f"Invalid datetime {raw_value!r}. Use ISO format, for example 2026-03-30T00:00:00"
        ) from error


def main() -> None:
    if len(sys.argv) >= 3:
        start_dt = _parse_cli_datetime(sys.argv[1])
        end_dt = _parse_cli_datetime(sys.argv[2])
    else:
        end_dt = datetime.now()
        start_dt = end_dt - timedelta(hours=24)

    token = login_LEO().get("token")
    if not token:
        raise RuntimeError("MyLeonardo login failed: token missing")

    headers = {
        "Accept": "application/json",
        "Authorization": f"Token {token}",
    }
    params = {
        "date_from": int(time.mktime(start_dt.timetuple())),
        "date_to": int(time.mktime(end_dt.timetuple())),
        "type": "C",
    }

    response = requests.get(ADVANCED_URL, params=params, headers=headers, timeout=60)
    response.raise_for_status()
    payload = response.json()
    rows = payload.get("data", [])

    print("== MyLeonardo advanced data probe ==")
    print(f"url: {ADVANCED_URL}")
    print(f"window_start: {start_dt.isoformat(sep=' ')}")
    print(f"window_end: {end_dt.isoformat(sep=' ')}")
    print(f"rows_found: {len(rows)}")
    print("")

    if rows:
        print("first_row:")
        print(json.dumps(rows[0], ensure_ascii=False, indent=2))
        print("")
        print("last_row:")
        print(json.dumps(rows[-1], ensure_ascii=False, indent=2))
    else:
        print("No data rows returned.")
        print("")
        print("full_payload:")
        print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
