import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path

import dominate
from dominate.tags import br, h1, h2, hr, i, p, table, td, th, tr

# These are imported directly because this script is run directly, isort gets confused by that.
import download  # isort:skip
import html  # isort:skip

REPORTS_PATH = Path(__file__).parent.resolve() / "reports" / "master_diff"
RECORDED_SCREENS_PATH = Path(__file__).parent.parent.resolve() / "screens"


def get_diff():
    master = download.fetch_fixtures_master()
    current = download.fetch_fixtures_current()

    # removed items
    removed = {test: master[test] for test in (master.keys() - current.keys())}
    # added items
    added = {test: current[test] for test in (current.keys() - master.keys())}
    # items in both branches
    same = master.items() - removed.items() - added.items()
    # create the diff
    diff = dict()
    for master_test, master_hash in same:
        if current.get(master_test) == master_hash:
            continue
        diff[master_test] = master[master_test], current[master_test]

    return removed, added, diff


def removed(screens_path, test_name):
    doc = dominate.document(title=test_name)
    screens = sorted(screens_path.iterdir())

    with doc:
        h1(test_name)
        p(
            "This UI test has been removed from fixtures.json.",
            style="color: red; font-weight: bold;",
        )
        hr()

        with table(border=1):
            with tr():
                th("Removed files")

            for screen in screens:
                with tr():
                    html.image(screen)

    return html.write(REPORTS_PATH / "removed", doc, test_name + ".html")


def added(screens_path, test_name):
    doc = dominate.document(title=test_name)
    screens = sorted(screens_path.iterdir())

    with doc:
        h1(test_name)
        p(
            "This UI test has been added to fixtures.json.",
            style="color: green; font-weight: bold;",
        )
        hr()

        with table(border=1):
            with tr():
                th("Added files")

            for screen in screens:
                with tr():
                    html.image(screen)

    return html.write(REPORTS_PATH / "added", doc, test_name + ".html")


def diff(
    master_screens_path, current_screens_path, test_name, master_hash, current_hash
):
    doc = dominate.document(title=test_name)
    master_screens = sorted(master_screens_path.iterdir())
    current_screens = sorted(current_screens_path.iterdir())

    with doc:
        h1(test_name)
        p("This UI test differs from master.", style="color: grey; font-weight: bold;")
        with table():
            with tr():
                td("Master:")
                td(master_hash, style="color: red;")
            with tr():
                td("Current:")
                td(current_hash, style="color: green;")
        hr()

        with table(border=1, width=600):
            with tr():
                th("Master")
                th("Current branch")

            html.diff_table(master_screens, current_screens)

    return html.write(REPORTS_PATH / "diff", doc, test_name + ".html")


def index():
    removed = list((REPORTS_PATH / "removed").iterdir())
    added = list((REPORTS_PATH / "added").iterdir())
    diff = list((REPORTS_PATH / "diff").iterdir())

    title = "UI changes from master"
    doc = dominate.document(title=title)

    with doc:
        h1("UI changes from master")
        hr()

        h2("Removed:", style="color: red;")
        i("UI fixtures that have been removed:")
        html.report_links(removed, REPORTS_PATH)
        br()
        hr()

        h2("Added:", style="color: green;")
        i("UI fixtures that have been added:")
        html.report_links(added, REPORTS_PATH)
        br()
        hr()

        h2("Differs:", style="color: grey;")
        i("UI fixtures that have been modified:")
        html.report_links(diff, REPORTS_PATH)

    return html.write(REPORTS_PATH, doc, "index.html")


def create_dirs():
    # delete the reports dir to clear previous entries and create folders
    shutil.rmtree(REPORTS_PATH, ignore_errors=True)
    REPORTS_PATH.mkdir()
    (REPORTS_PATH / "removed").mkdir()
    (REPORTS_PATH / "added").mkdir()
    (REPORTS_PATH / "diff").mkdir()


def create_reports():
    removed_tests, added_tests, diff_tests = get_diff()

    @contextmanager
    def tmpdir():
        with tempfile.TemporaryDirectory(prefix="trezor-records-") as temp_dir:
            yield Path(temp_dir)

    for test_name, test_hash in removed_tests.items():
        with tmpdir() as temp_dir:
            download.fetch_recorded(test_hash, temp_dir)
            removed(temp_dir, test_name)

    for test_name, test_hash in added_tests.items():
        path = RECORDED_SCREENS_PATH / test_name / "actual"
        if not path.exists():
            raise RuntimeError("Folder does not exist, has it been recorded?", path)
        added(path, test_name)

    for test_name, (master_hash, current_hash) in diff_tests.items():
        with tmpdir() as master_screens:
            download.fetch_recorded(master_hash, master_screens)

            current_screens = RECORDED_SCREENS_PATH / test_name / "actual"
            if not current_screens.exists():
                raise RuntimeError(
                    "Folder does not exist, has it been recorded?", current_screens
                )
            diff(
                master_screens,
                current_screens,
                test_name,
                master_hash,
                current_hash,
            )


if __name__ == "__main__":
    create_dirs()
    create_reports()
    index()
