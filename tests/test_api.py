"""Tests for guarded pyduro request/response handling."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest
from pyduro.actions import STATUS_PARAMS

from custom_components.aduro import api
from custom_components.aduro.api import (
    AduroClient,
    AduroConnectionError,
    AduroInvalidResponseError,
    AduroRejectedError,
    normalize_pin,
    normalize_serial,
)
from custom_components.aduro.model import AduroData


@dataclass
class Response:
    """Minimal pyduro response double."""

    function: int
    payload: str
    serial: str = "084956"
    status: int = 0
    sequence_number: int = 0


def status_payload(**overrides: Any) -> str:
    values = ["0"] * len(STATUS_PARAMS)
    indexes = {key: index for index, key in enumerate(STATUS_PARAMS)}
    for key, value in overrides.items():
        values[indexes[key]] = str(value)
    return ",".join(values)


def test_normalization_matches_pyduro_contract() -> None:
    assert normalize_serial("84956") == "084956"
    assert normalize_pin("12345678") == "1234567800"


def test_validate_accepts_matching_response(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        api.pyduro_raw,
        "run",
        lambda **kwargs: Response(11, status_payload(state=5, power_pct=50)),
    )
    AduroClient("192.0.2.10", "84956", "4438539130").validate()


def test_no_response_is_connection_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(api.pyduro_raw, "run", lambda **kwargs: None)
    with pytest.raises(AduroConnectionError, match="No response"):
        AduroClient("192.0.2.10", "84956", "4438539130").validate()


def test_incomplete_status_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(api.pyduro_raw, "run", lambda **kwargs: Response(11, "1,2,3"))
    with pytest.raises(AduroInvalidResponseError, match="incomplete"):
        AduroClient("192.0.2.10", "84956", "4438539130").validate()


@pytest.mark.parametrize(
    "response",
    [
        Response(11, "1,2", serial="999999"),
        Response(1, "1,2"),
        Response(11, "1,2", sequence_number=1),
    ],
)
def test_mismatched_response_is_rejected(
    monkeypatch: pytest.MonkeyPatch, response: Response
) -> None:
    monkeypatch.setattr(api.pyduro_raw, "run", lambda **kwargs: response)
    with pytest.raises(AduroInvalidResponseError):
        AduroClient("192.0.2.10", "84956", "4438539130").validate()


def test_nonzero_nbe_status_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        api.pyduro_raw,
        "run",
        lambda **kwargs: Response(11, "bad pin", status=3),
    )
    with pytest.raises(AduroRejectedError, match="status 3"):
        AduroClient("192.0.2.10", "84956", "4438539130").validate()


def test_fetches_complete_snapshot(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        api.pyduro_raw,
        "run",
        lambda **kwargs: Response(
            11,
            status_payload(
                boiler_temp=21.5,
                smoke_temp=83.2,
                state=5,
                substate=0,
                power_pct=50,
            ),
        ),
    )

    def fake_get(**kwargs: Any) -> Response:
        if kwargs["function_name"] == "consumption":
            return Response(6, "counter=1234.5,2,3")
        section = kwargs["path"].split(".", 1)[0]
        payloads = {
            "regulation": "operation_mode=1;fixed_power=50;",
            "boiler": "temp=22;",
            "auger": "forced_run=0;",
        }
        return Response(1, payloads[section])

    monkeypatch.setattr(api.pyduro_get, "run", fake_get)
    data = AduroClient("192.0.2.10", "84956", "4438539130").fetch_data()

    assert data.status["boiler_temp"] == 21.5
    assert data.status["state"] == 5
    assert data.setting("regulation", "operation_mode") == 1
    assert data.setting("boiler", "temp") == 22
    assert data.consumption_counter == (1234.5, 2.0, 3.0)
    assert not data.stale_sections


def test_optional_failure_retains_previous_section(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        api.pyduro_raw,
        "run",
        lambda **kwargs: Response(11, status_payload(state=5)),
    )

    def fake_get(**kwargs: Any) -> Response | None:
        if kwargs["function_name"] == "consumption":
            return Response(6, "counter=10")
        section = kwargs["path"].split(".", 1)[0]
        if section == "auger":
            return None
        return Response(1, "temp=20;" if section == "boiler" else "fixed_power=50;")

    monkeypatch.setattr(api.pyduro_get, "run", fake_get)
    previous = AduroData(settings={"auger": {"forced_run": 30}})
    data = AduroClient("192.0.2.10", "84956", "4438539130").fetch_data(previous)

    assert data.setting("auger", "forced_run") == 30
    assert "auger" in data.stale_sections
    assert data.status["state"] == 5


def test_set_is_allowlisted_and_validates_reply(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, int]] = []

    def fake_set(host: str, serial: str, pin: str, path: str, value: int) -> Response:
        calls.append((path, value))
        return Response(2, f"{path}={value}")

    monkeypatch.setattr(api.pyduro_set, "run", fake_set)
    client = AduroClient("192.0.2.10", "84956", "4438539130")
    client.set_value("regulation.operation_mode", 1)
    assert calls == [("regulation.operation_mode", 1)]

    with pytest.raises(ValueError, match="Unsupported"):
        client.set_value("manual.unsafe", 1)
