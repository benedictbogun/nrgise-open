<!-- Assisted-by: Copilot SDK:unknown -->
# Power-to-heat: thermal baseline for MPC

This example is being adapted into an industrial energy-system MPC with the
objective of minimizing gas fuel input. **The current controller is rule-based,
not MPC, and does not guarantee minimum gas consumption.** The battery and an
explicit gas supply bus are not yet included.

## Step 1: thermal system boundary

The example now uses the real 2024 heat-demand profile in one-hour intervals.
Its conceptual energy paths are:

```text
Electricity grid --> Electrical load
                --> Electric heater --+
                                      |
Gas fuel ----------> Gas boiler -------+--> Heat bus <--> Thermal storage
                                              |
                                              v
                                    Steam conversion --> Useful heat load
```

In the implementation, steam conversion and useful heat demand are represented
on the same heat bus. `SteamGenerator` adds conversion losses to the load demand;
it is not a separate steam bus or a dynamic steam generator. The heater, boiler,
and storage are upstream of this conversion. Storage charging does not incur
steam conversion losses.

Gas is accounted for as the actual fuel input of `GasBoiler`, not as a bus
contribution. The electricity grid supplies both the independent electrical
load and the heater's electrical input.

### Current parameters

| Component | Parameter | Value |
|-----------|-----------|-------|
| Electrical load | Constant demand | 4 kW |
| Useful heat load | Hourly mean demand from CSV | 0 to approximately 21,356.29 kW |
| Electric heater | Maximum electrical input | 6 kW |
| Electric heater | Heat output / electrical input | 0.95 |
| Gas boiler | Maximum fuel input | 10 kW |
| Gas boiler | Heat output / fuel input | 0.80 |
| Steam conversion | Useful heat / upstream heat input | 0.98 |
| Thermal storage | Energy capacity | 24 kWh |
| Thermal storage | Initial state of charge | 50% |
| Thermal storage | Maximum charging / discharging power at heat bus | 1 / 2 kW |
| Thermal storage | Charging / discharging efficiency | 0.95 / 0.95 |
| Thermal storage | Standing loss per one-hour interval | 0.0004 of stored energy |

These are example inputs, not validated industrial plant parameters.
All powers are in kW and stored energy is in kWh. Boiler fuel input and
efficiency must use the same heating-value basis.

### Current dispatch rule

`HeatDemandController` reads heat demand including steam conversion losses.
It schedules storage charging during the first 12 simulation intervals and
discharging afterward, subject to available energy and power limits. This
original demonstration rule is not repeated daily and has not been adapted
into an annual operating strategy.
Standing losses are applied before charging or discharging.

For the remaining demand, the controller uses the electric heater first and
the gas boiler second. During the charging phase it may also use gas to charge
the storage. There is no forecast, optimization horizon, or terminal storage
constraint.

### Historical baseline with the original synthetic load

The prepared configuration was run and checked on 2026-10-28 using the existing
`nrgise-open` conda environment. Checks covered all 24 intervals:

- Useful heat plus steam losses matches upstream heat demand.
- Actual heater and boiler inputs match their outputs and efficiencies.
- Heat demand is fully supplied in every interval.
- Grid electricity equals electrical load plus heater input.
- Reported storage SOC and actual component powers respect their limits.
- Numerical results are finite.

| Quantity over 24 hours | Result |
|------------------------|--------|
| Useful heat demand | 134.200000 kWh |
| Steam conversion losses | 2.738776 kWh |
| Gas fuel input | 21.836382 kWh |
| Grid electricity | 211.127820 kWh |
| Initial stored energy | 12.000000 kWh |
| Final stored energy | 0.000000 kWh |

These are simulation results for the current rule, not an optimal solution or
empirical plant validation. Energy totals are calculated by summing actual
powers multiplied by interval duration. Gas consumption refers to fuel energy,
not gas volume.

The initial storage energy contributes to supplying the load. Since the store
ends empty, these totals must not be used as evidence of savings against a
scenario with a different initial or final stored energy.

## Step 2: connect real heat demand

`create_energy_system()` calls the existing functions in
`read_and_preprocess_data.py`. The CSV supplies useful heat demand in W, which
is converted to kW and aggregated to hourly means. The original 2024 timestamps
are used without year mapping or cyclic shifting. No demand scaling is applied.
Both load profiles have 8,784 values; the electrical load remains a constant
4 kW placeholder.

Hourly means preserve energy for complete, equally weighted minute intervals
when the input represents interval-mean power. They do not preserve minute
peaks. Incomplete hours use the available minute values and produce a warning.
The first hour has 57 valid values, all zero; its missing minutes are not filled
or assumed to be measured zeros. Non-finite or negative hourly demand is
rejected before simulation.

The hourly useful heat energy is approximately 10,547.60 MWh for this file.
This is not boiler fuel energy: steam conversion, generation efficiencies,
and storage operation affect the required inputs.

**Component sizes remain the original demonstration values.** They cannot
supply the real production load. A simulation hook checks actual heat supply
after every dispatch and raises an error at the first unmet demand, including
the timestamp and deficit in kW. An absolute tolerance of 1e-9 kW is used only
for numerical roundoff. No new CSV or plot is saved on a failed run; any old
results are not automatically deleted and must not be mistaken for new output.
Appropriate test sizes are a separate next step, not inferred from the data.

## Next steps toward MPC

1. Agree on the thermal optimization formulation: minimize gas fuel energy,
   enforce heat-demand coverage, and reproduce the component limits, losses,
   and efficiencies. Decide on the prediction horizon and terminal storage
   condition before implementation.
2. Implement and verify one optimization horizon before adding receding-horizon
   operation with storage-state feedback.
3. Extend the verified thermal MPC with the electrical subsystem and battery.

With unrestricted grid electricity and gas minimization alone, electric heat
will be preferred wherever feasible. Electricity costs, grid limits, and any
secondary objective are separate modeling decisions, not implicit parts of
gas minimization. A gas-only objective can admit multiple equally good storage
and heater schedules.

Methodological confidence: **High** for the described implementation behavior
and checked balances; applicability to an actual industrial plant remains
unvalidated. The model assumes constant efficiencies and energy-only thermal
storage; it does not resolve temperatures, pressure, steam mass flow, ramps,
or startup behavior.

## Running and plotting

Use an environment with the project dependencies installed, such as the
existing `nrgise-open` conda environment. Run from this example directory:

```powershell
python power_to_heat.py
```

After a successful run, the script writes `results/simulation_results.csv` and generates
`results/power_to_heat.png`. The four plot panels show electricity flows, boiler
fuel and heat flows, heat-bus contributions, and storage SOC. The reported SOC
is the state at the start of each interval; the last plotted SOC is not
necessarily the final state after the last dispatch.

To regenerate the plot from existing results:

```powershell
python plot_power_to_heat.py
```
