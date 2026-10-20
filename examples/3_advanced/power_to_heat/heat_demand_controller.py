# Assisted-by: OpenCode:fhgenie-pro/gpt-5.6-sol
from typing import Any, Optional

from nrgise.common.state import State
from nrgise.common.types import Bus, ControlAction
from nrgise.components import GasBoiler, ThermalStorage
from nrgise.controllers import ControllerABC


class HeatDemandController(ControllerABC):
    """Control a power-to-heat component to balance uncontrolled heat demand."""

    def __init__(
            self,
            power_to_heat_label: str,
            thermal_storage_label: str,
            # gas_boiler: str,
            gas_boiler: GasBoiler,
            thermal_storage: ThermalStorage,
            thermal_storage_power: float,
            efficiency: float,
            electric_heater_size: Optional[float],
            heat_bus: Bus,
            # gas_boiler: GasBoiler,
            # thermal_storage: ThermalStorage,
            storage_loss_per_timestep: float,
    ) -> None:
        if efficiency <= 0:
            raise ValueError("`efficiency` must be greater than zero.")

        self._power_to_heat_label = power_to_heat_label
        self._thermal_storage_label = thermal_storage_label
        self._thermal_storage_power = thermal_storage_power
        self._efficiency = efficiency
        self._electric_heater_size = electric_heater_size
        self._heat_bus = heat_bus
        self._gas_boiler = gas_boiler
        self._storage = thermal_storage
        self._storage_loss = storage_loss_per_timestep

    def get_action(self, state: State) -> tuple[ControlAction, Any]:
        """
        Caution: Generated methodological logic; verification needed.

        Method summary:
        - Charge for the first 12 steps and discharge for the final 12 steps.
        - Use power-to-heat generation to keep the heat bus balanced.

        Reasoning:
        - Charging adds to heat demand, while discharging reduces heat demand.

        Assumptions and Limitations:
        - The simulation has 24 one-hour steps and the storage can apply the scheduled power.
        - COP is constant and heat demand remains above discharge power.

        Confidence Level: High
        """
        net_heat = state.uncontrolled_power_balance_per_bus[self._heat_bus]

        heat_demand = max(0.0, -net_heat)

        soc = float(
            state.components_states[self._thermal_storage_label]["soc"]
        )
        if not 0 <= soc <= 1:
            raise ValueError("Storage SOC must be finite and in [0, 1].")

        dt_hours = self._storage.time_delta_seconds / 3600
        capacity = self._storage.capacity
        stored_energy = soc * capacity * (1 - self._storage_loss)
        storage_limit = min(
            self._thermal_storage_power,
            self._storage.nom_power,
        )

        max_charge = min(
            storage_limit,
            (capacity - stored_energy)
            / (self._storage.eta_charge * dt_hours),
        )
        max_discharge = min(
            storage_limit,
            stored_energy * self._storage.eta_discharge / dt_hours,
        )

        max_p2h_heat = (
            float("inf")
            if self._electric_heater_size is None
            else self._electric_heater_size * self._efficiency
        )
        max_boiler_heat = (
            self._gas_boiler.gas_boiler_size
            * self._gas_boiler.efficiency
        )

        if state.time_step < 12:
            spare_heat = max(
                0.0,
                max_p2h_heat + max_boiler_heat - heat_demand,
            )
            storage_power = -min(max_charge, spare_heat)
        else:
            storage_power = min(max_discharge, heat_demand)

        required_heat = heat_demand - storage_power
        p2h_heat = min(required_heat, max_p2h_heat)
        boiler_heat = min(
            max(0.0, required_heat - p2h_heat),
            max_boiler_heat,
        )
        
        return {
            self._power_to_heat_label: p2h_heat / self._efficiency,
            self._storage.label: storage_power,
            self._gas_boiler.label: (
                boiler_heat / self._gas_boiler.efficiency
            ),
        }, None
        
"""
        return {
            self._power_to_heat_label: p2h_heat / self._efficiency,
            # self._thermal_storage_label: storage_power,
            self._storage: storage_power,
            self._gas_boiler.label: (
                boiler_heat / self._gas_boiler.efficiency
            ),
        }, None
"""