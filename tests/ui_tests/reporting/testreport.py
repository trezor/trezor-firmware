from __future__ import annotations

import shutil
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import dominate.tags as t
from dominate.tags import (
    a,
    div,
    h1,
    h2,
    hr,
    i,
    p,
    script,
    span,
    strong,
    table,
    td,
    th,
    tr,
)
from dominate.util import text

from ..common import FixturesType, TestCase, TestResult
from . import download, html
from .common import REPORTS_PATH, document, generate_master_diff_report, get_diff

TESTREPORT_PATH = REPORTS_PATH / "test"
IMAGES_PATH = TESTREPORT_PATH / "images"

# These two html files are referencing each other
ALL_SCREENS = "all_screens.html"
ALL_UNIQUE_SCREENS = "all_unique_screens.html"


def _header(test_name: str, expected_hash: str | None, actual_hash: str) -> None:
    h1(test_name)
    with div():
        if actual_hash == expected_hash:
            p(
                "This test succeeded on UI comparison.",
                style="color: green; font-weight: bold;",
            )
        elif expected_hash is None:
            p(
                "This test is new and has no expected hash.",
                style="color: blue; font-weight: bold;",
            )
        else:
            p(
                "This test failed on UI comparison.",
                style="color: red; font-weight: bold;",
            )
        p("Expected: ", expected_hash or "(new test case)")
        p("Actual: ", actual_hash)
    hr()


def setup(main_runner: bool) -> None:
    """Delete and create the reports dir to clear previous entries."""
    if main_runner:
        shutil.rmtree(TESTREPORT_PATH, ignore_errors=True)
        TESTREPORT_PATH.mkdir(parents=True)
        (TESTREPORT_PATH / "failed").mkdir()
        (TESTREPORT_PATH / "passed").mkdir()
        (TESTREPORT_PATH / "new").mkdir()
        (TESTREPORT_PATH / "diff").mkdir()
        IMAGES_PATH.mkdir(parents=True)

    html.set_image_dir(IMAGES_PATH)


def index() -> Path:
    """Generate index.html with all the test results - lists of failed and passed tests."""
    passed_tests = list((TESTREPORT_PATH / "passed").iterdir())
    failed_tests = list((TESTREPORT_PATH / "failed").iterdir())
    new_tests = list((TESTREPORT_PATH / "new").iterdir())

    actual_hashes = {
        result.test.id: result.actual_hash for result in TestResult.recent_results()
    }

    title = "UI Test report " + datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    doc = document(title=title, index=True)

    with doc:
        h1("UI Test report")
        if not failed_tests:
            p("All tests succeeded!", style="color: green; font-weight: bold;")
        else:
            p("Some tests failed!", style="color: red; font-weight: bold;")
        hr()

        h2("Failed", style="color: red;")
        with p(id="file-hint"):
            strong("Tip:")
            text(" use ")
            t.span("./tests/show_results.sh", style="font-family: monospace")
            text(" to enable smart features.")

        with div("Test colors", _class="script-hidden"):
            with t.ul():
                with t.li():
                    t.span("new", style="color: blue")
                    t.button("clear all", onclick="resetState('all')")
                with t.li():
                    t.span("marked OK", style="color: grey")
                    t.button("clear", onclick="resetState('ok')")
                with t.li():
                    t.span("marked BAD", style="color: darkred")
                    t.button("clear", onclick="resetState('bad')")

        html.report_links(failed_tests, TESTREPORT_PATH, actual_hashes)

        h2("New tests", style="color: blue;")
        html.report_links(new_tests, TESTREPORT_PATH)

        h2("Passed", style="color: green;")
        html.report_links(passed_tests, TESTREPORT_PATH)

    return html.write(TESTREPORT_PATH, doc, "index.html")


def all_screens() -> Path:
    """Generate an HTML file for all the screens from the current test run.

    Shows all test-cases at one place.
    """
    recent_results = list(TestResult.recent_results())
    model = recent_results[0].test.model if recent_results else None

    title = "All test cases"
    doc = document(title=title, model=model)
    with doc:
        h1("All test cases")
        hr()

        count = 0
        result_count = 0
        for result in recent_results:
            result_count += 1
            h2(result.test.id, id=result.test.id)
            for image in result.images:
                # Including link to each image to see where else it occurs.
                with a(href=f"{ALL_UNIQUE_SCREENS}#{image}"):
                    html.image_link(image, TESTREPORT_PATH)
                count += 1

        h2(f"{count} screens from {result_count} testcases.")

    return html.write(TESTREPORT_PATH, doc, ALL_SCREENS)


def all_unique_screens() -> Path:
    """Generate an HTML file with all the unique screens from the current test run."""
    recent_results = TestResult.recent_results()
    result_count = 0
    model = None
    test_cases: dict[str, list[str]] = defaultdict(list)
    for result in recent_results:
        result_count += 1
        model = result.test.model
        for image in result.images:
            test_cases[image].append(result.test.id)

    test_case_pairs = sorted(test_cases.items(), key=lambda x: len(x[1]), reverse=True)

    title = "All unique screens"
    doc = document(title=title, model=model)
    with doc:
        h1("All unique screens")
        hr()

        for hash, tests in test_case_pairs:
            # Adding link to the appropriate hash, where other testcases
            # with the same hash (screen) are listed.
            with a(href=f"#{hash}"):
                with span(id="l-" + hash):
                    html.image_link(
                        hash, TESTREPORT_PATH, title=f"{len(tests)} testcases)"
                    )

        # Adding all screen hashes together with links to testcases having these screens.
        for hash, tests in test_case_pairs:
            h2(hash)
            with div(id=hash):
                with a(href=f"#l-{hash}"):
                    html.image_link(hash, TESTREPORT_PATH)
                for case in tests:
                    # Adding link to each test-case
                    with a(href=f"{ALL_SCREENS}#{case}"):
                        p(case)

        h2(f"{len(test_case_pairs)} unique screens from {result_count} testcases.")

    return html.write(TESTREPORT_PATH, doc, ALL_UNIQUE_SCREENS)


def differing_screens() -> None:
    """Creating an HTML page showing all the unique screens that got changed."""
    unique_diffs: set[tuple[str | None, str | None]] = set()

    def already_included(left: str | None, right: str | None) -> bool:
        return (left, right) in unique_diffs

    def include(left: str | None, right: str | None) -> None:
        unique_diffs.add((left, right))

    # Only going through tests failed in UI comparison,
    # there are no differing screens in UI-passed tests.
    recent_ui_failures = list(TestResult.recent_ui_failures())

    model = recent_ui_failures[0].test.model if recent_ui_failures else None
    doc = document(title="Differing screens", model=model)
    with doc.head:
        script(
            type="text/javascript", src="https://cdn.jsdelivr.net/npm/pixelmatch@5.3.0"
        )
    with doc:
        with table(border=1, width=600):
            with tr():
                th("Expected")
                th("Actual")
                th("Diff")
                th("Testcase (link)")

            for ui_failure in recent_ui_failures:
                for recorded, actual in ui_failure.diff_lines():
                    if recorded != actual and not already_included(recorded, actual):
                        include(recorded, actual)
                        with tr(bgcolor="red"):
                            html.image_column(recorded, TESTREPORT_PATH)
                            html.image_column(actual, TESTREPORT_PATH)
                            html.diff_column()
                            with td():
                                with a(href=f"failed/{ui_failure.test.id}.html"):
                                    i(ui_failure.test.id)

    html.write(TESTREPORT_PATH, doc, "differing_screens.html")


def _get_current_results() -> FixturesType:
    current: FixturesType = {}  # type: ignore
    for res in TestResult.recent_results():
        model = res.test.model
        group = res.test.group
        fixtures_name = res.test.fixtures_name
        actual_hash = res.actual_hash
        if model not in current:
            current[model] = {}
        if group not in current[model]:
            current[model][group] = {}
        current[model][group][fixtures_name] = actual_hash
    return current


def master_diff() -> None:
    """Creating an HTML page showing all screens differing from master."""
    current = _get_current_results()
    _removed_tests, added_tests, diff_tests = get_diff(current)
    # Enriching the diff tests with the newly added ones (empty master hash)
    for key, value in added_tests.items():
        diff_tests[key] = ("", value)
    generate_master_diff_report(diff_tests, TESTREPORT_PATH)


def master_index() -> Path:
    """Shows all the differing tests from master."""
    diff = list((TESTREPORT_PATH / "diff").iterdir())

    title = "UI changes from master"
    doc = document(title=title)

    with doc:
        h1(title)
        hr()

        h2("Differs:", style="color: grey;")
        i("UI fixtures that have been modified:")
        html.report_links(diff, TESTREPORT_PATH)

    return html.write(TESTREPORT_PATH, doc, "master_index.html")


def generate_reports(do_master_diff: bool = False) -> None:
    """Generate HTML reports for the test."""
    html.set_image_dir(IMAGES_PATH)
    index()
    all_screens()
    all_unique_screens()
    differing_screens()
    if do_master_diff:
        master_diff()
        master_index()


def _copy_deduplicated(test: TestCase) -> None:
    """Copy the actual screenshots to the deduplicated dir."""
    html.store_images(*test.actual_screens)
    html.store_images(*test.recorded_screens)


def failed(result: TestResult) -> Path:
    """Generate an HTML file for a failed test-case.

    Compares the actual screenshots to the expected ones.
    """
    download_failed = False

    if not result.test.recorded_dir.exists():
        result.test.recorded_dir.mkdir()

    if result.expected_hash:
        try:
            download.fetch_recorded(result.expected_hash, result.test.recorded_dir)
        except Exception:
            download_failed = True

    _copy_deduplicated(result.test)

    doc = document(
        title=result.test.id, actual_hash=result.actual_hash, model=result.test.model
    )
    with doc.head:
        script(
            type="text/javascript", src="https://cdn.jsdelivr.net/npm/pixelmatch@5.3.0"
        )

    with doc:

        _header(result.test.id, result.expected_hash, result.actual_hash)

        with div(id="markbox", _class="script-hidden"):
            p("Click a button to mark the test result as:")
            with div(id="buttons"):
                t.button("OK", id="mark-ok", onclick="markState('ok')")
                t.button("OK & UPDATE", id="mark-update", onclick="markState('update')")
                t.button("BAD", id="mark-bad", onclick="markState('bad')")

        if download_failed:
            with p():
                strong("WARNING:")
                text(" failed to download recorded fixtures. Is this a new test case?")

        with table(border=1, width=600):
            with tr():
                th("Expected")
                th("Actual")
                th("Diff")

            html.diff_table(result.diff_lines(), TESTREPORT_PATH / "failed")

    return html.write(TESTREPORT_PATH / "failed", doc, result.test.id + ".html")


def passed(result: TestResult) -> Path:
    """Generate an HTML file for a passed test-case."""
    return recorded(result, header="Passed")


def missing(result: TestResult) -> Path:
    """Generate an HTML file for a newly seen test-case."""
    return recorded(result, header="New testcase", dir="new")


def recorded(result: TestResult, header: str = "Recorded", dir: str = "passed") -> Path:
    """Generate an HTML file for a passed test-case.

    Shows all the screens from it in exact order.
    """
    _copy_deduplicated(result.test)

    doc = document(title=result.test.id, model=result.test.model)

    with doc:
        _header(result.test.id, result.actual_hash, result.actual_hash)

        with table(border=1):
            with tr():
                th("id")
                th(header)

            for index, screen in enumerate(result.images):
                with tr():
                    td(index)
                    html.image_column(screen, TESTREPORT_PATH / dir, img_id=str(index))

    return html.write(TESTREPORT_PATH / dir, doc, result.test.id + ".html")
