<!-- Assisted-by: OpenCode:fhgenie-pro/gpt-5.6-sol -->
## Conversion

::: nrgise.components.PowerToHeat

<!-- Assisted-by: Copilot SDK:gpt-6.1-sol -->
## Optional steam conversion on one heat bus

::: nrgise.components.SteamGenerator

Add one `SteamGenerator` to enable conversion for all `Load` components on its
configured heat bus. Omit it to keep the original heat balance. No second bus
or additional controller action is needed.

```python
from nrgise.common.constants import HEAT_BUS
from nrgise.components import Load, SteamGenerator

heat_load = Load(label="heat_load", power_profile=[-98.0, -49.0], power_bus=HEAT_BUS)
energy_system.add_components(heat_load)

use_steam_generator = True
if use_steam_generator:
    energy_system.add_components(
        SteamGenerator(label="steam_generator", efficiency=0.98, heat_bus=HEAT_BUS),
    )
```

Use profiles matching the energy system's time index. At 98 kW useful demand
and 98% efficiency, the load still reports -98 kW and the generator reports
-2 kW in `uncontrolled_power_contribution_per_component_and_bus`. Controllers
therefore see -100 kW in `uncontrolled_power_balance_per_bus` for that bus.
P2H, storage discharge, and gas burners must together supply 100 kW.

Storage charging is upstream of conversion and causes no additional generator
loss. With no useful demand, generator loss is zero, even while charging.
This intentionally routes gas-burner heat through the generator too; LoCoMoSa's
original optimizer instead lets its gas boiler supply useful demand directly.

The model assumes constant efficiency and does not model capacity, temperatures,
pressure, or steam mass flow. Losses describe the heat required to serve demand;
they do not guarantee supply. A nonzero heat-bus residual in simulation results
still indicates unmet demand or excess supply. Custom demand components that
are not `Load` instances are not automatically treated as useful steam demand.
