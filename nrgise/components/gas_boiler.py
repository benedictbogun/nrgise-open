# Assisted-by: Copilot SDK:gpt-6.1-sol

from nrgise.common.constants import HEAT_BUS
from nrgise.common.types import Bus, PowerContribution
from nrgise.components.capabilities.controllable_mixin import ControllableMixin
from nrgise.components.capabilities.publishes_dispatch_results_mixin import PublishesDispatchResultsMixin


class GasBoiler(ControllableMixin, PublishesDispatchResultsMixin):
    """
    Convert controlled fuel input into heat on a heat bus.

    Args:
        label: Unique component identifier.
        gas_boiler_size: Maximum fuel input power in kW.
        efficiency: Thermal output divided by fuel input.
        heat_bus: Bus receiving the thermal output.

    Fuel is accounted for as input power, not as a separate bus.
    """

    def __init__(
        self,
        label: str,
        gas_boiler_size: float,
        efficiency: float = 0.80,
        heat_bus: Bus = HEAT_BUS,
    ) -> None:
        if gas_boiler_size < 0:
            raise ValueError("`gas_boiler_size` must non-negative.")
        if not 0 < efficiency <= 1:
            raise ValueError("`efficiency` must be in the range (0, 1].")

        self._label = label
        self._gas_boiler_size = gas_boiler_size
        self._efficiency = efficiency
        self._heat_bus = heat_bus
        self.reset()

    def set_power_contribution(self, power: float) -> PowerContribution:
        """
        Caution: Generated methodological logic; verification needed.

        Method summary:
        - Limit fuel input to rated input power.
        - Convert actual fuel input to heat using constant efficiency.
        - Account for the difference as conversion loss.

        Reasoning:
        - Reproduces the fuel-side capacity and efficiency convention
          of the LoCoMoSa optimization model.

        Assumptions and Limitations:
        - All power values are in kW.
        - No minimum load, startup losses, ramps, or thermal dynamics.
        - Fuel supply is assumed available and is not a separate bus.
        - Efficiency and fuel input must use the same heating-value basis.

        Confidence Level: High

        Args:
            power: Requested non-negative fuel input power in kW.

        Returns:
            Actual positive thermal contribution to the heat bus in kW.
        """
        if power < 0:
            raise ValueError("Gas boiler input power must be non-negative.")

        self._fuel_input_power = min(power, self._gas_boiler_size)
        self._thermal_output_power = self._fuel_input_power * self._efficiency
        self._loss_power = self._fuel_input_power - self._thermal_output_power

        return {self._heat_bus: self._thermal_output_power}

    def get_dispatch_results(self) -> dict[str, float]:
        """Return actual powers of the most recently applied action in kW."""
        return {
            "fuel_input_kw": self._fuel_input_power,
            "thermal_output_kw": self._thermal_output_power,
            "loss_kw": self._loss_power,
        }

    def reset(self) -> None:
        """Clear the power values from the previous dispatch."""
        self._fuel_input_power = 0.0
        self._thermal_output_power = 0.0
        self._loss_power = 0.0

    @property
    def label(self) -> str:
        return self._label

    @property
    def gas_boiler_size(self) -> float:
        return self._gas_boiler_size

    @property
    def efficiency(self) -> float:
        return self._efficiency

    @property
    def heat_bus(self) -> Bus:
        return self._heat_bus

    @property
    def fuel_input_power(self) -> float:
        return self._fuel_input_power

    @property
    def thermal_output_power(self) -> float:
        return self._thermal_output_power
