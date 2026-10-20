# Assisted-by: OpenCode:fhgenie-pro/gpt-5.6-sol
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

EXAMPLE_DIRECTORY = Path(__file__).resolve().parent
DEFAULT_RESULTS_PATH = EXAMPLE_DIRECTORY / "results" / "simulation_results.csv"
DEFAULT_OUTPUT_PATH = EXAMPLE_DIRECTORY / "results" / "power_to_heat.png"

ELECTRIC_LOAD_COLUMN = (
    "uncontrolled_power_contribution_per_component_and_bus.electric_load.electricity"
)
STEAM_GENERATOR_LOSS_COLUMN = (
    "uncontrolled_power_contribution_per_component_and_bus.steam_generator.heat"
)  # added BBo
HEAT_LOAD_COLUMN = "uncontrolled_power_contribution_per_component_and_bus.heat_load.heat"
GRID_USAGE_COLUMN = "grid_builder_usage"
POWER_TO_HEAT_ELECTRICITY_COLUMN = "power_applied.power_to_heat.electricity"
THERMAL_STORAGE_POWER_COLUMN = "power_applied.thermal_storage.heat"
HEAT_BALANCE_COLUMN = "power_balance_per_bus.heat"
THERMAL_STORAGE_SOC_COLUMN = "components_states.thermal_storage.soc"
POWER_TO_HEAT_HEAT_COLUMN = "power_applied.power_to_heat.heat"
GAS_BOILER_HEAT_COLUMN = "power_applied.gas_boiler.heat"
GAS_BOILER_FUEL_COLUMN = "dispatch_results.gas_boiler.fuel_input_kw"
GAS_BOILER_LOSS_COLUMN = "dispatch_results.gas_boiler.loss_kw"


def plot_results(
        results_path: Path = DEFAULT_RESULTS_PATH,
        output_path: Path = DEFAULT_OUTPUT_PATH,
        show: bool = False,
) -> None:
    """Plot electrical and heat power flows from saved simulation results."""
    results = pd.read_csv(results_path, index_col="date_time", parse_dates=["date_time"])

    figure, (
        electric_axis,
        heat_axis,
        storage_axis,
        gas_axis,
    ) = plt.subplots(
        nrows=4,
        sharex=True,
        figsize=(11, 12),
    )

    electric_axis.step(
        results.index,
        -results[ELECTRIC_LOAD_COLUMN],
        where="post",
        label="Electrical load",
    )
    electric_axis.step(
        results.index,
        results[GRID_USAGE_COLUMN],
        where="post",
        label="Grid usage",
    )
    electric_axis.step(
        results.index,
        -results[POWER_TO_HEAT_ELECTRICITY_COLUMN],
        where="post",
        label="Power-to-heat electrical input",
    )
    electric_axis.set_ylabel("Electrical power [kW]")
    electric_axis.grid(True)
    electric_axis.legend()

    heat_axis.step(
        results.index,
        -results[HEAT_LOAD_COLUMN],
        where="post",
        label="Heat load",
    )
    heat_axis.step(
        results.index,
        results[HEAT_BALANCE_COLUMN],
        where="post",
        label="Heat balance",
    )
    heat_axis.step(
        results.index,
        results[THERMAL_STORAGE_POWER_COLUMN],
        where="post",
        label="Thermal storage contribution",
    )
    heat_axis.step(
        results.index,
        results[POWER_TO_HEAT_HEAT_COLUMN],
        where="post",
        label="P2H thermal output",
    )
    heat_axis.step(
        results.index,
        results[GAS_BOILER_HEAT_COLUMN],
        where="post",
        label="Gas boiler thermal output",
    )
    if STEAM_GENERATOR_LOSS_COLUMN in results.columns:
        heat_axis.step(
            results.index,
            -results[STEAM_GENERATOR_LOSS_COLUMN],
            where="post",
            label="Steam generator losses",
        )
        heat_axis.step(
            results.index,
            -results[HEAT_LOAD_COLUMN] + -results[STEAM_GENERATOR_LOSS_COLUMN],
            where="post",
            label="Heat demand including steam conversion",
        )
    heat_axis.set_ylabel("Thermal power [kW]")
    heat_axis.grid(True)
    heat_axis.legend()

    storage_axis.step(
        results.index,
        results[THERMAL_STORAGE_SOC_COLUMN] * 100,
        where="post",
        label="Thermal storage state of charge",
    )
    storage_axis.set_xlabel("Time")
    storage_axis.set_ylabel("State of charge [%]")
    storage_axis.set_ylim(0, 105)
    storage_axis.grid(True)
    storage_axis.legend()

    gas_axis.step(
        results.index,
        results[GAS_BOILER_HEAT_COLUMN],
        where="post",
        label="Gas boiler heat output",
    )
    gas_axis.step(
        results.index,
        results[GAS_BOILER_FUEL_COLUMN],
        where="post",
        label="Gas boiler fuel input",
    )
    gas_axis.step(
        results.index,
        results[GAS_BOILER_LOSS_COLUMN],
        where="post",
        label="Gas boiler conversion losses",
    )
    gas_axis.set_xlabel("Time")
    gas_axis.set_ylabel("Power [kW]")
    gas_axis.grid(True)
    gas_axis.legend()

    figure.suptitle("Power-to-heat example")
    figure.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=150, bbox_inches="tight")

    if show:
        plt.show()
    plt.close(figure)


if __name__ == "__main__":
    plot_results(show=True)
