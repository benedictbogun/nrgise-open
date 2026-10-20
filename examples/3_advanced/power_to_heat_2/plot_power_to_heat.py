# Assisted-by: Copilot SDK:gpt-6.1-sol
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

EXAMPLE_DIRECTORY = Path(__file__).resolve().parent
DEFAULT_RESULTS_PATH = EXAMPLE_DIRECTORY / "results" / "simulation_results.csv"
DEFAULT_OUTPUT_PATH = EXAMPLE_DIRECTORY / "results" / "power_to_heat.png"

ELECTRIC_LOAD_COLUMN = "uncontrolled_power_contribution_per_component_and_bus.electric_load.electricity"
HEAT_LOAD_COLUMN = "uncontrolled_power_contribution_per_component_and_bus.heat_load.heat"
STEAM_GENERATOR_LOSS_COLUMN = "uncontrolled_power_contribution_per_component_and_bus.steam_generator.heat"
GRID_USAGE_COLUMN = "grid_builder_usage"
POWER_TO_HEAT_ELECTRICITY_COLUMN = "power_applied.power_to_heat.electricity"
POWER_TO_HEAT_HEAT_COLUMN = "power_applied.power_to_heat.heat"
THERMAL_STORAGE_POWER_COLUMN = "power_applied.thermal_storage.heat"
THERMAL_STORAGE_SOC_COLUMN = "components_states.thermal_storage.soc"
HEAT_BALANCE_COLUMN = "power_balance_per_bus.heat"
GAS_BOILER_HEAT_COLUMN = "power_applied.gas_boiler.heat"
GAS_BOILER_FUEL_COLUMN = "gas_boiler.fuel_input_kw"
GAS_BOILER_LOSS_COLUMN = "gas_boiler.loss_kw"


def plot_results(
        results_path: Path = DEFAULT_RESULTS_PATH,
        output_path: Path = DEFAULT_OUTPUT_PATH,
        show: bool = False,
) -> None:
    """Plot electricity, upstream heat, storage SOC, and actual boiler fuel use.

    Heat demand retains useful load and optionally shows steam losses separately.
    Boiler fuel input and heat output are distinct powers in kW, not energies.
    """
    results = pd.read_csv(results_path, index_col="date_time", parse_dates=["date_time"])
    figure, (electric_axis, heat_axis, storage_axis, gas_axis) = plt.subplots(
        nrows=4,
        sharex=True,
        figsize=(12, 13),
    )
    try:
        electric_axis.step(
            results.index, -results[ELECTRIC_LOAD_COLUMN], where="post", label="Electrical load",
        )
        electric_axis.step(
            results.index, results[GRID_USAGE_COLUMN], where="post", label="Grid usage",
        )
        electric_axis.step(
            results.index, -results[POWER_TO_HEAT_ELECTRICITY_COLUMN],
            where="post", label="P2H electrical input",
        )
        electric_axis.set_ylabel("Electrical power [kW]")

        heat_axis.step(
            results.index, -results[HEAT_LOAD_COLUMN], where="post", label="Useful heat load",
        )
        heat_axis.step(
            results.index, results[POWER_TO_HEAT_HEAT_COLUMN], where="post", label="P2H thermal output",
        )
        heat_axis.step(
            results.index, results[GAS_BOILER_HEAT_COLUMN], where="post", label="Gas boiler thermal output",
        )
        heat_axis.step(
            results.index, results[THERMAL_STORAGE_POWER_COLUMN],
            where="post", label="Storage (+ discharge / - charge)",
        )
        heat_axis.step(
            results.index, results[HEAT_BALANCE_COLUMN], where="post", label="Heat balance",
        )
        if STEAM_GENERATOR_LOSS_COLUMN in results.columns:
            heat_axis.step(
                results.index, -results[STEAM_GENERATOR_LOSS_COLUMN],
                where="post", label="Steam generator losses",
            )
            heat_axis.step(
                results.index, -results[HEAT_LOAD_COLUMN] - results[STEAM_GENERATOR_LOSS_COLUMN],
                where="post", label="Heat demand including steam conversion",
            )
        heat_axis.set_ylabel("Thermal power [kW]")

        storage_axis.step(
            results.index, results[THERMAL_STORAGE_SOC_COLUMN] * 100,
            where="post", label="Storage SOC at start of timestep",
        )
        storage_axis.set_ylabel("State of charge [%]")
        storage_axis.set_ylim(0, 105)

        gas_axis.step(
            results.index, results[GAS_BOILER_FUEL_COLUMN], where="post", label="Gas boiler fuel input",
        )
        gas_axis.step(
            results.index, results[GAS_BOILER_HEAT_COLUMN], where="post", label="Gas boiler thermal output",
        )
        gas_axis.step(
            results.index, results[GAS_BOILER_LOSS_COLUMN], where="post", label="Gas boiler conversion losses",
        )
        gas_axis.set_ylabel("Power [kW]")
        gas_axis.set_xlabel("Time")
        for axis in (electric_axis, heat_axis, storage_axis, gas_axis):
            axis.grid(True)
            axis.legend(loc="upper left", fontsize="small", ncol=2)

        figure.suptitle("P2H, gas boiler, storage and optional steam conversion - reference dispatch")
        figure.tight_layout()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        figure.savefig(output_path, dpi=150, bbox_inches="tight")
        if show:
            plt.show()
    finally:
        plt.close(figure)


if __name__ == "__main__":
    plot_results(show=True)
