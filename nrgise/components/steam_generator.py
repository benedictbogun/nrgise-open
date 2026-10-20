# Assisted-by: Copilot SDK:gpt-6.1-sol

from nrgise.common.constants import HEAT_BUS
from nrgise.common.types import Bus, PowerContribution
from nrgise.components.component_abc import ComponentABC


class SteamGenerator(ComponentABC):
    """Account for steam conversion losses on a single heat bus.

    Register one generator per heat bus using ``EnergySystem.add_components``.
    The state builder adds its conversion losses to the demand of all ``Load``
    components on that bus. Loads retain their useful-heat demand; heat sources
    and storage operate upstream of the conversion. No controller action is
    required for this component.

    Omit the component to run the same bus without steam conversion.

    Args:
        label: Unique identifier of the component.
        efficiency: Useful steam heat divided by thermal input, in (0, 1].
            Defaults to the LoCoMoSa optimization assumption of 0.98.
        heat_bus: Bus carrying the heat sources, storage, and useful-heat loads.
    """

    def __init__(
            self,
            label: str,
            efficiency: float = 0.98,
            heat_bus: Bus = HEAT_BUS,
    ) -> None:
        if not 0 < efficiency <= 1:
            raise ValueError("`efficiency` must be in the range (0, 1].")
        self._label = label
        self._efficiency = efficiency
        self._heat_bus = heat_bus

    def loss_power_contribution(self, useful_heat_demand: float) -> PowerContribution:
        """
        Caution: Generated methodological logic; verification needed.

        Method summary:
        - Add the conversion loss Q_useful / efficiency - Q_useful as bus demand.

        Reasoning:
        - Existing loads already consume Q_useful; adding only losses preserves
          their reported demand while requiring the correct upstream heat input.

        Assumptions and Limitations:
        - Constant LoCoMoSa-style efficiency, power in kW, no thermal dynamics,
          capacity limit, pressure model, or explicit steam mass flow.
        - Conversion applies to useful load demand, not storage charging.
        - This is a demand-side loss model, not proof that demand was supplied.

        Confidence Level: High
        """
        if useful_heat_demand < 0:
            raise ValueError("`useful_heat_demand` must be non-negative.")
        loss = useful_heat_demand / self._efficiency - useful_heat_demand
        return {self._heat_bus: -loss}

    def reset(self) -> None:
        """Reset the stateless component."""

    @property
    def label(self) -> str:
        return self._label

    @property
    def efficiency(self) -> float:
        return self._efficiency

    @property
    def heat_bus(self) -> Bus:
        return self._heat_bus
