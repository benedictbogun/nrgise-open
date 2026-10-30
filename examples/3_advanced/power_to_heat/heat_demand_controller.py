# Assisted-by: OpenCode:fhgenie-pro/gpt-5.6-sol
from typing import Any

from nrgise.common.state import State
from nrgise.common.types import ControlAction
from nrgise.components import GasBoiler, PowerToHeat, ThermalStorage
from nrgise.controllers import ControllerABC
from nrgise.energy_system import EnergySystem


class HeatDemandController(ControllerABC):
    """Charge during the first 12 steps and discharge afterward."""

    def __init__(
        self,
        energy_system: EnergySystem,
        power_to_heat_label: str,
        thermal_storage_label: str,
        gas_boiler_label: str,
    ) -> None:
        self._energy_system = energy_system
        self._power_to_heat_label = power_to_heat_label
        self._thermal_storage_label = thermal_storage_label
        self._gas_boiler_label = gas_boiler_label

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


        self._electric_heater = self._energy_system.get_component_by_label(self._power_to_heat_label)
        self._thermal_storage = self._energy_system.get_component_by_label(self._thermal_storage_label)
        self._gas_boiler = self._energy_system.get_component_by_label(self._gas_boiler_label)

        if not isinstance(self._electric_heater, PowerToHeat):
            raise TypeError(
                f"{self._power_to_heat_label!r} must identify a PowerToHeat component."
            )
        if not isinstance(self._thermal_storage, ThermalStorage):
            raise TypeError(
                f"{self._thermal_storage_label!r} must identify a ThermalStorage component."
            )
        if not isinstance(self._gas_boiler, GasBoiler):
            raise TypeError(
                f"{self._gas_boiler_label!r} must identify a GasBoiler component."
            )

        if not self._electric_heater.heat_bus == self._thermal_storage.heat_bus == self._gas_boiler.heat_bus:
            raise ValueError("All components must use the same heat bus.") 

        net_heat = state.uncontrolled_power_balance_per_bus[self._electric_heater.heat_bus]
        heat_demand = max(0.0, -net_heat)

        soc = float(state.components_states[self._thermal_storage_label]["soc"])

        # Validate storage parameters before proceeding with calculations
        if not 0 <= soc <= 1:
            raise ValueError("Storage SOC must be finite and in [0, 1].")
        if self._thermal_storage.time_delta_seconds <= 0:
            raise ValueError("Storage timestep must be positive.")
        if self._thermal_storage.capacity < 0:
            raise ValueError("Storage capacity must be non-negative.")
        if not 0 <= self._thermal_storage.loss_per_timestep <= 1:
            raise ValueError("Storage loss must be in [0, 1].")
        if not (
            0 < self._thermal_storage.eta_charge <= 1
            and 0 < self._thermal_storage.eta_discharge <= 1
        ):
            raise ValueError("Storage efficiencies must be in (0, 1].")
        if self._thermal_storage.max_charge_power < 0 or self._thermal_storage.max_discharge_power < 0:
            raise ValueError("Storage power limits must be non-negative.")

        dt_hours = self._thermal_storage.time_delta_seconds / 3600
        capacity = self._thermal_storage.capacity
        stored_energy = soc * capacity * (1 - self._thermal_storage.loss_per_timestep)

        max_charge = min(
            self._thermal_storage.max_charge_power,
            (capacity - stored_energy)
            / (self._thermal_storage.eta_charge * dt_hours),
        )
        max_discharge = min(
            self._thermal_storage.max_discharge_power,
            stored_energy * self._thermal_storage.eta_discharge / dt_hours,
        )
 
        max_heater_heat = (
            float("inf")
            if self._electric_heater.electric_heater_size is None
            else self._electric_heater.electric_heater_size * self._electric_heater.efficiency
        )
        max_boiler_heat = (
            self._gas_boiler.gas_boiler_size
            * self._gas_boiler.efficiency
        )

        if state.time_step < 12:
            spare_heat = max(
                0.0,
                max_heater_heat + max_boiler_heat - heat_demand,
            )
            storage_power = -min(max_charge, spare_heat)
        else:
            storage_power = min(max_discharge, heat_demand)

        required_heat = heat_demand - storage_power
        heater_heat = min(required_heat, max_heater_heat)
        boiler_heat = min(
            max(0.0, required_heat - heater_heat),
            max_boiler_heat,
        )
        
        return {
            self._electric_heater.label: heater_heat / self._electric_heater.efficiency,
            self._thermal_storage.label: storage_power,
            self._gas_boiler.label: boiler_heat / self._gas_boiler.efficiency,
        }, None