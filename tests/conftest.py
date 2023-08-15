# This file is part of the Trezor project.
#
# Copyright (C) 2012-2019 SatoshiLabs and contributors
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3
# as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the License along with this library.
# If not, see <https://www.gnu.org/licenses/lgpl-3.0.html>.

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING, Generator, Iterator

import pytest
import xdist

from trezorlib import debuglink, log
from trezorlib.debuglink import TrezorClientDebugLink as Client
from trezorlib.device import apply_settings
from trezorlib.device import wipe as wipe_device
from trezorlib.transport import enumerate_devices, get_transport

from . import ui_tests
from .device_handler import BackgroundDeviceHandler
from .emulators import EmulatorWrapper

if TYPE_CHECKING:
    from _pytest.config import Config
    from _pytest.config.argparsing import Parser
    from _pytest.terminal import TerminalReporter

    from trezorlib._internal.emulator import Emulator


HERE = Path(__file__).resolve().parent


# So that we see details of failed asserts from this module
pytest.register_assert_rewrite("tests.common")


def _emulator_wrapper_main_args() -> list[str]:
    """Look at TREZOR_PROFILING env variable, so that we can generate coverage reports."""
    do_profiling = os.environ.get("TREZOR_PROFILING") == "1"
    if do_profiling:
        core_dir = HERE.parent / "core"
        profiling_wrapper = core_dir / "prof" / "prof.py"
        # So that the coverage reports have the correct paths
        os.environ["TREZOR_SRC"] = str(core_dir / "src")
        return [str(profiling_wrapper)]
    else:
        return ["-m", "main"]


@pytest.fixture
def core_emulator(request: pytest.FixtureRequest) -> Iterator[Emulator]:
    """Fixture returning default core emulator with possibility of screen recording."""
    with EmulatorWrapper("core", main_args=_emulator_wrapper_main_args()) as emu:
        # Modifying emu.client to add screen recording (when --ui=test is used)
        with ui_tests.screen_recording(emu.client, request) as _:
            yield emu


@pytest.fixture(scope="session")
def emulator(request: pytest.FixtureRequest) -> Generator["Emulator", None, None]:
    """Fixture for getting emulator connection in case tests should operate it on their own.

    Is responsible for starting it at the start of the session and stopping
    it at the end of the session - using `with EmulatorWrapper...`.

    Makes sure that each process will run the emulator on a different
    port and with different profile directory, which is cleaned afterwards.

    Used so that we can run the device tests in parallel using `pytest-xdist` plugin.
    Docs: https://pypi.org/project/pytest-xdist/

    NOTE for parallel tests:
    So that all worker processes will explore the tests in the exact same order,
    we cannot use the "built-in" random order, we need to specify our own,
    so that all the processes share the same order.
    Done by appending `--random-order-seed=$RANDOM` as a `pytest` argument,
    using system RNG.
    """

    model = str(request.session.config.getoption("model"))
    interact = os.environ.get("INTERACT") == "1"

    assert model in ("core", "legacy")
    if model == "legacy":
        raise RuntimeError(
            "Legacy emulator is not supported until it can be run on arbitrary ports."
        )

    def _get_port() -> int:
        """Get a unique port for this worker process on which it can run.

        Guarantees to be unique because each worker has a different name.
        gw0=>20000, gw1=>20003, gw2=>20006, etc.
        """
        worker_id = xdist.get_xdist_worker_id(request)
        assert worker_id.startswith("gw")
        # One emulator instance occupies 3 consecutive ports:
        # 1. normal link, 2. debug link and 3. webauthn fake interface
        return 20000 + int(worker_id[2:]) * 3

    with EmulatorWrapper(
        model,
        port=_get_port(),
        headless=True,
        auto_interact=not interact,
        main_args=_emulator_wrapper_main_args(),
    ) as emu:
        yield emu


@pytest.fixture(scope="session")
def _raw_client(request: pytest.FixtureRequest) -> Client:
    # In case tests run in parallel, each process has its own emulator/client.
    # Requesting the emulator fixture only if relevant.
    if request.session.config.getoption("control_emulators"):
        emu_fixture = request.getfixturevalue("emulator")
        return emu_fixture.client
    else:
        interact = os.environ.get("INTERACT") == "1"
        path = os.environ.get("TREZOR_PATH")
        if path:
            return _client_from_path(request, path, interact)
        else:
            return _find_client(request, interact)


def _client_from_path(
    request: pytest.FixtureRequest, path: str, interact: bool
) -> Client:
    try:
        transport = get_transport(path)
        return Client(transport, auto_interact=not interact)
    except Exception as e:
        request.session.shouldstop = "Failed to communicate with Trezor"
        raise RuntimeError(f"Failed to open debuglink for {path}") from e


def _find_client(request: pytest.FixtureRequest, interact: bool) -> Client:
    devices = enumerate_devices()
    for device in devices:
        try:
            return Client(device, auto_interact=not interact)
        except Exception:
            pass

    request.session.shouldstop = "Failed to communicate with Trezor"
    raise RuntimeError("No debuggable device found")


@pytest.fixture(scope="function")
def client(
    request: pytest.FixtureRequest, _raw_client: Client
) -> Generator[Client, None, None]:
    """Client fixture.

    Every test function that requires a client instance will get it from here.
    If we can't connect to a debuggable device, the test will fail.
    If 'skip_t2' is used and TT is connected, the test is skipped. Vice versa with T1
    and 'skip_t1'. Same with TR.

    The client instance is wiped and preconfigured with "all all all..." mnemonic, no
    password and no pin. It is possible to customize this with the `setup_client`
    marker.

    To specify a custom mnemonic and/or custom pin and/or enable passphrase:

    @pytest.mark.setup_client(mnemonic=MY_MNEMONIC, pin="9999", passphrase=True)

    To receive a client instance that was not initialized:

    @pytest.mark.setup_client(uninitialized=True)

    To enable experimental features:

    @pytest.mark.experimental
    """
    if request.node.get_closest_marker("skip_t2") and _raw_client.features.model == "T":
        pytest.skip("Test excluded on Trezor T")
    if request.node.get_closest_marker("skip_t1") and _raw_client.features.model == "1":
        pytest.skip("Test excluded on Trezor 1")
    if request.node.get_closest_marker("skip_tr") and _raw_client.features.model == "R":
        pytest.skip("Test excluded on Trezor R")

    sd_marker = request.node.get_closest_marker("sd_card")
    if sd_marker and not _raw_client.features.sd_card_present:
        raise RuntimeError(
            "This test requires SD card.\n"
            "To skip all such tests, run:\n"
            "  pytest -m 'not sd_card' <test path>"
        )

    test_ui = request.config.getoption("ui")

    _raw_client.reset_debug_features()
    _raw_client.open()
    try:
        _raw_client.init_device()
    except Exception:
        request.session.shouldstop = "Failed to communicate with Trezor"
        pytest.fail("Failed to communicate with Trezor")

    # Resetting all the debug events to not be influenced by previous test
    _raw_client.debug.reset_debug_events()

    if test_ui:
        # we need to reseed before the wipe
        _raw_client.debug.reseed(0)

    if sd_marker:
        should_format = sd_marker.kwargs.get("formatted", True)
        _raw_client.debug.erase_sd_card(format=should_format)

    wipe_device(_raw_client)

    setup_params = dict(
        uninitialized=False,
        mnemonic=" ".join(["all"] * 12),
        pin=None,
        passphrase=False,
        needs_backup=False,
        no_backup=False,
    )

    marker = request.node.get_closest_marker("setup_client")
    if marker:
        setup_params.update(marker.kwargs)

    use_passphrase = setup_params["passphrase"] is True or isinstance(
        setup_params["passphrase"], str
    )

    if not setup_params["uninitialized"]:
        debuglink.load_device(
            _raw_client,
            mnemonic=setup_params["mnemonic"],  # type: ignore
            pin=setup_params["pin"],  # type: ignore
            passphrase_protection=use_passphrase,
            label="test",
            language="en-US",
            needs_backup=setup_params["needs_backup"],  # type: ignore
            no_backup=setup_params["no_backup"],  # type: ignore
        )

        if request.node.get_closest_marker("experimental"):
            apply_settings(_raw_client, experimental_features=True)

        if use_passphrase and isinstance(setup_params["passphrase"], str):
            _raw_client.use_passphrase(setup_params["passphrase"])

        _raw_client.clear_session()

    with ui_tests.screen_recording(_raw_client, request):
        yield _raw_client

    _raw_client.close()


def _is_main_runner(session_or_request: pytest.Session | pytest.FixtureRequest) -> bool:
    """Return True if the current process is the main test runner.

    In case tests are run in parallel, the main runner is the xdist controller.
    We cannot use `is_xdist_controller` directly because it is False when xdist is
    not used.
    """
    return xdist.get_xdist_worker_id(session_or_request) == "master"


def pytest_sessionstart(session: pytest.Session) -> None:
    if session.config.getoption("ui"):
        ui_tests.setup(main_runner=_is_main_runner(session))


def pytest_sessionfinish(session: pytest.Session, exitstatus: pytest.ExitCode) -> None:
    test_ui = session.config.getoption("ui")
    if test_ui and _is_main_runner(session):
        session.exitstatus = ui_tests.sessionfinish(
            exitstatus,
            test_ui,  # type: ignore
            bool(session.config.getoption("ui_check_missing")),
            bool(session.config.getoption("record_text_layout")),
            bool(session.config.getoption("do_master_diff")),
        )


def pytest_terminal_summary(
    terminalreporter: "TerminalReporter", exitstatus: pytest.ExitCode, config: "Config"
) -> None:
    println = terminalreporter.write_line
    println("")

    ui_option = config.getoption("ui")
    if ui_option:
        ui_tests.terminal_summary(
            terminalreporter.write_line,
            ui_option,  # type: ignore
            bool(config.getoption("ui_check_missing")),
            exitstatus,
        )


def pytest_addoption(parser: "Parser") -> None:
    parser.addoption(
        "--ui",
        action="store",
        choices=["test", "record"],
        help="Enable UI integration tests: 'record' or 'test'",
    )
    parser.addoption(
        "--ui-check-missing",
        action="store_true",
        default=False,
        help="Check UI fixtures are containing the appropriate test cases (fails on `test`,"
        "deletes old ones on `record`).",
    )
    parser.addoption(
        "--control-emulators",
        action="store_true",
        default=False,
        help="Pytest will be responsible for starting and stopping the emulators. "
        "Useful when running tests in parallel.",
    )
    parser.addoption(
        "--model",
        action="store",
        choices=["core", "legacy"],
        help="Which emulator to use: 'core' or 'legacy'. "
        "Only valid in connection with `--control-emulators`",
    )
    parser.addoption(
        "--record-text-layout",
        action="store_true",
        default=False,
        help="Saving debugging traces for each screen change. "
        "Will generate a report with text from all test-cases.",
    )
    parser.addoption(
        "--do-master-diff",
        action="store_true",
        default=False,
        help="Generating a master-diff report. "
        "This shows all unique differing screens compared to master.",
    )


def pytest_configure(config: "Config") -> None:
    """Called at testsuite setup time.

    Registers known markers, enables verbose output if requested.
    """
    # register known markers
    config.addinivalue_line("markers", "skip_t1: skip the test on Trezor One")
    config.addinivalue_line("markers", "skip_t2: skip the test on Trezor T")
    config.addinivalue_line("markers", "skip_tr: skip the test on Trezor R")
    config.addinivalue_line(
        "markers", "experimental: enable experimental features on Trezor"
    )
    config.addinivalue_line(
        "markers",
        'setup_client(mnemonic="all all all...", pin=None, passphrase=False, uninitialized=False): configure the client instance',
    )
    with open(os.path.join(os.path.dirname(__file__), "REGISTERED_MARKERS")) as f:
        for line in f:
            config.addinivalue_line("markers", line.strip())

    # enable debug
    if config.getoption("verbose"):
        log.enable_debug_output()


def pytest_runtest_setup(item: pytest.Item) -> None:
    """Called for each test item (class, individual tests).

    Ensures that altcoin tests are skipped, and that no test is skipped on
    both T1 and TT.
    """
    if all(
        item.get_closest_marker(marker) for marker in ("skip_t1", "skip_t2", "skip_tr")
    ):
        raise RuntimeError("Don't skip tests for all trezor models!")

    skip_altcoins = int(os.environ.get("TREZOR_PYTEST_SKIP_ALTCOINS", 0))
    if item.get_closest_marker("altcoin") and skip_altcoins:
        pytest.skip("Skipping altcoin test")


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call) -> Generator:
    # Make test results available in fixtures.
    # See https://docs.pytest.org/en/latest/example/simple.html#making-test-result-information-available-in-fixtures
    # The device_handler fixture uses this as 'request.node.rep_call.passed' attribute,
    # in order to raise error only if the test passed.
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)


@pytest.fixture
def device_handler(client: Client, request: pytest.FixtureRequest) -> Generator:
    device_handler = BackgroundDeviceHandler(client)
    yield device_handler

    # get call test result
    test_res = ui_tests.common.get_last_call_test_result(request)

    if test_res is None:
        return

    # if test finished, make sure all background tasks are done
    finalized_ok = device_handler.check_finalize()
    if test_res and not finalized_ok:  # type: ignore [rep_call must exist]
        raise RuntimeError("Test did not check result of background task")
