from pathlib import Path
from typing import Any

import dominate
import dominate.tags as t
from dominate.tags import a, h1, hr, i, p, script, table, td, th, tr

from ..common import (
    UI_TESTS_DIR,
    FixturesType,
    TestCase,
    get_screen_path,
    screens_and_hashes,
    screens_diff,
)
from . import download, html

HERE = Path(__file__).resolve().parent

STYLE = (HERE / "testreport.css").read_text()
SCRIPT = (HERE / "testreport.js").read_text()
GIF_SCRIPT = (HERE / "create-gif.js").read_text()

REPORTS_PATH = UI_TESTS_DIR / "reports"

# Saving the master screens on disk not to fetch them all the time
MASTER_CACHE_DIR = HERE / "master_cache"
if not MASTER_CACHE_DIR.exists():
    MASTER_CACHE_DIR.mkdir()

LEGACY_MODEL_NAMES = {
    "T1": "T1B1",
    "TT": "T2T1",
    "TR": "T3B1",
    "T2B1": "T3B1",
}


def generate_master_diff_report(
    diff_tests: dict[TestCase, tuple[str, str]], base_dir: Path
) -> None:
    unique_differing_screens = _get_unique_differing_screens(diff_tests, base_dir)
    _differing_screens_report(unique_differing_screens, base_dir)


def get_diff(
    current: FixturesType,
    print_to_console: bool = False,
    models: list[str] | None = None,
) -> tuple[dict[TestCase, str], dict[TestCase, str], dict[TestCase, tuple[str, str]]]:
    master = _preprocess_master_compat(download.fetch_fixtures_master())

    removed = {}
    added = {}
    diff = {}

    for model in master.keys() | current.keys():
        if models and model not in models:
            continue

        master_groups = master.get(model, {})
        current_groups = current.get(model, {})
        for group in master_groups.keys() | current_groups.keys():
            master_tests = master_groups.get(group, {})
            current_tests = current_groups.get(group, {})

            def testkey(test: str) -> TestCase:
                return TestCase.from_fixtures(test, group)

            # removed items
            removed_here = {
                testkey(test): master_tests[test]
                for test in (master_tests.keys() - current_tests.keys())
            }
            # added items
            added_here = {
                testkey(test): current_tests[test]
                for test in (current_tests.keys() - master_tests.keys())
            }
            # create the diff from items in both branches
            diff_here = {}
            for master_test, master_hash in master_tests.items():
                key = testkey(master_test)
                if key in removed_here:
                    continue
                if current_tests.get(master_test) == master_hash:
                    continue
                diff_here[key] = (
                    master_tests[master_test],
                    current_tests[master_test],
                )

            removed.update(removed_here)
            added.update(added_here)
            diff.update(diff_here)
            if print_to_console:
                print(f"{model} {group}")
                print(f"  removed: {len(removed_here)}")
                print(f"  added: {len(added_here)}")
                print(f"  diff: {len(diff_here)}")

    return removed, added, diff


def document(
    title: str,
    actual_hash: str | None = None,
    index: bool = False,
    model: str | None = None,
) -> dominate.document:
    doc = dominate.document(title=title)
    style = t.style()
    style.add_raw_string(STYLE)
    script = t.script()
    script.add_raw_string(GIF_SCRIPT)
    script.add_raw_string(SCRIPT)
    doc.head.add(style, script)

    if actual_hash is not None:
        doc.body["data-actual-hash"] = actual_hash

    if index:
        doc.body["data-index"] = True

    if model:
        doc.body["class"] = f"model-{model}"

    return doc


def _preprocess_master_compat(master_fixtures: dict[str, Any]) -> FixturesType:
    new_fixtures = {}
    for model, groups_by_model in master_fixtures.items():
        if model not in LEGACY_MODEL_NAMES:
            new_fixtures[model] = groups_by_model
            continue

        # (a) replace model group name
        model = LEGACY_MODEL_NAMES.get(model)
        new_groups_by_model = new_fixtures.setdefault(model, {})
        for group, tests_by_group in groups_by_model.items():
            new_tests_by_group = new_groups_by_model.setdefault(group, {})
            for key, val in tests_by_group.items():
                case = TestCase.from_fixtures(key, group)
                # (b) in individual testcases, replace model name prefix
                new_case = case.replace(model=model)
                new_tests_by_group[new_case.fixtures_name] = val

    return FixturesType(new_fixtures)


def _create_testcase_html_diff_file(
    zipped_screens: list[tuple[str | None, str | None]],
    test_case: TestCase,
    master_hash: str,
    current_hash: str,
    base_dir: Path,
) -> Path:
    test_name = test_case.id
    doc = document(title=test_name, model=test_case.model)
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

            html.diff_table(zipped_screens, base_dir / "diff")

    return html.write(base_dir / "diff", doc, test_name + ".html")


def _differing_screens_report(
    unique_differing_screens: dict[tuple[str | None, str | None], TestCase],
    base_dir: Path,
) -> None:
    try:
        model = next(iter(unique_differing_screens.values())).model
    except StopIteration:
        model = ""

    doc = document(title="Master differing screens", model=model)
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

            for (master, current), testcase in unique_differing_screens.items():
                with tr(bgcolor="red"):
                    html.image_column(master, base_dir)
                    html.image_column(current, base_dir)
                    html.diff_column()
                    with td():
                        with a(href=f"diff/{testcase.id}.html"):
                            i(testcase.id)

    html.write(base_dir, doc, "master_diff.html")


def _get_unique_differing_screens(
    diff_tests: dict[TestCase, tuple[str, str]], base_dir: Path
) -> dict[tuple[str | None, str | None], TestCase]:

    # Holding unique screen differences, connected with a certain testcase
    # Used for diff report
    unique_differing_screens: dict[tuple[str | None, str | None], TestCase] = {}

    for test_case, (master_hash, current_hash) in diff_tests.items():
        # Downloading master recordings only if we do not have them already
        master_screens_path = MASTER_CACHE_DIR / master_hash
        if not master_screens_path.exists():
            master_screens_path.mkdir()
            # master_hash may be empty, in case of new test
            if master_hash:
                try:
                    download.fetch_recorded(master_hash, master_screens_path)
                except RuntimeError as e:
                    print("WARNING:", e)

        current_screens_path = get_screen_path(test_case)
        if not current_screens_path:
            current_screens_path = MASTER_CACHE_DIR / "empty_current_screens"
            current_screens_path.mkdir(exist_ok=True)

        # Saving all the images to a common directory
        # They will be referenced from the HTML files
        if master_hash:
            master_screens, master_hashes = screens_and_hashes(master_screens_path)
        else:
            master_screens, master_hashes = [], []
        current_screens, current_hashes = screens_and_hashes(current_screens_path)
        html.store_images(master_screens, master_hashes)
        html.store_images(current_screens, current_hashes)

        # List of tuples of master and current screens
        # Useful for both testcase HTML report and the differing screen report
        zipped_screens = list(screens_diff(master_hashes, current_hashes))

        # Create testcase HTML report
        _create_testcase_html_diff_file(
            zipped_screens, test_case, master_hash, current_hash, base_dir
        )

        # Save differing screens for differing screens report
        for master, current in zipped_screens:
            if master != current:
                unique_differing_screens[(master, current)] = test_case

    return unique_differing_screens
