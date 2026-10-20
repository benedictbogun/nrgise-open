# Assisted-by: Copilot SDK:gpt-6.1-sol
# this file was completely created by Copilot SDK:gpt-6.1-sol and not verified
import pandas as pd
import pytest

from nrgise import EnergySystem
from nrgise.common.constants import ELECTRICITY_BUS, HEAT_BUS
from nrgise.common.state import build_state
from nrgise.components import Grid, Load, PowerProfile, PowerToHeat, SteamGenerator, ThermalStorage
from nrgise.simulator.simulation import Simulation


@pytest.mark.parametrize(
    "efficiency,demand,expected",
    [(0.98, 98, -2), (1.0, 98, 0), (0.5, 10, -10), (0.98, 0, 0)],
)
def test_conversion_loss(efficiency, demand, expected):
    generator = SteamGenerator("steam", efficiency=efficiency)
    assert generator.loss_power_contribution(demand) == {HEAT_BUS: pytest.approx(expected)}
    generator.reset()
    assert generator.label == "steam"
    assert generator.efficiency == efficiency
    assert generator.heat_bus == HEAT_BUS


@pytest.mark.parametrize("efficiency", [0, -0.1, 1.01, float("nan"), float("inf")])
def test_invalid_efficiency(efficiency):
    with pytest.raises(ValueError, match="efficiency"):
        SteamGenerator("steam", efficiency=efficiency)


@pytest.mark.parametrize("demand", [-1, float("nan"), float("inf")])
def test_invalid_demand(demand):
    with pytest.raises(ValueError, match="useful_heat_demand"):
        SteamGenerator("steam").loss_power_contribution(demand)


def test_loss_uses_gross_load_not_net_bus_balance():
    state = build_state([
        Load("load", [-98], power_bus=HEAT_BUS),
        PowerProfile("source", [50], power_bus=HEAT_BUS),
        SteamGenerator("steam"),
    ], time_step=0)
    assert state.uncontrolled_power_balance_per_bus[HEAT_BUS] == pytest.approx(-50)
    assert state.uncontrolled_power_contribution_per_component_and_bus["load"] == {HEAT_BUS: -98}
    assert state.uncontrolled_power_contribution_per_component_and_bus["steam"] == {
        HEAT_BUS: pytest.approx(-2),
    }


def test_optional_generator_custom_bus_multiple_loads_and_profile_updates():
    system = EnergySystem(pd.date_range("2024-01-01", periods=2, freq="1h"))
    system.add_components(
        Load("load_a", [-49, -49], power_bus="process_heat"),
        Load("load_b", [-49, 0], power_bus="process_heat"),
        Load("other_heat", [-10, -20], power_bus=HEAT_BUS),
        Load("electric", [-5, -6]),
    )
    assert system.reset().uncontrolled_power_balance_per_bus["process_heat"] == -98
    system.add_components(SteamGenerator("steam", heat_bus="process_heat"))
    for _ in range(2):
        state = system.reset()
        assert state.uncontrolled_power_balance_per_bus["process_heat"] == pytest.approx(-100)
        assert state.uncontrolled_power_balance_per_bus[HEAT_BUS] == -10
        assert state.uncontrolled_power_balance_per_bus[ELECTRICITY_BUS] == -5
        _, state, done = system.simulate_one_time_step({})
        assert not done
        assert state.uncontrolled_power_balance_per_bus["process_heat"] == pytest.approx(-50)
        assert state.uncontrolled_power_balance_per_bus[HEAT_BUS] == -20


def test_duplicate_generators_on_same_bus_are_rejected():
    with pytest.raises(ValueError, match="Only one SteamGenerator"):
        build_state([SteamGenerator("a"), SteamGenerator("b")], time_step=0)


def test_generators_on_different_buses():
    state = build_state([
        SteamGenerator("steam_a", efficiency=0.5, heat_bus="a"),
        SteamGenerator("steam_b", efficiency=0.8, heat_bus="b"),
        Load("load_a", [-10], power_bus="a"),
        Load("load_b", [-8], power_bus="b"),
    ], time_step=0)
    assert state.uncontrolled_power_balance_per_bus["a"] == -20
    assert state.uncontrolled_power_balance_per_bus["b"] == -10


@pytest.mark.parametrize("storage_power", [-2, 2])
def test_p2h_and_storage_balance_heat_without_double_counting_losses(storage_power):
    heater = PowerToHeat("p2h", electric_heater_size=200, efficiency=0.95)
    storage = ThermalStorage(
        "storage", nom_power=10, capacity=100, time_delta_seconds=3600,
        loss_per_timestep=0, initial_soc=0.5,
    )
    system = EnergySystem(pd.date_range("2024-01-01", periods=2, freq="1h"))
    system.add_components(
        heater, storage, SteamGenerator("steam"),
        Load("load", [-98, -98], power_bus=HEAT_BUS),
    )
    state = system.reset()
    applied, _, _ = system.simulate_one_time_step({
        "p2h": (100 - storage_power) / 0.95,
        "storage": storage_power,
    })
    balance = Simulation._calculate_power_balance_per_bus(state, applied)
    assert balance[HEAT_BUS] == pytest.approx(0)
    assert balance[ELECTRICITY_BUS] == pytest.approx(-(100 - storage_power) / 0.95)


def test_storage_charging_without_load_has_no_conversion_loss():
    state = build_state([SteamGenerator("steam")], time_step=0)
    balance = Simulation._calculate_power_balance_per_bus(
        state, {"source": {HEAT_BUS: 20}, "storage": {HEAT_BUS: -20}},
    )
    assert balance[HEAT_BUS] == 0


def test_insufficient_supply_remains_visible():
    state = build_state([
        Load("load", [-98], power_bus=HEAT_BUS), SteamGenerator("steam"),
    ], time_step=0)
    balance = Simulation._calculate_power_balance_per_bus(state, {"source": {HEAT_BUS: 90}})
    assert balance[HEAT_BUS] == pytest.approx(-10)


def test_simulation_reports_conversion_loss_separately():
    system = EnergySystem(pd.date_range("2024-01-01", periods=2, freq="1h"))
    system.add_components(
        Grid("grid"),
        Load("load", [-98, -49], power_bus=HEAT_BUS),
        PowerProfile("heat_source", [100, 50], power_bus=HEAT_BUS),
        SteamGenerator("steam"),
    )
    results = Simulation(system).run()
    assert results["power_balance_per_bus.heat"].tolist() == pytest.approx([0, 0])
    assert results["uncontrolled_power_contribution_per_component_and_bus.steam.heat"].tolist() == pytest.approx([-2, -1])
    assert results["uncontrolled_power_contribution_per_component_and_bus.load.heat"].tolist() == [-98, -49]
    assert results["grid_builder_usage"].tolist() == [0, 0]


def test_nonfinite_load_is_not_hidden():
    with pytest.raises(ValueError, match="useful_heat_demand"):
        build_state([
            Load("load", [float("nan")], power_bus=HEAT_BUS),
            SteamGenerator("steam"),
        ], time_step=0)
