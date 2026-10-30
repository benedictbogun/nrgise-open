# Assisted-by: Copilot SDK:unknown
import importlib
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def example(monkeypatch):
    directory = (
        Path(__file__).resolve().parents[1]
        / "examples" / "3_advanced" / "power_to_heat_mpc"
    )
    monkeypatch.syspath_prepend(str(directory))
    return importlib.import_module("power_to_heat")


def test_real_hourly_load_is_connected_without_scaling(example):
    hourly = example.aggregate_hourly_heat_demand(example.read_heat_demand())
    with pytest.warns(UserWarning, match="incomplete hours"):
        system = example.create_energy_system()
    state = system.reset()
    for label in ("electric_load", "heat_load"):
        component = system.get_component_by_label(label)
        assert len(component.data_profile) == 8784
    heat_load = system.get_component_by_label("heat_load")
    np.testing.assert_allclose(heat_load.data_profile, -hourly["heat_demand_kw"])
    assert system.time_delta_seconds == 3600
    assert state.uncontrolled_power_balance_per_bus["electricity"] == -4
    assert hourly.index[0] == pd.Timestamp("2024-01-01")
    assert hourly.index[-1] == pd.Timestamp("2024-12-31 23:00")
    assert hourly["heat_demand_kw"].max() == pytest.approx(21356.289666666664)


@pytest.mark.parametrize("invalid", [float("nan"), float("inf"), -1.0])
def test_invalid_hourly_demand_is_rejected(example, monkeypatch, invalid):
    hourly = pd.DataFrame(
        {"heat_demand_kw": [0.0, invalid], "valid_minutes": [60, 60]},
        index=pd.date_range("2024-01-01", periods=2, freq="1h"),
    )
    monkeypatch.setattr(example, "read_heat_demand", lambda: pd.Series(dtype=float))
    monkeypatch.setattr(example, "aggregate_hourly_heat_demand", lambda _: hourly)
    with pytest.raises(ValueError, match="finite and non-negative"):
        example.create_energy_system()


def test_small_complete_profile_still_runs(example, monkeypatch):
    minute_load = pd.Series(
        1.0, index=pd.date_range("2024-02-01", periods=120, freq="1min"),
    )
    monkeypatch.setattr(example, "read_heat_demand", lambda: minute_load)
    results = example.run_example()
    assert len(results) == 2
    assert results.index[0] == pd.Timestamp("2024-02-01")
    np.testing.assert_allclose(results["power_balance_per_bus.heat"], 0, atol=1e-9)
    np.testing.assert_allclose(
        results["uncontrolled_power_contribution_per_component_and_bus.heat_load.heat"],
        -1,
    )


def test_real_load_does_not_silently_run_with_undersized_components(example):
    with (
        pytest.warns(UserWarning, match="incomplete hours"),
        pytest.raises(ValueError, match="Heat demand not covered at .* kW unmet demand"),
    ):
        example.run_example()
