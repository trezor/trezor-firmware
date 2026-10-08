from __future__ import annotations

import logging
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pqhw.device import Unit  # noqa: E402
from pqhw.fixtures import DEFAULT_ROOT, Fixtures  # noqa: E402
from pqhw.report import Recorder  # noqa: E402

REPORTS = Path(__file__).resolve().parent / "reports"


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
        "--nrf-jlink",
        default=None,
        metavar="SERIAL",
        help="J-Link wired to the nRF (serial, or 'auto'): every baseline then "
        "puts the nRF on a known application image instead of whatever the "
        "previous run left there",
    )
    group.addoption(
        "--no-screens",
        action="store_true",
        help="skip SWD screenshots (each one takes a few seconds)",
    )
    group.addoption(
        "--report-dir",
        type=Path,
        default=REPORTS,
        help="where the HTML flow report goes (default: core/test_pq_hw/reports)",
    )
    group.addoption(
        "--stall",
        type=float,
        default=6.0,
        help="seconds of silence that count as a confirmation prompt",
    )


def pytest_configure(config: pytest.Config) -> None:
    # trezorlib logs every transport open/close at INFO; device waits poll.
    logging.getLogger("trezorlib").setLevel(logging.WARNING)
    config._pqhw_recorder = None  # type: ignore[attr-defined]


@pytest.hookimpl(wrapper=True, tryfirst=True)
def pytest_runtest_makereport(item: pytest.Item, call):
    report = yield
    setattr(item, f"_pqhw_rep_{report.when}", report)
    return report


def pytest_terminal_summary(terminalreporter, config: pytest.Config) -> None:
    recorder = config._pqhw_recorder  # type: ignore[attr-defined]
    if recorder is not None:
        path = recorder.write()
        if path is not None:
            terminalreporter.write_line(f"flow report: {path}")


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


def _asker(config: pytest.Config):
    capture = config.pluginmanager.getplugin("capturemanager")

    def ask(instruction: str) -> None:
        with capture.global_and_fixture_disabled():
            input(f"\n>>> {instruction}\n    press Enter when done ")

    return ask


@pytest.fixture(scope="session")
def recorder(request: pytest.FixtureRequest, fx: Fixtures) -> Recorder:
    config = request.config
    context = {
        "fixture set": f"{fx.root} (builder {fx.manifest.get('builder', '?')[:10]})",
        **{
            f"source {name}": f"{src['ref']} @ {src['commit'][:10]}"
            for name, src in fx.manifest.get("sources", {}).items()
        },
        "screenshots": "off" if config.getoption("--no-screens") else "SWD",
        "nRF reset": (
            f"J-Link {config.getoption('--nrf-jlink')}"
            if config.getoption("--nrf-jlink")
            else "off (the nRF keeps what the previous run left)"
        ),
        "releases": (
            "legacy = firmware 2.13.0, bootloader 2.1.18; intermediary = 2.13.1; "
            "A = 2.14.0 / 2.1.19; B = 2.14.1 / 2.1.20 (new bootloader code "
            "and nRF); B-fix = 2.14.2 / 2.1.20 with fix_version 2.14.1; "
            "C = 2.14.3 / 2.1.21, needs release 2.14.1 installed; "
            "E = 2.14.4 / 2.1.22, anti-rollback counter 4"
        ),
    }
    rec = Recorder(
        config.getoption("--report-dir"),
        screenshots=not config.getoption("--no-screens"),
        title="PQ secure boot hardware tests",
        context=context,
    )
    config._pqhw_recorder = rec  # type: ignore[attr-defined]
    return rec


@pytest.fixture(scope="session")
def unit(request: pytest.FixtureRequest) -> Unit:
    config = request.config
    unit = Unit(
        path=config.getoption("--unit-path"),
        stall=config.getoption("--stall"),
        ask=_asker(config) if config.getoption("--operator") else None,
        nrf_jlink=config.getoption("--nrf-jlink"),
    )
    if config.getoption("--hw"):
        unit.recorder = request.getfixturevalue("recorder")
    return unit


@pytest.fixture(autouse=True)
def _flow_record(request: pytest.FixtureRequest):
    """Record each hardware test's flow for the HTML report."""
    item = request.node
    if "hw" not in item.keywords or not request.config.getoption("--hw"):
        yield
        return
    rec: Recorder = request.getfixturevalue("recorder")
    rec.start(item.nodeid, getattr(item.function, "__doc__", None) or "")
    yield
    report = getattr(item, "_pqhw_rep_call", None) or getattr(
        item, "_pqhw_rep_setup", None
    )
    if report is None:
        rec.finish("unknown", 0.0, "", "")
        return
    rec.finish(
        report.outcome,
        report.duration,
        report.longreprtext if report.failed else "",
        report.caplog,
    )


@pytest.fixture
def operator(request: pytest.FixtureRequest):
    """Ask the person at the bench to do something, and wait until they have."""
    return _asker(request.config)
