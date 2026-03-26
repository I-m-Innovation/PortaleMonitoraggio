from __future__ import annotations

from datetime import datetime

import pandas as pd
import requests

from PortaleZilioService.API_inverter import saj_client


TIME_KEYS = (
    "dataTime",
    "time",
    "collectTime",
    "createTime",
    "recordTime",
    "timestamp",
)

POWER_KEYS = (
    "totalPVPower",
    "totalPvPower",
    "pvPower",
)

PLANT_DEVICE_OVERRIDES = {
    "colroigo50kwp": {
        "device_serial_numbers_to_query": [
            "CSV6503J2416E00004",
        ],
        "api_response_field_for_instantaneous_power_watts": "totalPVPower",
        "api_response_field_for_energy_produced_today_kwh": "todayPvEnergy",
    },
}


def _normalize(value: str | None) -> str:
    if not value:
        return ""
    return "".join(ch for ch in str(value).lower() if ch.isalnum())


def _extract_timestamp(record: dict) -> datetime | None:
    for key in TIME_KEYS:
        raw_value = record.get(key)
        if raw_value in (None, ""):
            continue
        parsed = pd.to_datetime(raw_value, errors="coerce")
        if pd.notna(parsed):
            return parsed.to_pydatetime()
    return None


def _extract_numeric_value(record: dict, keys: tuple[str, ...]) -> float | None:
    for key in keys:
        raw_value = record.get(key)
        if raw_value in (None, ""):
            continue
        try:
            return float(raw_value)
        except (TypeError, ValueError):
            continue
    return None


def _parse_float(value) -> float | None:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _get_history_records(headers: dict[str, str], device_sn: str, start: datetime, end: datetime) -> list[dict]:
    response = requests.get(
        f"{saj_client.BASE_URL}/open/api/device/historyDataCommon",
        headers=headers,
        params={
            "deviceSn": device_sn,
            "startTime": start.strftime("%Y-%m-%d %H:%M:%S"),
            "endTime": end.strftime("%Y-%m-%d %H:%M:%S"),
            "fields": "deviceSn,dataTime,totalPVPower,todayPvEnergy,totalPvEnergy,pv1power,pv2power,pv3power,pv4power,pv5power,pv6power,pv7power,pv8power,pv9power,pv10power,pv11power,pv12power,pv13power,pv14power,pv15power,pv16power",
        },
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    records = payload.get("data", [])
    return [record for record in records if isinstance(record, dict)]


def _get_plant_override_config(impianto) -> dict | None:
    return PLANT_DEVICE_OVERRIDES.get(_normalize(getattr(impianto, "nome_impianto", None)))


def _build_device_timeseries_dataframe(records: list[dict], power_field_name: str) -> pd.DataFrame:
    rows = []
    for record in records:
        timestamp = _extract_timestamp(record)
        power_w = _parse_float(record.get(power_field_name))
        if timestamp is None or power_w is None:
            continue
        rows.append(
            {
                "timestamp": timestamp,
                # SAJ power values are returned in W; UI expects kW.
                "power_kw": power_w / 1000.0,
            }
        )

    if not rows:
        return pd.DataFrame(columns=["timestamp", "power_kw"])

    df_power = (
        pd.DataFrame(rows)
        .drop_duplicates(subset=["timestamp"], keep="last")
        .sort_values("timestamp")
        .reset_index(drop=True)
    )
    return df_power[["timestamp", "power_kw"]]


def _build_led_from_devices(devices: list[dict]) -> str:
    if not devices:
        return "led-gray"

    alarms = [device for device in devices if str(device.get("isAlarm", 0)) == "1"]
    online = [device for device in devices if str(device.get("isOnline", 0)) == "1"]

    if alarms:
        return "led-red"
    if online:
        return "led-green"
    return "led-gray"


def _find_matching_plant(plants: list[dict], impianto) -> dict | None:
    candidates = {
        _normalize(getattr(impianto, "nome_impianto", None)),
        _normalize(getattr(impianto, "nickname", None)),
        _normalize(getattr(impianto, "tag", None)),
    }
    candidates.discard("")

    for plant in plants:
        plant_keys = {
            _normalize(plant.get("plantName")),
            _normalize(str(plant.get("plantId"))),
        }
        if candidates & plant_keys:
            return plant
    return None


def _extract_last_today_energy_kwh(records: list[dict], energy_field_name: str) -> float | None:
    ordered = sorted(
        [record for record in records if _extract_timestamp(record) is not None],
        key=_extract_timestamp,
    )
    for record in reversed(ordered):
        value = _parse_float(record.get(energy_field_name))
        if value is not None:
            return value
    return None


def _aggregate_device_timeseries(device_dataframes: list[pd.DataFrame]) -> pd.DataFrame:
    if not device_dataframes:
        return pd.DataFrame(columns=["t", "P"])

    merged_df = pd.concat(device_dataframes, ignore_index=True)
    aggregated_df = (
        merged_df.groupby("timestamp", as_index=False)["power_kw"]
        .sum()
        .sort_values("timestamp")
        .reset_index(drop=True)
    )
    aggregated_df.columns = ["t", "P"]
    return aggregated_df


def get_saj_day_data(impianto, start: datetime, end: datetime) -> tuple[pd.DataFrame, str, float | None]:
    config = _get_plant_override_config(impianto)
    if config is None:
        raise saj_client.SajApiError(f"Nessuna configurazione SAJ trovata per {impianto.nome_impianto!r}")

    device_serial_numbers = config["device_serial_numbers_to_query"]
    power_field_name = config["api_response_field_for_instantaneous_power_watts"]
    energy_field_name = config["api_response_field_for_energy_produced_today_kwh"]

    token = saj_client.get_token()
    headers = saj_client.build_headers(token)

    plants = saj_client.get_plants(headers)
    plant = _find_matching_plant(plants, impianto)
    if plant is None:
        raise saj_client.SajApiError(f"Plant SAJ non trovato per {impianto.nome_impianto!r}")

    devices = saj_client.get_devices(headers, plant_id=str(plant["plantId"]))
    available_device_serials = {
        str(device.get("deviceSn"))
        for device in devices
        if device.get("deviceSn")
    }
    if not available_device_serials:
        raise saj_client.SajApiError(f"Nessun device SAJ trovato per {impianto.nome_impianto!r}")

    selected_device_serials = [
        device_sn for device_sn in device_serial_numbers if device_sn in available_device_serials
    ]
    if not selected_device_serials:
        raise saj_client.SajApiError(
            f"Nessuno dei device configurati SAJ e' disponibile per {impianto.nome_impianto!r}"
        )

    device_dataframes: list[pd.DataFrame] = []
    device_today_energy_values: list[float] = []

    for device_sn in selected_device_serials:
        records = _get_history_records(headers, device_sn, start, end)
        device_df = _build_device_timeseries_dataframe(records, power_field_name)
        if not device_df.empty:
            device_dataframes.append(device_df)

        last_today_energy = _extract_last_today_energy_kwh(records, energy_field_name)
        if last_today_energy is not None:
            device_today_energy_values.append(last_today_energy)

    df_time_series = _aggregate_device_timeseries(device_dataframes)
    if not df_time_series.empty:
        df_time_series = df_time_series[(df_time_series["t"] >= start) & (df_time_series["t"] <= end)]
        df_time_series = df_time_series.sort_values("t").reset_index(drop=True)
    today_energy_kwh = sum(device_today_energy_values) if device_today_energy_values else None
    led = _build_led_from_devices(devices)
    return df_time_series, led, today_energy_kwh
