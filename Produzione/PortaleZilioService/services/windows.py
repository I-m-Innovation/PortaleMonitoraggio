from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta


@dataclass(frozen=True)
class MetricsWindow:
    start_date: date
    end_date: date
    label: str


def shift_year(value: date, years: int) -> date:
    target_year = value.year + years
    try:
        return value.replace(year=target_year)
    except ValueError:
        return value.replace(year=target_year, day=28)


def rolling_12_months_until_yesterday(today: date | None = None) -> MetricsWindow:
    current_day = today or date.today()
    end_date = current_day - timedelta(days=1)
    start_date = shift_year(end_date + timedelta(days=1), -1)
    return MetricsWindow(
        start_date=start_date,
        end_date=end_date,
        label=f"{start_date.isoformat()} -> {end_date.isoformat()}",
    )


def year_to_date_until_yesterday(today: date | None = None) -> MetricsWindow:
    current_day = today or date.today()
    end_date = current_day - timedelta(days=1)
    start_date = date(end_date.year, 1, 1)
    return MetricsWindow(
        start_date=start_date,
        end_date=end_date,
        label=f"YTD {end_date.year}",
    )
