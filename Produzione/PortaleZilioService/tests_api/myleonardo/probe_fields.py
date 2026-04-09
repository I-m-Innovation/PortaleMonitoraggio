"""Manual probe to summarize available MyLeonardo fields.

Optional:
    py Produzione/PortaleZilioService/tests_api/myleonardo/probe_fields.py
    py Produzione/PortaleZilioService/tests_api/myleonardo/probe_fields.py 2026-03-30T00:00:00 2026-03-30T23:59:59
"""

from __future__ import annotations

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

    print("== MyLeonardo fields probe ==")
    print(f"window_start: {start_dt.isoformat(sep=' ')}")
    print(f"window_end: {end_dt.isoformat(sep=' ')}")
    print(f"rows_found: {len(rows)}")
    print("")

    if not rows:
        print("No rows available.")
        return

    field_names = sorted({key for row in rows if isinstance(row, dict) for key in row.keys()})
    print("fields:")
    for field_name in field_names:
        print(f"- {field_name}")

    print("")
    print("sample_non_null_values:")
    for field_name in field_names:
        sample_value = None
        for row in rows:
            value = row.get(field_name)
            if value not in (None, ""):
                sample_value = value
                break
        print(f"{field_name}: {sample_value!r}")


if __name__ == "__main__":
    main()
