# Assisted-by: Copilot SDK:unknown
from pathlib import Path

import pandas as pd
import math
import warnings
from heat_demand_controller import HeatDemandController
from plot_power_to_heat import plot_results
from read_and_preprocess_data import aggregate_hourly_power_demand, read_power_demand

from nrgise import EnergySystem, Simulation
from nrgise.common.constants import ELECTRICITY_BUS, HEAT_BUS
from nrgise.components import GasBoiler, Grid, Load, PowerToHeat, SteamGenerator, ThermalStorage
from nrgise.simulator.simulation import SimulationStepResult

# Heater Parameters
POWER_TO_HEAT_LABEL = "power_to_heat"
HEATER_EFFICIENCY = 0.95  # Heater efficiency added
ELECTRIC_HEATER_SIZE = 5000.0  # added, No limit on electrical input power
# Gas Boiler Parameters
GAS_BOILER_LABEL = "gas_boiler"  # added
GAS_BOILER_SIZE = 20000.0  # added, Size of the gas boiler, in kW
GAS_BOILER_EFFICIENCY = 0.80  # added, Efficiency of the gas boiler
# Steam Generator Parameters
USE_STEAM_GENERATOR = True  # added
STEAM_GENERATOR_LABEL = "steam_generator"  # added
STEAM_GENERATOR_EFFICIENCY = 0.98  # added
# Thermal Storage Parameters
THERMAL_STORAGE_LABEL = "thermal_storage"
THERMAL_STORAGE_LOSS_PER_TIMESTEP = 0.0004  # added, assuming loss of 0.04% per timestep (hourly)
THERMAL_STORAGE_CAPACITY = 24000.0
THERMAL_STORAGE_INITIAL_SOC = 0.0  # added, Initial state of charge for the thermal storage (50%)
THERMAL_STORAGE_POWER = 20000.0
THERMAL_STORAGE_MAX_CHARGE_POWER = 10000.0  # added, Maximum charge power for the thermal storage
THERMAL_STORAGE_MAX_DISCHARGE_POWER = 20000.0  # added, Maximum discharge power for the thermal storage
THERMAL_STORAGE_EFFICIENCY_CHARGE = 0.95  # added, Efficiency for charging the thermal storage
THERMAL_STORAGE_EFFICIENCY_DISCHARGE = 0.95  # added, Efficiency for discharging the thermal storage

#ELECTRIC_LOAD_KW = -4.0

EXAMPLE_DIRECTORY = Path(__file__).resolve().parent
RESULTS_PATH = EXAMPLE_DIRECTORY / "results" / "simulation_results.csv"
PLOT_PATH = EXAMPLE_DIRECTORY / "results" / "power_to_heat.png"


def create_energy_system() -> EnergySystem:
    """
    Caution: Generated methodological logic; verification needed.

    Method summary:
    - Use hourly mean useful heat demand in kW with its original timestamps.
    - Negate demand for nrgise and match the electrical placeholder length.

    Reasoning:
    - Preserve the measured demand scale and align both load profiles in time.

    Assumptions and Limitations:
    - Minute powers are assigned to their timestamp hour by the preprocessing.
    - Incomplete hours use available values, with an explicit warning.
    - No year mapping, demand scaling, or component resizing is performed.
    - Electrical demand remains an unvalidated constant placeholder.

    Confidence Level: High
    """
    heat_demand_minute, electricity_demand_minute = read_power_demand()
    heat_demand_hourly = aggregate_hourly_power_demand(heat_demand_minute)
    electricity_demand_hourly = aggregate_hourly_power_demand(electricity_demand_minute)
    
    """
    if not heat_demand_hourly.index.equals(electricity_demand_hourly.index):
        raise ValueError(
            "Heat and electricity demand have different hourly timestamps. "
            "Choose a common simulation period before running the simulation."
        )
    """
    # ____________________________________________________________________________________
    """
    Temporary solution for non-matching hourly timestamps between heat and electricity demand.
    Using only the period from September to December
    """
    
    common_index = heat_demand_hourly.index.intersection(
        electricity_demand_hourly.index,
    ).sort_values()

    if len(common_index) < 2:
        raise ValueError("The demand profiles have insufficient overlapping data.")

    time_differences = common_index.to_series().diff().iloc[1:]
    if not time_differences.eq(pd.Timedelta(hours=1)).all():
        raise ValueError("The overlapping simulation period contains hourly gaps.")

    warnings.warn(
        "Temporary alignment: restricting both demand profiles to "
        f"{common_index[0]} through {common_index[-1]} "
        f"({len(common_index)} hourly intervals).",
        UserWarning,
        stacklevel=2,
    )

    heat_demand_hourly = heat_demand_hourly.loc[common_index].copy()
    electricity_demand_hourly = electricity_demand_hourly.loc[common_index].copy()
    
    # ____________________________________________________________________________________
    
    
    HEAT_DEMAND_KW = heat_demand_hourly["power_demand_kw"]
    ELECTRIC_LOAD_KW = electricity_demand_hourly["power_demand_kw"]
    
    energy_system = EnergySystem(time_index=pd.DatetimeIndex(heat_demand_hourly.index))

    grid = Grid(label="grid")
    electric_load = Load(
        label="electric_load",
        power_profile=ELECTRIC_LOAD_KW,  # * len(electricity_demand_hourly),
        power_bus=ELECTRICITY_BUS,
    )
    heat_load = Load(
        label="heat_load",
        power_profile=HEAT_DEMAND_KW,
        power_bus=HEAT_BUS,
    )
    heater = PowerToHeat(
        label=POWER_TO_HEAT_LABEL,
        efficiency=HEATER_EFFICIENCY,
        electric_heater_size=ELECTRIC_HEATER_SIZE,  # added
        heat_bus=HEAT_BUS,
    )
    thermal_storage = ThermalStorage(
        label=THERMAL_STORAGE_LABEL,
        loss_per_timestep=THERMAL_STORAGE_LOSS_PER_TIMESTEP,  # added
        capacity=THERMAL_STORAGE_CAPACITY,
        initial_soc=THERMAL_STORAGE_INITIAL_SOC,  # added, Initial state of charge for the thermal storage
        nom_power=THERMAL_STORAGE_POWER,
        max_charge_power=THERMAL_STORAGE_MAX_CHARGE_POWER,  # Maximum charging power [kW]
        max_discharge_power=THERMAL_STORAGE_MAX_DISCHARGE_POWER,  # Maximum discharging power [kW]
        efficiency_charge=THERMAL_STORAGE_EFFICIENCY_CHARGE,  # added, Efficiency for charging the thermal storage
        efficiency_discharge=THERMAL_STORAGE_EFFICIENCY_DISCHARGE,  # added, Efficiency for discharging the thermal storage
        time_delta_seconds=energy_system.time_delta_seconds,
        heat_bus=HEAT_BUS,
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


# Assisted-by: Copilot SDK:unknown
def check_heat_supply(_simulation: Simulation, step_result: SimulationStepResult) -> None:
    """
    Caution: Generated methodological logic; verification needed.

    Method summary:
    - Stop unmet heat demand after actual dispatch.

    Reasoning:
    - The simulation grid builder balances electricity, not heat.

    Assumptions and Limitations:
    - A negative heat-bus balance denotes unmet upstream heat demand.
    - Absolute tolerance of 1e-9 kW handles floating-point roundoff only.
    - This check does not establish optimal dispatch or suitable plant sizing.

    Confidence Level: High
    """
    balance = step_result.power_balance_per_bus[HEAT_BUS]
    if balance < 0 and not math.isclose(balance, 0.0, abs_tol=1e-9):
        raise ValueError(
            f"Heat demand not covered at {step_result.date_time}: "
            f"{-balance:.6f} kW unmet demand. Review component sizes and dispatch; "
            "the real heat demand has not been scaled.",
        )


def run_example() -> pd.DataFrame:
    energy_system = create_energy_system()
    controller = HeatDemandController(
        energy_system=energy_system,
        power_to_heat_label=POWER_TO_HEAT_LABEL,
        thermal_storage_label=THERMAL_STORAGE_LABEL,
        gas_boiler_label=GAS_BOILER_LABEL,
    )
    simulation = Simulation(energy_system=energy_system, controller=controller)
    simulation.register_hook(check_heat_supply)
    return simulation.run()


def save_results(results: pd.DataFrame, output_path: Path = RESULTS_PATH) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    results.to_csv(output_path)


if __name__ == "__main__":
    results = run_example()
    save_results(results)
    plot_results(results_path=RESULTS_PATH, output_path=PLOT_PATH)
    print(f"Saved results to {RESULTS_PATH}")
    print(f"Saved plot to {PLOT_PATH}")
