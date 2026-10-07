from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pqhw.device import Unit  # noqa: E402
from pqhw.fixtures import DEFAULT_ROOT, Fixtures  # noqa: E402


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("pq hardware tests")
    group.addoption(
        "--fixture-set",
        type=Path,
        default=DEFAULT_ROOT,
        help="fixture set directory (default: core/test_pq_hw/fixtures)",
    )
    group.addoption(
        "--hw",
        action="store_true",
        help="run tests that flash and drive the attached T3W1",
    )
    group.addoption(
        "--operator",
        action="store_true",
        help="run tests that need a person at the device (use with -s)",
    )
    group.addoption(
        "--unit-path",
        default=None,
        help="transport path of the unit, if several devices are connected",
    )
    group.addoption(
        "--stall",
        type=float,
        default=6.0,
        help="seconds of silence that count as a confirmation prompt",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list) -> None:
    hw = config.getoption("--hw")
    operator = config.getoption("--operator")
    for item in items:
        if "hw" in item.keywords and not hw:
            item.add_marker(pytest.mark.skip(reason="flashes the device: pass --hw"))
        if "operator" in item.keywords and not operator:
            item.add_marker(
                pytest.mark.skip(reason="needs a person: pass --operator -s")
            )


@pytest.fixture(scope="session")
def fx(request: pytest.FixtureRequest) -> Fixtures:
    fixtures = Fixtures(request.config.getoption("--fixture-set"))
    fixtures.verify()
    return fixtures


@pytest.fixture(scope="session")
def unit(request: pytest.FixtureRequest) -> Unit:
    return Unit(
        path=request.config.getoption("--unit-path"),
        stall=request.config.getoption("--stall"),
    )


@pytest.fixture
def operator(request: pytest.FixtureRequest):
    """Ask the person at the bench to do something, and wait until they have."""
    capture = request.config.pluginmanager.getplugin("capturemanager")

    def ask(instruction: str) -> None:
        with capture.global_and_fixture_disabled():
            input(f"\n>>> {instruction}\n    press Enter when done ")

    return ask
