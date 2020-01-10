import base64
import filecmp
import shutil
from datetime import datetime
from distutils.dir_util import copy_tree
from itertools import zip_longest
from pathlib import Path

import dominate
from dominate.tags import a, div, h1, h2, hr, i, img, p, table, td, th, tr

from . import download

REPORTS_PATH = Path(__file__).parent.resolve() / "reports"


def _image(src):
    with td():
        if src:
            # open image file
            image = src.read_bytes()
            # encode image as base64
            image = base64.b64encode(image)
            # convert output to str
            image = image.decode()
            # img(src=src.relative_to(fixture_test_path))
            img(src="data:image/png;base64, " + image)
        else:
            i("missing")


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


def _write(fixture_test_path, doc, filename):
    (fixture_test_path / filename).write_text(doc.render())
    return fixture_test_path / filename


def _report_links(tests):
    if not tests:
        i("None!")
        return
    with table(border=1):
        with tr():
            th("Link to report")
        for test in sorted(tests):
            with tr():
                path = test.relative_to(REPORTS_PATH)
                td(a(test.name, href=path))


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
    doc = dominate.document(title=title)

    with doc:
        h1("UI Test report")
        if not failed_tests:
            p("All tests succeeded!", style="color: green; font-weight: bold;")
        else:
            p("Some tests failed!", style="color: red; font-weight: bold;")
        hr()

        h2("Failed", style="color: red;")
        _report_links(failed_tests)

        h2("Passed", style="color: green;")
        _report_links(passed_tests)

    return _write(REPORTS_PATH, doc, "index.html")


def failed(fixture_test_path, test_name, actual_hash, expected_hash):
    doc = dominate.document(title=test_name)
    recorded_path = fixture_test_path / "recorded"
    actual_path = fixture_test_path / "actual"

    if not recorded_path.exists():
        recorded_path.mkdir()
    download.fetch_recorded(expected_hash, recorded_path)

    recorded_screens = sorted(recorded_path.iterdir())
    actual_screens = sorted(actual_path.iterdir())

    if not recorded_screens:
        return

    with doc:
        _header(test_name, expected_hash, actual_hash)

        with table(border=1, width=600):
            with tr():
                th("Expected")
                th("Actual")

            for recorded, actual in zip_longest(recorded_screens, actual_screens):
                if recorded and actual and filecmp.cmp(actual, recorded):
                    background = "white"
                else:
                    background = "red"
                with tr(bgcolor=background):
                    _image(recorded)
                    _image(actual)

    return _write(REPORTS_PATH / "failed", doc, test_name + ".html")


def passed(fixture_test_path, test_name, actual_hash):
    copy_tree(str(fixture_test_path / "actual"), str(fixture_test_path / "recorded"))

    doc = dominate.document(title=test_name)
    actual_path = fixture_test_path / "actual"
    actual_screens = sorted(actual_path.iterdir())

    with doc:
        _header(test_name, actual_hash, actual_hash)

        with table(border=1):
            with tr():
                th("Recorded")

            for screen in actual_screens:
                with tr():
                    _image(screen)

    return _write(REPORTS_PATH / "passed", doc, test_name + ".html")
