# Assisted-by: Copilot SDK:gpt-6.1-sol
from math import isfinite
from typing import Any

from nrgise.common.state import State
from nrgise.common.types import ControlAction
from nrgise.components import GasBoiler, PowerToHeat, ThermalStorage
from nrgise.controllers import ControllerABC


class HeatDemandController(ControllerABC):
    """Reference dispatch, not economic optimization.

    Charge storage during the first ``charge_steps``, then discharge for demand.
    Dispatch P2H before gas. Sizes and efficiencies come from the components.
    ``storage_loss_per_timestep`` must match the storage configuration.
    """

    def __init__(
            self,
            heater: PowerToHeat,
            gas_boiler: GasBoiler,
            storage: ThermalStorage,
            storage_loss_per_timestep: float,
            charge_steps: int = 12,
    ) -> None:
        if heater.heat_bus != gas_boiler.heat_bus or heater.heat_bus != storage.power_bus:
            raise ValueError("P2H, gas boiler, and storage must use the same heat bus.")
        if not isfinite(storage_loss_per_timestep) or not 0 <= storage_loss_per_timestep <= 1:
            raise ValueError("Storage loss must be finite and in [0, 1].")
        if not isinstance(charge_steps, int) or charge_steps < 0:
            raise ValueError("`charge_steps` must be a non-negative integer.")

        for name, value in (
            ("heater efficiency", heater.efficiency),
            ("boiler efficiency", gas_boiler.efficiency),
            ("storage charging efficiency", storage.eta_charge),
            ("storage discharging efficiency", storage.eta_discharge),
        ):
            if not isfinite(value) or not 0 < value <= 1:
                raise ValueError(f"{name} must be finite and in (0, 1].")

        for name, value in (
            ("boiler size", gas_boiler.gas_boiler_size),
            ("storage capacity", storage.capacity),
            ("storage nominal power", storage.nom_power),
        ):
            if not isfinite(value) or value < 0:
                raise ValueError(f"{name} must be finite and non-negative.")
        if heater.electric_heater_size is not None and (
            not isfinite(heater.electric_heater_size) or heater.electric_heater_size < 0
        ):
            raise ValueError("Heater size must be finite and non-negative.")
        if not isfinite(storage.time_delta_seconds) or storage.time_delta_seconds <= 0:
            raise ValueError("Storage timestep must be finite and positive.")

        self._heater = heater
        self._gas_boiler = gas_boiler
        self._storage = storage
        self._storage_loss = storage_loss_per_timestep
        self._charge_steps = charge_steps

    def get_action(self, state: State) -> tuple[ControlAction, Any]:
        """
        Caution: Generated methodological logic; verification needed.

        Method summary:
        - Predict feasible storage power from SOC, losses, and efficiencies.
        - Charge initially using spare source capacity; then discharge for demand.
        - Dispatch P2H first, then gas, and reject insufficient heat supply.

        Reasoning:
        - Sources must cover actual feasible storage dispatch, not an ideal schedule.
        - Externally configured sizes allow later sizing studies.

        Assumptions and Limitations:
        - Mirrors the current ThermalStorage loss-before-dispatch equations.
        - Supplied storage loss must match the component configuration.
        - No uncontrolled heat surplus, costs, or terminal SOC constraint.
        - Charging may use gas; this is a reference rule, not optimal operation.
        - A 1e-9 kW tolerance is used for numerical roundoff only.

        Confidence Level: High
        """
        heat_bus = self._heater.heat_bus
        net_heat = state.uncontrolled_power_balance_per_bus.get(heat_bus, 0.0)
        if not isfinite(net_heat):
            raise ValueError("Heat bus balance must be finite.")
        if net_heat > 1e-9:
            raise ValueError("This reference controller does not handle uncontrolled heat surplus.")
        demand = max(0.0, -net_heat)

        soc = float(state.components_states[self._storage.label]["soc"])
        if not isfinite(soc) or not 0 <= soc <= 1:
            raise ValueError("Storage SOC must be finite and in [0, 1].")
        dt_hours = self._storage.time_delta_seconds / 3600
        capacity = self._storage.capacity
        stored_energy = soc * capacity * (1 - self._storage_loss)
        max_discharge = min(
            self._storage.nom_power,
            stored_energy * self._storage.eta_discharge / dt_hours,
        )
        max_charge = min(
            self._storage.nom_power,
            (capacity - stored_energy) / (self._storage.eta_charge * dt_hours),
        )

        heater_size = self._heater.electric_heater_size
        max_p2h_heat = float("inf") if heater_size is None else heater_size * self._heater.efficiency
        max_boiler_heat = self._gas_boiler.gas_boiler_size * self._gas_boiler.efficiency

        if state.time_step < self._charge_steps:
            spare_generation = max(0.0, max_p2h_heat + max_boiler_heat - demand)
            storage_power = -min(max_charge, spare_generation)
        else:
            storage_power = min(max_discharge, demand)

        heat_required = demand - storage_power
        p2h_heat = min(heat_required, max_p2h_heat)
        boiler_heat = min(max(0.0, heat_required - p2h_heat), max_boiler_heat)
        unmet_heat = heat_required - p2h_heat - boiler_heat
        if unmet_heat > 1e-9:
            raise ValueError(
                f"Insufficient heat supply at step {state.time_step}: {unmet_heat:.6f} kW unmet.",
            )

        return {
            self._heater.label: p2h_heat / self._heater.efficiency,
            self._gas_boiler.label: boiler_heat / self._gas_boiler.efficiency,
            self._storage.label: storage_power,
        }, None
