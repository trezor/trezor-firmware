from __future__ import annotations

import shutil
from contextlib import contextmanager
from typing import Callable, Generator

import pytest
from _pytest.outcomes import Failed

from trezorlib.debuglink import TrezorClientDebugLink as Client

from . import common
from .common import SCREENS_DIR, UI_TESTS_DIR, TestCase, TestResult
from .reporting import testreport

FIXTURES_SUGGESTION_FILE = UI_TESTS_DIR / "fixtures.suggestion.json"


def _process_recorded(result: TestResult) -> None:
    # calculate hash
    result.store_recorded()
    testreport.recorded(result)


def _process_tested(result: TestResult) -> None:
    if result.expected_hash is None:
        file_path = testreport.missing(result)
        pytest.fail(
            f"Hash of {result.test.id} not found in fixtures.json\n"
            f"Expected:  {result.expected_hash}\n"
            f"Actual:    {result.actual_hash}\n"
            f"Diff file: {file_path}"
        )
    elif result.actual_hash != result.expected_hash:
        file_path = testreport.failed(result)
        pytest.fail(
            f"Hash of {result.test.id} differs\n"
            f"Expected:  {result.expected_hash}\n"
            f"Actual:    {result.actual_hash}\n"
            f"Diff file: {file_path}"
        )
    else:
        testreport.passed(result)


@contextmanager
def screen_recording(
    client: Client, request: pytest.FixtureRequest
) -> Generator[None, None, None]:
    test_ui = request.config.getoption("ui")
    if not test_ui:
        yield
        return

    record_text_layout = request.config.getoption("record_text_layout")

    testcase = TestCase.build(client, request)
    testcase.dir.mkdir(exist_ok=True, parents=True)

    # remove previous files
    shutil.rmtree(testcase.actual_dir, ignore_errors=True)
    testcase.actual_dir.mkdir()

    try:
        client.debug.start_recording(str(testcase.actual_dir))
        if record_text_layout:
            client.debug.set_screen_text_file(testcase.screen_text_file)
            client.debug.watch_layout(True)
        yield
    finally:
        client.ensure_open()
        # Wait for response to Initialize, which gives the emulator time to catch up
        # and redraw the homescreen. Otherwise there's a race condition between that
        # and stopping recording.
        if record_text_layout:
            client.debug.set_screen_text_file(None)
            client.debug.watch_layout(False)
        client.init_device()
        client.debug.stop_recording()

    result = testcase.build_result(request)
    if test_ui == "record":
        _process_recorded(result)
    else:
        _process_tested(result)


def setup(main_runner: bool) -> None:
    # clear metadata and "actual" recordings before current run, keep "recorded" around
    if main_runner:
        for meta in SCREENS_DIR.glob("*/metadata.json"):
            meta.unlink()
            shutil.rmtree(meta.parent / "actual", ignore_errors=True)

    # clear testreport
    testreport.setup(main_runner)


def list_missing() -> set[str]:
    # Only listing the ones for the current model
    _, missing = common.prepare_fixtures(
        TestResult.recent_results(), remove_missing=True
    )
    return {test.id for test in missing}


def update_fixtures(remove_missing: bool = False) -> int:
    """Update the fixtures.json file with the actual hashes from the latest run.

    Used in --ui=record and in update_fixtures.py
    """
    results = list(TestResult.recent_results())
    for result in results:
        result.store_recorded()

    common.write_fixtures(results, remove_missing=remove_missing)
    return len(results)


def _should_write_ui_report(exitstatus: pytest.ExitCode) -> bool:
    # generate UI report and check missing only if pytest is exitting cleanly
    # I.e., the test suite passed or failed (as opposed to ctrl+c break, internal error,
    # etc.)
    return exitstatus in (pytest.ExitCode.OK, pytest.ExitCode.TESTS_FAILED)


def terminal_summary(
    println: Callable[[str], None],
    ui_option: str,
    check_missing: bool,
    exitstatus: pytest.ExitCode,
) -> None:
    println("")

    normal_exit = _should_write_ui_report(exitstatus)
    missing_tests = list_missing()
    if ui_option and normal_exit and missing_tests:
        println(f"{len(missing_tests)} expected UI tests did not run.")
        if check_missing:
            println("-------- List of missing tests follows: --------")
            for test in missing_tests:
                println("\t" + test)

            if ui_option == "test":
                println("UI test failed.")
            elif ui_option == "record":
                println("Removing missing tests from record.")
            println("")

    if ui_option == "record" and exitstatus != pytest.ExitCode.OK:
        println(
            "\n-------- WARNING! Recording to fixtures.json was disabled due to failed tests. --------"
        )
        println("")

    if normal_exit:
        println("-------- UI tests summary: --------")
        println("Run ./tests/show_results.py to open test summary")
        println("")

        println("-------- Accepting all recent UI changes: --------")
        println("Run ./tests/update_fixtures.py to apply all changes")
        println("")


def sessionfinish(
    exitstatus: pytest.ExitCode,
    test_ui: str,
    check_missing: bool,
    record_text_layout: bool,
) -> pytest.ExitCode:
    if not _should_write_ui_report(exitstatus):
        return exitstatus

    testreport.generate_reports(record_text_layout)
    if test_ui == "test" and check_missing and list_missing():
        common.write_fixtures(
            TestResult.recent_results(),
            remove_missing=True,
            dest=FIXTURES_SUGGESTION_FILE,
        )
        return pytest.ExitCode.TESTS_FAILED

    if test_ui == "record" and exitstatus == pytest.ExitCode.OK:
        update_fixtures(check_missing)

    return exitstatus


def main() -> None:
    for result in TestResult.recent_results():
        try:
            _process_tested(result)
            print("PASSED:", result.test.id)
        except Failed:
            print("FAILED:", result.test.id)

    testreport.generate_reports()
