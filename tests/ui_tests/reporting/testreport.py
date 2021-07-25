import shutil
from datetime import datetime
from distutils.dir_util import copy_tree
from pathlib import Path

import dominate
import dominate.tags as t
from dominate.tags import div, h1, h2, hr, p, strong, table, th, tr
from dominate.util import text

from . import download, html

HERE = Path(__file__).parent.resolve()
REPORTS_PATH = HERE / "reports" / "test"

STYLE = (HERE / "testreport.css").read_text()
SCRIPT = (HERE / "testreport.js").read_text()

ACTUAL_HASHES = {}


def document(title, actual_hash=None, index=False):
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


def _header(test_name, expected_hash, actual_hash):
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


def clear_dir():
    # delete and create the reports dir to clear previous entries
    shutil.rmtree(REPORTS_PATH, ignore_errors=True)
    REPORTS_PATH.mkdir()
    (REPORTS_PATH / "failed").mkdir()
    (REPORTS_PATH / "passed").mkdir()


def index():
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


def failed(fixture_test_path, test_name, actual_hash, expected_hash):
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
                t.button("BAD", id="mark-bad", onclick="markState('bad')")

        if download_failed:
            with p():
                strong("WARNING:")
                text(" failed to download recorded fixtures. Is this a new test case?")

        with table(border=1, width=600):
            with tr():
                th("Expected")
                th("Actual")

            html.diff_table(recorded_screens, actual_screens)

    return html.write(REPORTS_PATH / "failed", doc, test_name + ".html")


def passed(fixture_test_path, test_name, actual_hash):
    copy_tree(str(fixture_test_path / "actual"), str(fixture_test_path / "recorded"))

    doc = document(title=test_name)
    actual_path = fixture_test_path / "actual"
    actual_screens = sorted(actual_path.iterdir())

    with doc:
        _header(test_name, actual_hash, actual_hash)

        with table(border=1):
            with tr():
                th("Recorded")

            for screen in actual_screens:
                with tr():
                    html.image(screen)

    return html.write(REPORTS_PATH / "passed", doc, test_name + ".html")
