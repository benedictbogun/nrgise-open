# Assisted-by: Copilot SDK:gpt-6.1-sol
"""Configurable P2H, gas boiler, storage, and optional steam conversion example.

Run this file to save a CSV and four-panel plot under this example's results/.
run_example() accepts component sizes for parameter studies. Dispatch is a
reference rule, not cost optimization, and imposes no terminal storage SOC.
"""

from pathlib import Path
from typing import Optional

import pandas as pd
from heat_demand_controller import HeatDemandController
from plot_power_to_heat import plot_results

from nrgise import EnergySystem, Simulation
from nrgise.common.constants import ELECTRICITY_BUS, HEAT_BUS
from nrgise.components import (
    GasBoiler,
    Grid,
    Load,
    PowerToHeat,
    SteamGenerator,
    ThermalStorage,
)

HEATER_EFFICIENCY = 0.95
ELECTRIC_HEATER_SIZE = 6.0  # kW electrical input; limited to demonstrate gas dispatch.
GAS_BOILER_SIZE = 10.0  # kW fuel input, not thermal output.
GAS_BOILER_EFFICIENCY = 0.80
USE_STEAM_GENERATOR = True
STEAM_GENERATOR_EFFICIENCY = 0.98
THERMAL_STORAGE_CAPACITY = 24.0  # kWh
THERMAL_STORAGE_POWER = 2.0  # kW on the heat bus
THERMAL_STORAGE_LOSS_PER_TIMESTEP = 0.0004

POWER_TO_HEAT_LABEL = "power_to_heat"
GAS_BOILER_LABEL = "gas_boiler"
THERMAL_STORAGE_LABEL = "thermal_storage"
STEAM_GENERATOR_LABEL = "steam_generator"

ELECTRIC_LOAD_PROFILE = [-4.0] * 24
HEAT_LOAD_PROFILE = [
    -6.0,
    -5.8,
    -5.5,
    -5.2,
    -5.0,
    -5.5,
    -7.0,
    -8.0,
    -7.0,
    -5.5,
    -4.0,
    -3.0,
    -2.5,
    -2.2,
    -2.5,
    -3.0,
    -4.5,
    -6.5,
    -8.0,
    -8.5,
    -8.0,
    -7.5,
    -7.0,
    -6.5,
]
EXAMPLE_DIRECTORY = Path(__file__).resolve().parent
RESULTS_PATH = EXAMPLE_DIRECTORY / "results" / "simulation_results.csv"
PLOT_PATH = EXAMPLE_DIRECTORY / "results" / "power_to_heat.png"


def create_energy_system(
    heater_size: Optional[float] = ELECTRIC_HEATER_SIZE,
    boiler_size: float = GAS_BOILER_SIZE,
    storage_capacity: float = THERMAL_STORAGE_CAPACITY,
    storage_power: float = THERMAL_STORAGE_POWER,
    use_steam_generator: bool = USE_STEAM_GENERATOR,
) -> EnergySystem:
    """Build a fresh system for each set of sizes; all heat uses the same bus."""
    time_index = pd.date_range(
        "2024-01-01", periods=len(ELECTRIC_LOAD_PROFILE), freq="1h"
    )
    energy_system = EnergySystem(time_index=time_index)
    heater = PowerToHeat(
        label=POWER_TO_HEAT_LABEL,
        efficiency=HEATER_EFFICIENCY,
        electric_heater_size=heater_size,
        heat_bus=HEAT_BUS,
    )
    storage = ThermalStorage(
        label=THERMAL_STORAGE_LABEL,
        capacity=storage_capacity,
        nom_power=storage_power,
        time_delta_seconds=energy_system.time_delta_seconds,
        loss_per_timestep=THERMAL_STORAGE_LOSS_PER_TIMESTEP,
        power_bus=HEAT_BUS,
    )
    boiler = GasBoiler(
        label=GAS_BOILER_LABEL,
        gas_boiler_size=boiler_size,
        efficiency=GAS_BOILER_EFFICIENCY,
        heat_bus=HEAT_BUS,
    )
    energy_system.add_components(
        Grid(label="grid"),
        Load(
            label="electric_load",
            power_profile=ELECTRIC_LOAD_PROFILE,
            power_bus=ELECTRICITY_BUS,
        ),
        Load(label="heat_load", power_profile=HEAT_LOAD_PROFILE, power_bus=HEAT_BUS),
        heater,
        storage,
        boiler,
    )
    if use_steam_generator:
        energy_system.add_components(
            SteamGenerator(
                label=STEAM_GENERATOR_LABEL,
                efficiency=STEAM_GENERATOR_EFFICIENCY,
                heat_bus=HEAT_BUS,
            ),
        )
    return energy_system


def run_example(
    heater_size: Optional[float] = ELECTRIC_HEATER_SIZE,
    boiler_size: float = GAS_BOILER_SIZE,
    storage_capacity: float = THERMAL_STORAGE_CAPACITY,
    storage_power: float = THERMAL_STORAGE_POWER,
    use_steam_generator: bool = USE_STEAM_GENERATOR,
) -> pd.DataFrame:
    """
    Caution: Generated methodological logic; verification needed.

    Method summary:
    - Simulate configurable sizes, check heat balance, and derive fuel and losses
      from actual boiler heat output.

    Reasoning:
    - Applied output reflects component limits; controller requests may not.
    - Convert kW to kWh using the simulation timestep for later evaluation.

    Assumptions and Limitations:
    - Constant boiler efficiency, no standby fuel consumption or economic model.
    - No terminal SOC condition; not sufficient for optimal sizing on its own.
    - A 1e-8 kW tolerance is used for numerical roundoff only.

    Confidence Level: High
    """
    energy_system = create_energy_system(
        heater_size=heater_size,
        boiler_size=boiler_size,
        storage_capacity=storage_capacity,
        storage_power=storage_power,
        use_steam_generator=use_steam_generator,
    )
    heater = energy_system.get_component_by_label(POWER_TO_HEAT_LABEL)
    boiler = energy_system.get_component_by_label(GAS_BOILER_LABEL)
    storage = energy_system.get_component_by_label(THERMAL_STORAGE_LABEL)
    if not isinstance(heater, PowerToHeat):
        raise TypeError("Configured P2H component is missing.")
    if not isinstance(boiler, GasBoiler):
        raise TypeError("Configured gas boiler is missing.")
    if not isinstance(storage, ThermalStorage):
        raise TypeError("Configured thermal storage is missing.")

    controller = HeatDemandController(
        heater=heater,
        gas_boiler=boiler,
        storage=storage,
        storage_loss_per_timestep=THERMAL_STORAGE_LOSS_PER_TIMESTEP,
    )
    results = Simulation(energy_system=energy_system, controller=controller).run()
    heat_balance = results[f"power_balance_per_bus.{HEAT_BUS}"]
    if not heat_balance.between(-1e-8, 1e-8).all():
        raise ValueError("Simulation contains a non-finite or unbalanced heat bus.")

    boiler_heat = results[f"power_applied.{GAS_BOILER_LABEL}.{HEAT_BUS}"]
    results["gas_boiler.fuel_input_kw"] = boiler_heat / boiler.efficiency
    results["gas_boiler.loss_kw"] = results["gas_boiler.fuel_input_kw"] - boiler_heat
    dt_hours = energy_system.time_delta_seconds / 3600
    results["gas_boiler.fuel_energy_kwh"] = (
        results["gas_boiler.fuel_input_kw"] * dt_hours
    )
    return results


def save_results(results: pd.DataFrame, output_path: Path = RESULTS_PATH) -> None:
    """Save timestep results, including actual boiler fuel use and losses."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    results.to_csv(output_path)


if __name__ == "__main__":
    results = run_example()
    save_results(results)
    plot_results(results_path=RESULTS_PATH, output_path=PLOT_PATH)
    print(f"Saved results to {RESULTS_PATH}")
    print(f"Saved plot to {PLOT_PATH}")
