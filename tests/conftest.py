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

import os
from typing import TYPE_CHECKING, Generator

import pytest

from trezorlib import debuglink, log
from trezorlib.debuglink import TrezorClientDebugLink as Client
from trezorlib.device import apply_settings, wipe as wipe_device
from trezorlib.transport import enumerate_devices, get_transport

from . import ui_tests
from .device_handler import BackgroundDeviceHandler
from .ui_tests.reporting import testreport

if TYPE_CHECKING:
    from _pytest.config import Config
    from _pytest.config.argparsing import Parser
    from _pytest.terminal import TerminalReporter

# So that we see details of failed asserts from this module
pytest.register_assert_rewrite("tests.common")


@pytest.fixture(scope="session")
def _raw_client(request: pytest.FixtureRequest) -> Client:
    path = os.environ.get("TREZOR_PATH")
    interact = int(os.environ.get("INTERACT", 0))
    if path:
        try:
            transport = get_transport(path)
            return Client(transport, auto_interact=not interact)
        except Exception as e:
            request.session.shouldstop = "Failed to communicate with Trezor"
            raise RuntimeError(f"Failed to open debuglink for {path}") from e

    else:
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
    and 'skip_t1'.

    The client instance is wiped and preconfigured with "all all all..." mnemonic, no
    password and no pin. It is possible to customize this with the `setup_client`
    marker.

    To specify a custom mnemonic and/or custom pin and/or enable passphrase:

    @pytest.mark.setup_client(mnemonic=MY_MNEMONIC, pin="9999", passphrase=True)

    To receive a client instance that was not initialized:

    @pytest.mark.setup_client(uninitialized=True)
    """
    if request.node.get_closest_marker("skip_t2") and _raw_client.features.model == "T":
        pytest.skip("Test excluded on Trezor T")
    if request.node.get_closest_marker("skip_t1") and _raw_client.features.model == "1":
        pytest.skip("Test excluded on Trezor 1")

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
            mnemonic=setup_params["mnemonic"],
            pin=setup_params["pin"],
            passphrase_protection=use_passphrase,
            label="test",
            language="en-US",
            needs_backup=setup_params["needs_backup"],
            no_backup=setup_params["no_backup"],
        )

        if _raw_client.features.model == "T":
            apply_settings(_raw_client, experimental_features=True)

        if use_passphrase and isinstance(setup_params["passphrase"], str):
            _raw_client.use_passphrase(setup_params["passphrase"])

        _raw_client.clear_session()

    if test_ui:
        with ui_tests.screen_recording(_raw_client, request):
            yield _raw_client
    else:
        yield _raw_client

    _raw_client.close()


def pytest_sessionstart(session: pytest.Session) -> None:
    ui_tests.read_fixtures()
    if session.config.getoption("ui"):
        testreport.clear_dir()


def _should_write_ui_report(exitstatus: pytest.ExitCode) -> bool:
    # generate UI report and check missing only if pytest is exitting cleanly
    # I.e., the test suite passed or failed (as opposed to ctrl+c break, internal error,
    # etc.)
    return exitstatus in (pytest.ExitCode.OK, pytest.ExitCode.TESTS_FAILED)


def pytest_sessionfinish(session: pytest.Session, exitstatus: pytest.ExitCode) -> None:
    if not _should_write_ui_report(exitstatus):
        return

    missing = session.config.getoption("ui_check_missing")
    test_ui = session.config.getoption("ui")

    if test_ui == "test":
        if missing and ui_tests.list_missing():
            session.exitstatus = pytest.ExitCode.TESTS_FAILED
        ui_tests.write_fixtures_suggestion(missing)
        testreport.index()
    if test_ui == "record":
        if exitstatus == pytest.ExitCode.OK:
            ui_tests.write_fixtures(missing)
        else:
            ui_tests.write_fixtures_suggestion(missing, only_passed_tests=True)
        testreport.index()


def pytest_terminal_summary(
    terminalreporter: "TerminalReporter", exitstatus: pytest.ExitCode, config: "Config"
) -> None:
    println = terminalreporter.write_line
    println("")

    ui_option = config.getoption("ui")
    missing_tests = ui_tests.list_missing()
    if ui_option and _should_write_ui_report(exitstatus) and missing_tests:
        println(f"{len(missing_tests)} expected UI tests did not run.")
        if config.getoption("ui_check_missing"):
            println("-------- List of missing tests follows: --------")
            for test in missing_tests:
                println("\t" + test)

            if ui_option == "test":
                println("UI test failed.")
            elif ui_option == "record":
                println("Removing missing tests from record.")
            println("")

    if ui_option == "test" and _should_write_ui_report(exitstatus):
        println("\n-------- Suggested fixtures.json diff: --------")
        print("See", ui_tests.SUGGESTION_FILE)
        println("")

    if ui_option == "record" and exitstatus != pytest.ExitCode.OK:
        println(
            f"\n-------- WARNING! Recording to {ui_tests.HASH_FILE.name} was disabled due to failed tests. --------"
        )
        print("See", ui_tests.SUGGESTION_FILE, "for suggestions for ONLY PASSED tests.")
        println("")

    if _should_write_ui_report(exitstatus):
        println("-------- UI tests summary: --------")
        println("Run ./tests/show_results.py to open test summary")
        println("")


def pytest_addoption(parser: "Parser") -> None:
    parser.addoption(
        "--ui",
        action="store",
        choices=["test", "record"],
        help="Enable UI intergration tests: 'record' or 'test'",
    )
    parser.addoption(
        "--ui-check-missing",
        action="store_true",
        default=False,
        help="Check UI fixtures are containing the appropriate test cases (fails on `test`,"
        "deletes old ones on `record`).",
    )


def pytest_configure(config: "Config") -> None:
    """Called at testsuite setup time.

    Registers known markers, enables verbose output if requested.
    """
    # register known markers
    config.addinivalue_line("markers", "skip_t1: skip the test on Trezor One")
    config.addinivalue_line("markers", "skip_t2: skip the test on Trezor T")
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
    if item.get_closest_marker("skip_t1") and item.get_closest_marker("skip_t2"):
        raise RuntimeError("Don't skip tests for both trezors!")

    skip_altcoins = int(os.environ.get("TREZOR_PYTEST_SKIP_ALTCOINS", 0))
    if item.get_closest_marker("altcoin") and skip_altcoins:
        pytest.skip("Skipping altcoin test")


def pytest_runtest_teardown(item: pytest.Item) -> None:
    """Called after a test item finishes.

    Dumps the current UI test report HTML.
    """
    if item.session.config.getoption("ui"):
        testreport.index()


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call) -> None:
    # Make test results available in fixtures.
    # See https://docs.pytest.org/en/latest/example/simple.html#making-test-result-information-available-in-fixtures
    # The device_handler fixture uses this as 'request.node.rep_call.passed' attribute,
    # in order to raise error only if the test passed.
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)


@pytest.fixture
def device_handler(client: Client, request: pytest.FixtureRequest) -> None:
    device_handler = BackgroundDeviceHandler(client)
    yield device_handler

    # get call test result
    test_res = ui_tests.get_last_call_test_result(request)

    if test_res is None:
        return

    # if test finished, make sure all background tasks are done
    finalized_ok = device_handler.check_finalize()
    if test_res and not finalized_ok:  # type: ignore [rep_call must exist]
        raise RuntimeError("Test did not check result of background task")
