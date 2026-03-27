from __future__ import annotations

from datetime import datetime, timedelta
import time

import pandas as pd
import requests

from PortaleZilioService.API_inverter import saj_client


TIME_KEYS = ("dataTime", "time", "collectTime", "createTime", "recordTime", "timestamp")

PLANT_DEVICE_OVERRIDES = {
    "colroigo50kwp": {
        "device_serial_numbers_to_query": [
            "CSV6503J2416E00004",
        ],
        "bucket_aggregation": "nearest_grid",
        "timestamp_rounding": "none",
        "power_extraction_mode": "field",
        "power_field_name": "totalPVPower",
        "energy_field_name": "todayPvEnergy",
    },
    "ziliogroup490kw": {
        "device_serial_numbers_to_query": [
            "C6T9104J2314E00560", # inverter
            "C6T9104J2315E00670", # inverter
            "C6V9104G2424E00228", # inverter
            "C6V9104J2421E01334", # inverter
        ],
        "power_source": "ems_history",
        "ems_sn": "M5530J2428000038",
        "power_extraction_mode": "field",
        "power_field_name": "parallMeterPower",
        "energy_source": "ems_history",
        "energy_field_name": "parallTodayPVEnergy",
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


def _parse_float(value) -> float | None:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _round_timestamp_to_5min(timestamp: datetime) -> datetime:
    return pd.Timestamp(timestamp).round("5min").to_pydatetime()


def _extract_power_watts(record: dict, config: dict) -> float | None:
    field_name = config.get("power_field_name")
    if not field_name:
        return None
    return _parse_float(record.get(field_name))


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


def _get_ems_history_records(headers: dict[str, str], plant_id: str, ems_sn: str, start: datetime, end: datetime) -> list[dict]:
    windows: list[tuple[datetime, datetime]] = []
    cursor = start
    max_span = timedelta(hours=1, minutes=55)
    while cursor <= end:
        window_end = min(cursor + max_span, end)
        windows.append((cursor, window_end))
        if window_end >= end:
            break
        cursor = window_end + timedelta(minutes=5)

    merged_by_time: dict[str, dict] = {}
    for window_start, window_end in windows:
        payload = None
        for attempt in range(4):
            response = requests.get(
                f"{saj_client.BASE_URL}/open/api/device/emsHistoryData",
                headers={
                    **headers,
                    "Content-Type": "application/json",
                    "content-language": "en_US",
                },
                params={
                    "startTime": window_start.strftime("%Y-%m-%d %H:%M:%S"),
                    "endTime": window_end.strftime("%Y-%m-%d %H:%M:%S"),
                    "emsSn": ems_sn,
                    "plantId": plant_id,
                },
                timeout=30,
            )
            response.raise_for_status()
            payload = response.json()
            if payload.get("code") == 429:
                time.sleep(0.6 * (attempt + 1))
                continue
            break

        if payload is None:
            continue
        if payload.get("code") not in (None, 200):
            raise saj_client.SajApiError(
                f"Errore emsHistoryData SAJ per {ems_sn}: {payload.get('code')} {payload.get('msg')}"
            )
        records = payload.get("data", [])
        for record in records:
            if not isinstance(record, dict):
                continue
            data_time = record.get("dataTime")
            if not data_time:
                continue
            merged_by_time[str(data_time)] = record

    return [merged_by_time[key] for key in sorted(merged_by_time)]


def _get_plant_override_config(impianto) -> dict | None:
    return PLANT_DEVICE_OVERRIDES.get(_normalize(getattr(impianto, "nome_impianto", None)))


def _build_device_timeseries_dataframe(records: list[dict], config: dict) -> pd.DataFrame:
    rows = []
    rounding_mode = config.get("timestamp_rounding", "5min")
    for record in records:
        timestamp = _extract_timestamp(record)
        power_w = _extract_power_watts(record, config)
        if timestamp is None or power_w is None:
            continue
        if rounding_mode == "5min":
            timestamp = _round_timestamp_to_5min(timestamp)
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


def _extract_today_energy_from_source(
    config: dict,
    ems_records: list[dict],
    device_today_energy_values: list[float],
) -> float | None:
    if config.get("energy_source") == "ems_history":
        return _extract_last_today_energy_kwh(ems_records, config["energy_field_name"])
    return sum(device_today_energy_values) if device_today_energy_values else None


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


def _sample_nearest_to_5min_grid(
    device_dataframes: list[pd.DataFrame],
    start: datetime,
    end: datetime,
    tolerance: str = "2min30s",
) -> pd.DataFrame:
    if not device_dataframes:
        return pd.DataFrame(columns=["t", "P"])

    merged_df = (
        pd.concat(device_dataframes, ignore_index=True)
        .sort_values("timestamp")
        .drop_duplicates(subset=["timestamp"], keep="last")
        .reset_index(drop=True)
    )
    grid_df = pd.DataFrame({"timestamp": pd.date_range(start=start, end=end, freq="5min")})
    sampled_df = pd.merge_asof(
        grid_df,
        merged_df[["timestamp", "power_kw"]],
        on="timestamp",
        direction="nearest",
        tolerance=pd.Timedelta(tolerance),
    )
    sampled_df = sampled_df[sampled_df["power_kw"].notna()].reset_index(drop=True)
    sampled_df.columns = ["t", "P"]
    return sampled_df


def _fill_small_internal_gaps(df_time_series: pd.DataFrame, max_missing_points: int = 2) -> pd.DataFrame:
    if df_time_series.empty:
        return df_time_series

    working_df = df_time_series.copy()
    working_df["t"] = pd.to_datetime(working_df["t"])
    working_df = working_df.sort_values("t").drop_duplicates(subset=["t"], keep="last").reset_index(drop=True)

    full_index = pd.date_range(
        start=working_df["t"].iloc[0],
        end=working_df["t"].iloc[-1],
        freq="5min",
    )
    reindexed_df = (
        working_df.set_index("t")
        .reindex(full_index)
        .rename_axis("t")
        .reset_index()
    )
    missing_before = int(reindexed_df["P"].isna().sum())
    reindexed_df["P"] = reindexed_df["P"].interpolate(
        method="linear",
        limit=max_missing_points,
        limit_area="inside",
    )
    missing_after = int(reindexed_df["P"].isna().sum())
    return reindexed_df


def get_saj_day_data(impianto, start: datetime, end: datetime) -> tuple[pd.DataFrame, str, float | None]:
    config = _get_plant_override_config(impianto)
    if config is None:
        raise saj_client.SajApiError(f"Nessuna configurazione SAJ trovata per {impianto.nome_impianto!r}")

    device_serial_numbers = config["device_serial_numbers_to_query"]
    energy_field_name = config["energy_field_name"]

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
    ems_records: list[dict] = []

    if config.get("power_source") == "ems_history":
        ems_sn = config.get("ems_sn")
        if not ems_sn:
            raise saj_client.SajApiError(f"EMS SN non configurato per {impianto.nome_impianto!r}")

        ems_records = _get_ems_history_records(
            headers=headers,
            plant_id=str(plant["plantId"]),
            ems_sn=ems_sn,
            start=start,
            end=end,
        )
        ems_df = _build_device_timeseries_dataframe(ems_records, config)
        if not ems_df.empty:
            device_dataframes.append(ems_df)

    for device_sn in selected_device_serials:
        records = _get_history_records(headers, device_sn, start, end)
        if config.get("power_source") != "ems_history":
            device_df = _build_device_timeseries_dataframe(records, config)
            if not device_df.empty:
                device_dataframes.append(device_df)

        last_today_energy = _extract_last_today_energy_kwh(records, energy_field_name)
        if last_today_energy is not None:
            device_today_energy_values.append(last_today_energy)

    if config.get("bucket_aggregation") == "nearest_grid":
        df_time_series = _sample_nearest_to_5min_grid(device_dataframes, start=start, end=end)
    else:
        df_time_series = _aggregate_device_timeseries(device_dataframes)
    if config.get("power_source") == "ems_history" and not df_time_series.empty:
        df_time_series = _fill_small_internal_gaps(df_time_series, max_missing_points=2)
    if not df_time_series.empty:
        df_time_series = df_time_series[(df_time_series["t"] >= start) & (df_time_series["t"] <= end)]
        df_time_series = df_time_series.sort_values("t").reset_index(drop=True)
    today_energy_kwh = _extract_today_energy_from_source(config, ems_records, device_today_energy_values)
    print(
        f"SAJ DEBUG {impianto.nickname} power_source={config.get('power_source', 'devices')} "
        f"power_field={config.get('power_field_name')} "
        f"bucket_aggregation={config.get('bucket_aggregation', 'sum')} "
        f"selected_devices={len(selected_device_serials)} power_series={len(device_dataframes)} "
        f"points={len(df_time_series)} "
        f"today_energy_kwh={today_energy_kwh} energy_source={config.get('energy_source', 'devices')} "
        f"energy_field={config.get('energy_field_name')}"
    )
    led = _build_led_from_devices(devices)
    return df_time_series, led, today_energy_kwh
