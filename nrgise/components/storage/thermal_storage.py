from typing import Optional

from nrgise.common.types import Bus, PowerContribution
from nrgise.components.storage.storage_abc import StorageABC
from nrgise.common.constants import HEAT_BUS


class ThermalStorage(StorageABC):
    """
    A simple model of an thermal energy storage.

    Args:
        label: An unique identifier for the component.
        nom_power: Maximum of power which can be handled by the storage in kW.
        capacity: The overall capacity of the storage in kWh.
        time_delta_seconds: The duration of one time step in seconds.
        initial_soc: State of charge, in [0,1]
        efficiency_charge: Defines the efficiency of the storage when charging.
            When set to 0.95, 5% of the energy is considered lost when
            charging.
        efficiency_discharge: Defines the efficiency of the storage when discharging.
        power_bus: Bus to which charging and discharging power is contributed.
        temperature: Optional fixed storage temperature in degrees Celsius.
    """

    def __init__(
        self,
        label: str,
        capacity: float,  # max storage capacity
        time_delta_seconds: int,
        loss_per_timestep: float,  # added, Locomosa 0.0004 (hourly resolution)
        nom_power: float,  # charge/discharge limit, might be necessary to separate them
        max_charge_power: Optional[float] = None,  # added a optional maximum charge power
        max_discharge_power: Optional[float] = None,
        initial_soc: float = 0,
        efficiency_charge: float = 1,  # not implemented in locomosa
        efficiency_discharge: float = 1,  # not implemented in locomosa
        heat_bus: Bus = HEAT_BUS,
    ) -> None:
        self._label = label
        self._capacity = capacity
        self._time_delta_seconds = time_delta_seconds
        self._loss_per_timestep = loss_per_timestep
        self._max_charge_power = (
            max_charge_power if max_charge_power is not None else nom_power
        )
        self._max_discharge_power = (
            max_discharge_power if max_discharge_power is not None else nom_power
        )
        self._nom_power = max(self._max_charge_power, self._max_discharge_power)
        self._initial_soc = initial_soc
        self._soc = initial_soc
        self._efficiency_charge = efficiency_charge
        self._efficiency_discharge = efficiency_discharge
        self._heat_bus = heat_bus

    # Assisted-by: GitHub Copilot:GPT-6 Luna
    def set_power_contribution(self, power: float) -> PowerContribution:
        """
        Caution: Generated methodological logic; verification needed.

        Method summary:
        - Applies timestep losses, power limits, efficiencies, and SOC limits.

        Reasoning:
        - Mirrors Thermal Storage behavior while applying thermal loss to stored energy before dispatch.

        Assumptions and Limitations:
        - loss_per_timestep is a fraction of stored energy; temperature is fixed metadata, not dynamically calculated.

        Confidence Level: High
        ____
        Tries to apply requested power contribution (kW).

        1. Power limits are enforced.
        2. The state of charge is updated according to the applied power and the storage's capacity and efficiency.
        3. Power which was actually applied is returned.
        """

        capacity = self._capacity
        time_delta_h = self._time_delta_seconds / 3600
        self._soc *= 1 - self._loss_per_timestep
        soc = self._soc
        efficiency_charge = self._efficiency_charge
        efficiency_discharge = self._efficiency_discharge
        heat_bus = self._heat_bus

        power_limit = (
            self._max_discharge_power if power >= 0 else self._max_charge_power
            )
        power = super()._enforce_power_limit(power, power_limit)

        if power > 0 and capacity != 0:  # Discharge
            virtual_soc = (
                soc - 1 / efficiency_discharge * power * time_delta_h / capacity
            )
            if virtual_soc >= 0:  # Enough energy in storage to provide power
                self._soc = virtual_soc
            else:  # Not enough energy in storage => Storage empty
                power = soc * capacity / time_delta_h * efficiency_discharge
                self._soc = 0

        elif power < 0 and capacity != 0:  # Charging
            virtual_soc = soc + efficiency_charge * -power * time_delta_h / capacity
            if virtual_soc <= 1:  # Energy fits into storage
                self._soc = virtual_soc
            else:  # Energy does not fit into storage
                power = -(1 - soc) * capacity / time_delta_h * (1 / efficiency_charge)
                self._soc = 1
        else:  # Edge Case: applies only if power or capacity are 0
            power = 0

        return {self._heat_bus: power}

    def reset(self) -> None:
        """
        Resets the storage into its initial state.
        """
        self._soc = self._initial_soc

    def get_state(self) -> dict[str, float]:
        """
        Returns the state of charge.
        """
        return {"soc": self._soc}  # , "temperature": self._temperature}

    @property
    def capacity(self) -> float:
        return self._capacity
    
    @property
    def initial_soc(self) -> float:
        return self._initial_soc

    @property
    def loss_per_timestep(self) -> float:
        return self._loss_per_timestep

    @property
    def eta_charge(self) -> float:
        return self._efficiency_charge

    @property
    def eta_discharge(self) -> float:
        return self._efficiency_discharge

    @property
    def max_charge_power(self) -> float:
        return self._max_charge_power

    @property
    def max_discharge_power(self) -> float:
        return self._max_discharge_power

    @property
    def nom_power(self) -> float:
        return self._nom_power

    @property
    def soc(self) -> float:
        return self._soc

    @property
    def label(self) -> str:
        return self._label

    @property
    def time_delta_seconds(self) -> int:
        return self._time_delta_seconds

    @property
    def heat_bus(self) -> Bus:
        return self._heat_bus

    @property
    def power_bus(self) -> Bus:
        """Expose the heat bus through the common storage interface."""
        return self._heat_bus