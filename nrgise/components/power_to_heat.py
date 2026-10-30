# Assisted-by: OpenCode:fhgenie-pro/gpt-5.6-sol

from typing import Optional

from nrgise.common.constants import ELECTRICITY_BUS, HEAT_BUS
from nrgise.common.types import Bus, PowerContribution
from nrgise.components.capabilities.controllable_mixin import ControllableMixin


class PowerToHeat(ControllableMixin):
    """Convert controlled electrical input power into thermal output power.

    The control action is interpreted as the non-negative amount of electrical
    power consumed by the component. The returned contribution is negative on
    the electrical bus and positive on the heat bus.

    Args:
        label: Unique identifier of the component.
        efficiency: Constant efficiency, defined as thermal output power
        divided by electrical input power.
        electricity_bus: Bus from which electrical power is consumed.
        heat_bus: Bus to which thermal power is supplied.
        electric_heater_size: Maximum electrical input power in kW.
            None means unlimited input power.
    """
    """    BBo: Applied Changes
    Added efficiency as a parameter to represent the heater efficiency.
    Furthermore, the electric_heater_size parameter limits the maximum electrical input power.
    """
    """
    Note:
    Die standardmäßige Heizergröße wird so angesetzt, dass die maximale Nachfrage auch
    ohne Speicher und Gasboiler gedeckt werden kann:
    default_elec_heater_size = max(net_demand_no_losses_considered_per_timestep) /
    (elec_heater_eff * steam_gen_eff)
    """

    def __init__(
            self,
            label: str,
            electric_heater_size: Optional[float],
            efficiency: float = 1.0,  # default for a lossless heater is 1.0, locomosa has 0.95
            power_bus: Bus = ELECTRICITY_BUS,
            heat_bus: Bus = HEAT_BUS,
    ) -> None:
        if efficiency <= 0 or efficiency > 1:
            raise ValueError("`efficiency` must be in the range (0, 1].")
        if electric_heater_size is not None and electric_heater_size < 0:
            raise ValueError("`electric_heater_size` must be non-negative.")
        if power_bus == heat_bus:
            raise ValueError("`power_bus` and `heat_bus` must be different.")

        self._label = label
        self._efficiency = efficiency
        self._electric_heater_size = electric_heater_size
        self._power_bus = power_bus
        self._heat_bus = heat_bus

    def set_power_contribution(self, power: float) -> PowerContribution:
        """
        Caution: Generated methodological logic; verification needed.

        Method summary:
        - Limit electrical input to heater size and convert the actual input to heat.

        Reasoning:
        - Both bus contributions must reflect the same actual electrical input.

        Assumptions and Limitations:
        - Constant efficiency; no ramps, minimum load, or thermal dynamics.
        - No input limit is imposed when electric_heater_size is None.
        - ControllableMixin explicitly allows components to return less power than requested when
        physical constraints apply.

        Confidence Level: High

        Args:
            power: Non-negative electrical input power requested in kW.

        Returns:
            Negative electrical and positive thermal power contributions in kW.
        """
        if power < 0:
            raise ValueError("Power-to-heat input power must not be negative.")

        actual_input = power
        if self._electric_heater_size is not None:
            actual_input = min(actual_input, self._electric_heater_size)

        return {
            self._power_bus: -actual_input,
            self._heat_bus: actual_input * self._efficiency,
        }

    def reset(self) -> None:
        """Reset the stateless component."""

    @property
    def label(self) -> str:
        return self._label

    @property
    def efficiency(self) -> float:
        return self._efficiency

    @property
    def electric_heater_size(self) -> Optional[float]:
        return self._electric_heater_size

    @property
    def power_bus(self) -> Bus:
        return self._power_bus

    @property
    def heat_bus(self) -> Bus:
        return self._heat_bus
