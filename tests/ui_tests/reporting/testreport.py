import filecmp
import hashlib
import shutil
from collections import defaultdict
from datetime import datetime
from distutils.dir_util import copy_tree
from pathlib import Path
from typing import Dict, List, Set

import dominate
import dominate.tags as t
from dominate.tags import a, div, h1, h2, hr, i, p, span, strong, table, td, th, tr
from dominate.util import text

from . import download, html

HERE = Path(__file__).resolve().parent
REPORTS_PATH = HERE / "reports" / "test"
RECORDED_SCREENS_PATH = Path(__file__).resolve().parent.parent / "screens"
SCREEN_TEXT_FILE = REPORTS_PATH / "screen_text.txt"

STYLE = (HERE / "testreport.css").read_text()
SCRIPT = (HERE / "testreport.js").read_text()
SCREENSHOTS_WIDTH_PX_TO_DISPLAY = {
    "T1": 128 * 2,  # original is 128px
    "TT": 240,  # original is 240px
    "TR": 128 * 2,  # original is 128px
}

# These two html files are referencing each other
ALL_SCREENS = "all_screens.html"
ALL_UNIQUE_SCREENS = "all_unique_screens.html"

ACTUAL_HASHES: Dict[str, str] = {}


def _image_width(test_name: str) -> int:
    """Return the width of the image to display for the given test name.

    Is model-specific. Model is at the beginning of each test-case.
    """
    return SCREENSHOTS_WIDTH_PX_TO_DISPLAY[test_name[:2]]


def document(
    title: str, actual_hash: str = None, index: bool = False
) -> dominate.document:
    doc = dominate.document(title=title)
    style = t.style()
    style.add_raw_string(STYLE)
    script = t.script()
    script.add_raw_string(SCRIPT)
    doc.head.add(style, script)

    if actual_hash is not None:
        doc.body["data-actual-hash"] = actual_hash

    if index:
        doc.body["data-index"] = True

    return doc


def _header(test_name: str, expected_hash: str, actual_hash: str) -> None:
    h1(test_name)
    with div():
        if actual_hash == expected_hash:
            p(
                "This test succeeded on UI comparison.",
                style="color: green; font-weight: bold;",
            )
        else:
            p(
                "This test failed on UI comparison.",
                style="color: red; font-weight: bold;",
            )
        p("Expected: ", expected_hash)
        p("Actual: ", actual_hash)
    hr()


def clear_dir() -> None:
    """Delete and create the reports dir to clear previous entries."""
    shutil.rmtree(REPORTS_PATH, ignore_errors=True)
    REPORTS_PATH.mkdir()
    (REPORTS_PATH / "failed").mkdir()
    (REPORTS_PATH / "passed").mkdir()


def index() -> Path:
    """Generate index.html with all the test results - lists of failed and passed tests."""
    passed_tests = list((REPORTS_PATH / "passed").iterdir())
    failed_tests = list((REPORTS_PATH / "failed").iterdir())

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

        html.report_links(failed_tests, REPORTS_PATH, ACTUAL_HASHES)

        h2("Passed", style="color: green;")
        html.report_links(passed_tests, REPORTS_PATH)

    return html.write(REPORTS_PATH, doc, "index.html")


def all_screens(test_case_dirs: List[Path]) -> Path:
    """Generate an HTML file for all the screens from the current test run.

    Shows all test-cases at one place.
    """
    title = "All test cases"
    doc = dominate.document(title=title)

    with doc:
        h1("All test cases")
        hr()

        count = 0
        for test_case_dir in test_case_dirs:
            test_case_name = test_case_dir.name
            h2(test_case_name, id=test_case_name)
            actual_dir = test_case_dir / "actual"
            for png in sorted(actual_dir.rglob("*.png")):
                # Including link to each image to see where else it occurs.
                png_hash = _img_hash(png)
                with a(href=f"{ALL_UNIQUE_SCREENS}#{png_hash}"):
                    html.image_raw(png, _image_width(test_case_name))
                count += 1

        h2(f"{count} screens from {len(test_case_dirs)} testcases.")

    return html.write(REPORTS_PATH, doc, ALL_SCREENS)


def all_unique_screens(test_case_dirs: List[Path]) -> Path:
    """Generate an HTML file with all the unique screens from the current test run."""
    title = "All unique screens"
    doc = dominate.document(title=title)

    with doc:
        h1("All unique screens")
        hr()

        screen_hashes: Dict[str, List[Path]] = defaultdict(list)
        hash_images: Dict[str, Path] = {}

        # Adding all unique images onto the page
        for test_case_dir in test_case_dirs:
            actual_dir = test_case_dir / "actual"
            for png in sorted(actual_dir.rglob("*.png")):
                png_hash = _img_hash(png)
                if png_hash not in screen_hashes:
                    # Adding link to the appropriate hash, where other testcases
                    # with the same hash (screen) are listed.
                    with a(href=f"#{png_hash}"):
                        with span(id=png_hash[:8]):
                            html.image_raw(png, _image_width(test_case_dir.name))

                screen_hashes[png_hash].append(test_case_dir)
                hash_images[png_hash] = png

        # Adding all screen hashes together with links to testcases having these screens.
        for png_hash, test_cases in screen_hashes.items():
            h2(png_hash)
            with div(id=png_hash):
                # Showing the exact image as well (not magnifying it)
                with a(href=f"#{png_hash[:8]}"):
                    html.image_raw(hash_images[png_hash])
                for case in test_cases:
                    # Adding link to each test-case
                    with a(href=f"{ALL_SCREENS}#{case.name}"):
                        p(case.name.split("/")[-1])

        h2(f"{len(screen_hashes)} unique screens from {len(test_case_dirs)} testcases.")

    return html.write(REPORTS_PATH, doc, ALL_UNIQUE_SCREENS)


def screen_text_report(test_case_dirs: List[Path]) -> None:
    with open(SCREEN_TEXT_FILE, "w") as f2:
        for test_case_dir in test_case_dirs:
            screen_file = test_case_dir / "screens.txt"
            if not screen_file.exists():
                continue
            f2.write(f"\n{test_case_dir.name}\n")
            with open(screen_file, "r") as f:
                for line in f.readlines():
                    f2.write(f"\t{line}")


def differing_screens(test_case_dirs: List[Path]) -> None:
    """Creating an HTML page showing all the unique screens that got changed."""
    unique_diffs: set[tuple[str, str]] = set()

    def combine_hashes(left: Path, right: Path) -> tuple[str, str]:
        return (_img_hash(left), _img_hash(right))

    def already_included(left: Path, right: Path) -> bool:
        return combine_hashes(left, right) in unique_diffs

    def include(left: Path, right: Path) -> None:
        unique_diffs.add(combine_hashes(left, right))

    doc = dominate.document(title="Differing screens")
    with doc:
        with table(border=1, width=600):
            with tr():
                th("Expected")
                th("Actual")
                th("Testcase (link)")
            for test_case_dir in test_case_dirs:
                recorded_path = test_case_dir / "recorded"
                actual_path = test_case_dir / "actual"

                recorded_screens = sorted(recorded_path.iterdir())
                actual_screens = sorted(actual_path.iterdir())

                # Not comparing when the amount of screens differ
                if len(recorded_screens) != len(actual_screens):
                    with tr(bgcolor="red"):
                        with td():
                            i("Number of screens")
                        with td():
                            i("differs")
                        with td():
                            with a(href=f"failed/{test_case_dir.name}.html"):
                                i(test_case_dir.name)
                    continue

                image_width = _image_width(test_case_dir.name)

                for left, right in zip(recorded_screens, actual_screens):
                    if not filecmp.cmp(right, left) and not already_included(
                        left, right
                    ):
                        include(left, right)
                        with tr(bgcolor="red"):
                            html.image_column(left, image_width)
                            html.image_column(right, image_width)
                            with td():
                                with a(href=f"failed/{test_case_dir.name}.html"):
                                    i(test_case_dir.name)

    html.write(REPORTS_PATH, doc, "differing_screens.html")


def generate_reports(do_screen_text: bool = False) -> None:
    """Generate HTML reports for the test."""
    index()

    # To only get screens from the last running test-cases,
    # we need to get the list of all directories with screenshots.
    current_testcases = _get_testcases_dirs()
    all_screens(current_testcases)
    all_unique_screens(current_testcases)
    if do_screen_text:
        screen_text_report(current_testcases)
    differing_screens(current_testcases)


def _img_hash(img: Path) -> str:
    """Return the hash of the image."""
    content = img.read_bytes()
    return hashlib.md5(content).hexdigest()


def _get_testcases_dirs() -> List[Path]:
    """Get the list of test-cases dirs that the current test was running."""
    current_testcases = _get_all_current_testcases()
    all_test_cases_dirs = [
        case
        for case in (RECORDED_SCREENS_PATH).iterdir()
        if case.name in current_testcases
    ]
    return sorted(all_test_cases_dirs)


def _get_all_current_testcases() -> Set[str]:
    """Get names of all current test-cases.

    Equals to the names of HTML files in the reports dir.
    """
    passed_tests = list((REPORTS_PATH / "passed").glob("*.html"))
    failed_tests = list((REPORTS_PATH / "failed").glob("*.html"))
    return {test.stem for test in (passed_tests + failed_tests)}


def failed(
    fixture_test_path: Path, test_name: str, actual_hash: str, expected_hash: str
) -> Path:
    """Generate an HTML file for a failed test-case.

    Compares the actual screenshots to the expected ones.
    """
    ACTUAL_HASHES[test_name] = actual_hash

    doc = document(title=test_name, actual_hash=actual_hash)
    recorded_path = fixture_test_path / "recorded"
    actual_path = fixture_test_path / "actual"

    download_failed = False

    if not recorded_path.exists():
        recorded_path.mkdir()
    try:
        download.fetch_recorded(expected_hash, recorded_path)
    except Exception:
        download_failed = True

    recorded_screens = sorted(recorded_path.iterdir())
    actual_screens = sorted(actual_path.iterdir())

    with doc:
        _header(test_name, expected_hash, actual_hash)

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

            html.diff_table(
                recorded_screens,
                actual_screens,
                _image_width(test_name),
            )

    return html.write(REPORTS_PATH / "failed", doc, test_name + ".html")


def passed(fixture_test_path: Path, test_name: str, actual_hash: str) -> Path:
    """Generate an HTML file for a passed test-case."""
    copy_tree(str(fixture_test_path / "actual"), str(fixture_test_path / "recorded"))

    return recorded(fixture_test_path / "actual", test_name, actual_hash)


def recorded(fixture_test_path: Path, test_name: str, actual_hash: str) -> Path:
    """Generate an HTML file for a passed test-case.

    Shows all the screens from it in exact order.
    """
    doc = document(title=test_name)
    actual_screens = sorted(fixture_test_path.iterdir())

    with doc:
        _header(test_name, actual_hash, actual_hash)

        with table(border=1):
            with tr():
                th("Recorded")

            for screen in actual_screens:
                with tr():
                    html.image_column(screen, _image_width(test_name))

    return html.write(REPORTS_PATH / "passed", doc, test_name + ".html")
