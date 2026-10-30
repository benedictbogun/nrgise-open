import warnings
from pathlib import Path
from typing import Tuple

import numpy as np
import pandas as pd

INPUT_DIRECTORY = Path(__file__).resolve().parent / "input"

def read_power_demand() -> Tuple[pd.Series, pd.Series]:
    
    """
    Caution: Generated methodological logic; verification needed.

    Method summary:
    - Read heat demand in W and electricity demand in kW.
    - Convert heat demand to kW and return both demands as non-positive loads.

    Reasoning:
    - nrgise uses kW and negative power for consumption.
    - Electricity is already in kW and must not be divided by 1000.

    Assumptions and Limitations:
    - Source demand values are non-negative.
    - Missing values remain missing.
    - Original timestamps are retained; the two profiles are not aligned here.
    - Temporal overlap must be checked before joint simulation.

    Confidence Level: High
    """
    
    heat_data = pd.read_csv(
        INPUT_DIRECTORY / "Benninghoven_Simulation_Values.csv",
        sep=";",
        usecols=["date_time", "Qdot_heater_air_total:for_btissam/case_mods_only//sim_out_merged.csv"],
        index_col="date_time",
        parse_dates=["date_time"],
    )
    
    electricity_data = pd.read_csv(
        INPUT_DIRECTORY / "Benninghoven_Sensor_Values.csv",
        sep=",",
        usecols=["time", "Gesamtleistung_elektrisch[kW]"],
        index_col="time",
        parse_dates=["time"],
    )

    for name, data in (
        ("Heat", heat_data),
        ("Electricity", electricity_data),
    ):
        if (
            not isinstance(data.index, pd.DatetimeIndex)
            or data.empty
            or data.index.hasnans
        ):
            raise ValueError(f"{name} demand requires valid, non-empty timestamps.")

        if data.index.has_duplicates or not data.index.is_monotonic_increasing:
            raise ValueError(f"{name} demand timestamps must be unique and sorted.")

    heat_demand_w = -pd.to_numeric(heat_data["Qdot_heater_air_total:for_btissam/case_mods_only//sim_out_merged.csv"], errors="raise")
    electricity_demand_kw = -pd.to_numeric(electricity_data["Gesamtleistung_elektrisch[kW]"], errors="raise")

    for name, demand in (
        ("Heat", heat_demand_w),
        ("Electricity", electricity_demand_kw),
    ):
        if (demand > 0).any():
            raise ValueError(
                f"{name} demand must be non-negative.",
            )

    return (heat_demand_w / 1000).rename("heat_demand_kw"), electricity_demand_kw.rename("electricity_demand_kw")


def aggregate_hourly_power_demand(demand_minute_kw: pd.Series) -> pd.DataFrame:
    """
    Caution: Generated methodological logic; verification needed.

    Method summary:
    - Calculate hourly mean power demand and count valid minute values.

    Reasoning:
    - Mean power preserves energy for complete, equally weighted intervals.
    - Counts expose incomplete hours instead of silently filling gaps.

    Assumptions and Limitations:
    - Input is a unique, sorted, one-minute series in kW.
    - Values represent mean power for intervals assigned to their timestamp hour.
    - Incomplete hours contain means of available values only.
    - Hourly means do not preserve short-duration power peaks.

    Confidence Level: High
    """
    if not isinstance(demand_minute_kw.index, pd.DatetimeIndex):
        raise ValueError("Power demand requires a DatetimeIndex.")
    if demand_minute_kw.empty or demand_minute_kw.index.hasnans:
        raise ValueError("Power demand requires valid, non-empty timestamps.")

    time_differences = demand_minute_kw.index.to_series().diff().iloc[1:]
    if not time_differences.eq(pd.Timedelta(minutes=1)).all():
        raise ValueError("Power demand must have a regular one-minute index.")

    hourly = demand_minute_kw.resample(
        "1h",
        closed="left",  # 08:00 ≤ timestamp < 09:00
        label="left",  # label the resampled hour by its starting timestamp
    ).agg(["mean", "count"])  # count: number of valid minute values in each hour
    #note: locomosa uses maximum values of each hour

    hourly_demand = hourly.rename(
        columns={
            "mean": "power_demand_kw",
            "count": "valid_minutes",
        },
    )
    
    incomplete_hours = hourly_demand.loc[hourly_demand["valid_minutes"] != 60]
    if not incomplete_hours.empty:
        warnings.warn(
            "Hourly power demand contains incomplete hours; means use available "
            f"minute values only:\n{incomplete_hours.to_string()}",
            UserWarning,
            stacklevel=2,
        )
    
    return hourly_demand


if __name__ == "__main__":
    heat_demand_minute, electricity_demand_minute = read_power_demand()
    heat_demand_hourly = aggregate_hourly_power_demand(heat_demand_minute)
    electricity_demand_hourly = aggregate_hourly_power_demand(electricity_demand_minute)

    print("Heat demand:")
    print(heat_demand_hourly.head())
    print(f"Number of hours: {len(heat_demand_hourly)}")
    print(
        f"Period: {heat_demand_hourly.index.min()} "
        f"to {heat_demand_hourly.index.max()}",
    )

    print("\nElectricity demand:")
    print(electricity_demand_hourly.head())
    print(f"Number of hours: {len(electricity_demand_hourly)}")
    print(
        f"Period: {electricity_demand_hourly.index.min()} "
        f"to {electricity_demand_hourly.index.max()}",
    )

    if not heat_demand_hourly.index.equals(electricity_demand_hourly.index):
        warnings.warn(
            "Heat and electricity demand have different hourly timestamps. "
            "Align the simulation period explicitly before using them together.",
            UserWarning,
        )