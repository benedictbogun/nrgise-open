import pytest

from nrgise import HEAT_BUS
from nrgise.components import ThermalStorage


def test_thermal_storage_applies_loss_and_charging_efficiency():
    storage = ThermalStorage(
        label="thermal_storage",
        nom_power=10,
        capacity=10,
        time_delta_seconds=3600,
        loss_per_timestep=0.1,
        initial_soc=0.5,
        efficiency_charge=0.8,
        temperature=80,
    )

    power = storage.set_power_contribution(-1)

    assert power == {HEAT_BUS: -1}
    assert storage.soc == pytest.approx(0.53)
    assert storage.get_state() == {"soc": pytest.approx(0.53), "temperature": 80}


def test_thermal_storage_limits_discharge_and_resets():
    storage = ThermalStorage(
        label="thermal_storage",
        nom_power=10,
        capacity=10,
        time_delta_seconds=3600,
        loss_per_timestep=0,
        initial_soc=0.1,
        temperature=70,
    )

    power = storage.set_power_contribution(5)

    assert power == {HEAT_BUS: pytest.approx(1)}
    assert storage.soc == 0

    storage.temperature = 75
    storage.reset()

    assert storage.soc == 0.1
    assert storage.temperature == 75
