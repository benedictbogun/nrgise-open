# Assisted-by: OpenCode:fhgenie-pro/gpt-5.6-sol
from pathlib import Path

import pandas as pd
from heat_demand_controller import HeatDemandController
from plot_power_to_heat import plot_results

from nrgise import EnergySystem, Simulation
from nrgise.common.constants import HEAT_BUS, ELECTRICITY_BUS
from nrgise.components import (Grid,
                               Load,
                               PowerToHeat,
                               ThermalStorage,
                               SteamGenerator,
                               GasBoiler)
# deleted Battery, added ThermalStorage, SteamGenerator and GasBoiler


HEATER_EFFICIENCY = 0.95  # Heater efficiency added
#TARGET_TEMPERATURE = None  # added, Target temperature for the heat output
ELECTRIC_HEATER_SIZE = 6.0  # added, No limit on electrical input power
GAS_BOILER_SIZE = 10.0  # added, Size of the gas boiler, in kW
GAS_BOILER_EFFICIENCY = 0.80  # added, Efficiency of the gas boiler
USE_STEAM_GENERATOR = True  # added
STEAM_GENERATOR_EFFICIENCY = 0.98  # added
STEAM_GENERATOR_LABEL = "steam_generator"  # added
POWER_TO_HEAT_LABEL = "power_to_heat"
THERMAL_STORAGE_LABEL = "thermal_storage"
GAS_BOILER_LABEL = "gas_boiler"  # added
THERMAL_STORAGE_LOSS_PER_TIMESTEP = 0.0004  # added, assuming loss of 0.04% per timestep (hourly)
THERMAL_STORAGE_CAPACITY = 24.0
THERMAL_STORAGE_POWER = 2.0
ELECTRIC_LOAD_PROFILE = [-4.0] * 24
HEAT_LOAD_PROFILE = [
    -6.0, -5.8, -5.5, -5.2, -5.0,
    -5.5, -7.0, -8.0, -7.0, -5.5,
    -4.0, -3.0, -2.5, -2.2, -2.5,
    -3.0, -4.5, -6.5, -8.0, -8.5,
    -8.0, -7.5, -7.0, -6.5
]
EXAMPLE_DIRECTORY = Path(__file__).resolve().parent
RESULTS_PATH = EXAMPLE_DIRECTORY / "results" / "simulation_results.csv"
PLOT_PATH = EXAMPLE_DIRECTORY / "results" / "power_to_heat.png"


def create_energy_system() -> EnergySystem:
    time_index = pd.date_range(
        "2024-01-01",
        periods=len(ELECTRIC_LOAD_PROFILE),
        freq="1h",
    )
    energy_system = EnergySystem(time_index=time_index)

    grid = Grid(label="grid")
    electric_load = Load(
        label="electric_load",
        power_profile=ELECTRIC_LOAD_PROFILE,
        power_bus=ELECTRICITY_BUS
    )
    heat_load = Load(
        label="heat_load",
        power_profile=HEAT_LOAD_PROFILE,
        power_bus=HEAT_BUS,
    )
    heater = PowerToHeat(
        label=POWER_TO_HEAT_LABEL,
        efficiency=HEATER_EFFICIENCY,
        electric_heater_size=ELECTRIC_HEATER_SIZE,  # added, No limit on electrical input power
        heat_bus=HEAT_BUS,
    )
    thermal_storage = ThermalStorage(
        label=THERMAL_STORAGE_LABEL,
        capacity=THERMAL_STORAGE_CAPACITY,
        nom_power=THERMAL_STORAGE_POWER,
        time_delta_seconds=energy_system.time_delta_seconds,
        loss_per_timestep=THERMAL_STORAGE_LOSS_PER_TIMESTEP,  # added, assuming no loss per timestep for simplicity
        power_bus=HEAT_BUS,
    )
    gas_boiler = GasBoiler(
        label=GAS_BOILER_LABEL,
        gas_boiler_size=GAS_BOILER_SIZE,
        efficiency=GAS_BOILER_EFFICIENCY,
        heat_bus=HEAT_BUS,
    )

    energy_system.add_components(grid, electric_load, heat_load, heater, thermal_storage, gas_boiler)

    if USE_STEAM_GENERATOR:
        steam_generator = SteamGenerator(
            label=STEAM_GENERATOR_LABEL,
            efficiency=STEAM_GENERATOR_EFFICIENCY,
            heat_bus=HEAT_BUS,
        )
        energy_system.add_components(steam_generator)

    return energy_system


def run_example() -> pd.DataFrame:
    energy_system = create_energy_system()
    controller = HeatDemandController(
        power_to_heat_label=POWER_TO_HEAT_LABEL,
        thermal_storage_label=THERMAL_STORAGE_LABEL,
        thermal_storage_power=THERMAL_STORAGE_POWER,
        efficiency=HEATER_EFFICIENCY,
        electric_heater_size=ELECTRIC_HEATER_SIZE,
        heat_bus=HEAT_BUS,
        gas_boiler=energy_system.get_component_by_label(GAS_BOILER_LABEL),
        thermal_storage=energy_system.get_component_by_label(THERMAL_STORAGE_LABEL),
        storage_loss_per_timestep=THERMAL_STORAGE_LOSS_PER_TIMESTEP,
    )
    return Simulation(energy_system=energy_system, controller=controller).run()


def save_results(results: pd.DataFrame, output_path: Path = RESULTS_PATH) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    results.to_csv(output_path)


if __name__ == "__main__":
    results = run_example()
    save_results(results)
    plot_results(results_path=RESULTS_PATH, output_path=PLOT_PATH)
    print(f"Saved results to {RESULTS_PATH}")
    print(f"Saved plot to {PLOT_PATH}")
