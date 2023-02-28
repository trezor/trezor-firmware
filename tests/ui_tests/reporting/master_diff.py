from __future__ import annotations

import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from dominate.tags import br, h1, h2, hr, i, p, table, td, th, tr

from ..common import (
    SCREENS_DIR,
    FixturesType,
    get_fixtures,
    screens_and_hashes,
    screens_diff,
)
from . import download, html
from .testreport import REPORTS_PATH, document

MASTERDIFF_PATH = REPORTS_PATH / "master_diff"
IMAGES_PATH = MASTERDIFF_PATH / "images"


def _preprocess_master_compat(master_fixtures: dict[str, Any]) -> FixturesType:
    if all(isinstance(v, str) for v in master_fixtures.values()):
        # old format, convert to new format
        new_fixtures = {}
        for key, val in master_fixtures.items():
            model, _test = key.split("_", maxsplit=1)
            groups_by_model = new_fixtures.setdefault(model, {})
            default_group = groups_by_model.setdefault("device_tests", {})
            default_group[key] = val
        return FixturesType(new_fixtures)
    else:
        return FixturesType(master_fixtures)


def get_diff() -> tuple[dict[str, str], dict[str, str], dict[str, tuple[str, str]]]:
    master = _preprocess_master_compat(download.fetch_fixtures_master())
    current = get_fixtures()

    removed = {}
    added = {}
    diff = {}

    for model in master.keys() | current.keys():
        master_groups = master.get(model, {})
        current_groups = current.get(model, {})
        for group in master_groups.keys() | current_groups.keys():
            master_tests = master_groups.get(group, {})
            current_tests = current_groups.get(group, {})

            def testname(test: str) -> str:
                assert test.startswith(model + "_")
                test = test[len(model) + 1 :]
                return f"{model}-{group}-{test}"

            # removed items
            removed_here = {
                testname(test): master_tests[test]
                for test in (master_tests.keys() - current_tests.keys())
            }
            # added items
            added_here = {
                testname(test): current_tests[test]
                for test in (current_tests.keys() - master_tests.keys())
            }
            # create the diff from items in both branches
            diff_here = {}
            for master_test, master_hash in master_tests.items():
                full_test_name = testname(master_test)
                if full_test_name in removed_here:
                    continue
                if current_tests.get(master_test) == master_hash:
                    continue
                diff_here[full_test_name] = (
                    master_tests[master_test],
                    current_tests[master_test],
                )

            removed.update(removed_here)
            added.update(added_here)
            diff.update(diff_here)
            print(f"{model} {group}")
            print(f"  removed: {len(removed_here)}")
            print(f"  added: {len(added_here)}")
            print(f"  diff: {len(diff_here)}")

    return removed, added, diff


def removed(screens_path: Path, test_name: str) -> Path:
    doc = document(title=test_name, model=test_name[:2])
    screens, hashes = screens_and_hashes(screens_path)
    html.store_images(screens, hashes)

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

            for hash in hashes:
                with tr():
                    html.image_column(hash, MASTERDIFF_PATH / "removed")

    return html.write(MASTERDIFF_PATH / "removed", doc, test_name + ".html")


def added(screens_path: Path, test_name: str) -> Path:
    doc = document(title=test_name, model=test_name[:2])
    screens, hashes = screens_and_hashes(screens_path)
    html.store_images(screens, hashes)

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

            for hash in hashes:
                with tr():
                    html.image_column(hash, MASTERDIFF_PATH / "added")

    return html.write(MASTERDIFF_PATH / "added", doc, test_name + ".html")


def diff(
    master_screens_path: Path,
    current_screens_path: Path,
    test_name: str,
    master_hash: str,
    current_hash: str,
) -> Path:
    doc = document(title=test_name, model=test_name[:2])
    master_screens, master_hashes = screens_and_hashes(master_screens_path)
    current_screens, current_hashes = screens_and_hashes(current_screens_path)
    html.store_images(master_screens, master_hashes)
    html.store_images(current_screens, current_hashes)

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

            html.diff_table(
                screens_diff(master_hashes, current_hashes), MASTERDIFF_PATH / "diff"
            )

    return html.write(MASTERDIFF_PATH / "diff", doc, test_name + ".html")


def index() -> Path:
    removed = list((MASTERDIFF_PATH / "removed").iterdir())
    added = list((MASTERDIFF_PATH / "added").iterdir())
    diff = list((MASTERDIFF_PATH / "diff").iterdir())

    title = "UI changes from master"
    doc = document(title=title)

    with doc:
        h1("UI changes from master")
        hr()

        h2("Removed:", style="color: red;")
        i("UI fixtures that have been removed:")
        html.report_links(removed, MASTERDIFF_PATH)
        br()
        hr()

        h2("Added:", style="color: green;")
        i("UI fixtures that have been added:")
        html.report_links(added, MASTERDIFF_PATH)
        br()
        hr()

        h2("Differs:", style="color: grey;")
        i("UI fixtures that have been modified:")
        html.report_links(diff, MASTERDIFF_PATH)

    return html.write(MASTERDIFF_PATH, doc, "index.html")


def create_dirs() -> None:
    # delete the reports dir to clear previous entries and create folders
    shutil.rmtree(MASTERDIFF_PATH, ignore_errors=True)
    MASTERDIFF_PATH.mkdir(parents=True)
    (MASTERDIFF_PATH / "removed").mkdir()
    (MASTERDIFF_PATH / "added").mkdir()
    (MASTERDIFF_PATH / "diff").mkdir()
    IMAGES_PATH.mkdir(exist_ok=True)


def _get_screen_path(test_name: str) -> Path | None:
    path = SCREENS_DIR / test_name / "actual"
    if path.exists():
        return path
    path = SCREENS_DIR / test_name / "recorded"
    if path.exists():
        print(
            f"WARNING: no actual screens for {test_name}, recording may be outdated: {path}"
        )
        return path
    print(f"WARNING: missing screens for {test_name}. Did the test run?")
    return None


def create_reports() -> None:
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
        screen_path = _get_screen_path(test_name)
        if not screen_path:
            continue
        added(screen_path, test_name)

    for test_name, (master_hash, current_hash) in diff_tests.items():
        with tmpdir() as master_root:
            master_screens = master_root / "downloaded"
            master_screens.mkdir()
            try:
                download.fetch_recorded(master_hash, master_screens)
            except RuntimeError as e:
                print("WARNING:", e)

            current_screens = _get_screen_path(test_name)
            if not current_screens:
                current_screens = master_root / "empty_current_screens"
                current_screens.mkdir()

            diff(
                master_screens,
                current_screens,
                test_name,
                master_hash,
                current_hash,
            )


def main() -> None:
    create_dirs()
    html.set_image_dir(IMAGES_PATH)
    create_reports()
    index()
