"""Tests for Aduro state and value handling."""

from __future__ import annotations

import pytest

from custom_components.aduro.model import (
    AduroData,
    as_float,
    climate_mode_commands,
    climate_mode_key,
    fixed_power_for_preset,
    fixed_power_preset,
    is_heating,
    stove_state_key,
    values_equal,
)


@pytest.mark.parametrize(
    ("state", "substate", "expected"),
    [
        (14, 0, "off"),
        (14, 6, "stopping"),
        (2, 0, "ignition"),
        (4, 0, "extended_ignition"),
        (32, 0, "heating_up"),
        (5, 0, "running"),
        (0, 0, "waiting"),
        (6, 0, "temperature_reached"),
        (9, 0, "wood_burning"),
        (20, 0, "flame_out"),
        (13, 0, "ignition_failed"),
        (28, 0, "door_open"),
        (24, 0, "pellet_air_intake_closed"),
        (99, 1, "unknown"),
    ],
)
def test_stove_state_mapping(state: int, substate: int, expected: str) -> None:
    data = AduroData(status={"state": state, "substate": substate})
    assert stove_state_key(data) == expected


@pytest.mark.parametrize(
    ("state", "expected"),
    [(14, False), (13, False), (20, False), (28, False), (5, True), (24, True)],
)
def test_heating_mapping_matches_addon(state: int, expected: bool) -> None:
    assert is_heating(AduroData(status={"state": state})) is expected


def test_missing_heating_state_is_unknown() -> None:
    assert is_heating(AduroData()) is None


@pytest.mark.parametrize(
    ("state", "operation_mode", "expected"),
    [
        (14, 1, "off"),
        (13, 0, "off"),
        (20, 1, "off"),
        (28, 0, "off"),
        (5, 1, "auto"),
        (5, 0, "heat"),
        (0, 1, "auto"),
        (5, 2, None),
    ],
)
def test_climate_mode_uses_actual_power_state(
    state: int, operation_mode: int, expected: str | None
) -> None:
    data = AduroData(
        status={"state": state},
        settings={"regulation": {"operation_mode": operation_mode}},
    )
    assert climate_mode_key(data) == expected


def test_climate_mode_is_unknown_without_stove_state() -> None:
    data = AduroData(settings={"regulation": {"operation_mode": 1}})
    assert climate_mode_key(data) is None


@pytest.mark.parametrize(
    ("state", "configured_mode", "target_mode", "expected"),
    [
        (5, 1, "auto", ()),
        (5, 1, "heat", (("regulation.operation_mode", 0),)),
        (5, 0, "off", (("misc.stop", 1),)),
        (14, 1, "off", ()),
        (14, 1, "auto", (("misc.start", 1),)),
        (
            14,
            1,
            "heat",
            (("regulation.operation_mode", 0), ("misc.start", 1)),
        ),
    ],
)
def test_climate_command_plan_orders_mode_before_start(
    state: int,
    configured_mode: int,
    target_mode: str,
    expected: tuple[tuple[str, int], ...],
) -> None:
    data = AduroData(
        status={"state": state},
        settings={"regulation": {"operation_mode": configured_mode}},
    )
    assert climate_mode_commands(data, target_mode) == expected


def test_climate_command_plan_rejects_unknown_state_or_mode() -> None:
    assert climate_mode_commands(AduroData(), "auto") is None
    data = AduroData(status={"state": 5})
    assert climate_mode_commands(data, "unsupported") is None


@pytest.mark.parametrize(
    ("power", "expected"),
    [
        (10, "eco"),
        (39, "eco"),
        (40, "comfort"),
        (50, "comfort"),
        (90, "boost"),
        (100, "boost"),
    ],
)
def test_fixed_power_preset_mapping(power: int, expected: str) -> None:
    data = AduroData(
        status={"state": 5},
        settings={"regulation": {"operation_mode": 0, "fixed_power": power}},
    )
    assert fixed_power_preset(data) == expected


def test_fixed_power_preset_is_inactive_in_temperature_mode() -> None:
    data = AduroData(
        status={"state": 5},
        settings={"regulation": {"operation_mode": 1, "fixed_power": 100}},
    )
    assert fixed_power_preset(data) is None


def test_fixed_power_preset_is_inactive_while_stove_is_off() -> None:
    data = AduroData(
        status={"state": 14},
        settings={"regulation": {"operation_mode": 0, "fixed_power": 100}},
    )
    assert fixed_power_preset(data) is None


@pytest.mark.parametrize(
    ("preset", "expected"),
    [("eco", 10), ("comfort", 50), ("boost", 100), ("unknown", None)],
)
def test_fixed_power_for_preset(preset: str, expected: int | None) -> None:
    assert fixed_power_for_preset(preset) == expected


def test_protocol_value_comparison() -> None:
    assert values_equal("20", 20.0)
    assert values_equal("19.995", 20)
    assert not values_equal("19.5", 20)


@pytest.mark.parametrize("value", ["nan", "inf", "-inf"])
def test_non_finite_values_do_not_reach_home_assistant(value: str) -> None:
    assert as_float(value) is None
