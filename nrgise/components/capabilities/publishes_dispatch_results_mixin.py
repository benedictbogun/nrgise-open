from abc import ABC, abstractmethod

from nrgise.components.component_abc import ComponentABC


class PublishesDispatchResultsMixin(ComponentABC, ABC):
    """
    The operational values from the most recently executed action are published.

    The results are scalar snapshots, not bus messages.

    Implementations must retain these values until the next dispatch or reset.
    Updates within a time step must not delete or replace these values.

    ###Right now being used to save fuel input power, thermal input power and loss power of the gas boiler###
    """

    @abstractmethod
    def get_dispatch_results(self) -> dict[str, float]:
        """Return operating values from the most recently applied action."""
