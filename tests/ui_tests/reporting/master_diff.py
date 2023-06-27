from __future__ import annotations

import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path

from dominate.tags import br, h1, h2, hr, i, p, table, th, tr

from ..common import get_current_fixtures, get_screen_path, screens_and_hashes
from . import download, html
from .common import REPORTS_PATH, document, generate_master_diff_report, get_diff

MASTERDIFF_PATH = REPORTS_PATH / "master_diff"
IMAGES_PATH = MASTERDIFF_PATH / "images"


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


def index() -> Path:
    removed = list((MASTERDIFF_PATH / "removed").iterdir())
    added = list((MASTERDIFF_PATH / "added").iterdir())
    diff = list((MASTERDIFF_PATH / "diff").iterdir())

    title = "UI changes from master"
    doc = document(title=title)

    with doc:
        h1(title)
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


def create_reports() -> None:
    current = get_current_fixtures()
    removed_tests, added_tests, diff_tests = get_diff(current, print_to_console=True)

    @contextmanager
    def tmpdir():
        with tempfile.TemporaryDirectory(prefix="trezor-records-") as temp_dir:
            yield Path(temp_dir)

    for test_name, test_hash in removed_tests.items():
        with tmpdir() as temp_dir:
            try:
                download.fetch_recorded(test_hash, temp_dir)
            except RuntimeError:
                print("Could not download recorded files for", test_name)
                continue
            removed(temp_dir, test_name)

    for test_name, test_hash in added_tests.items():
        screen_path = get_screen_path(test_name)
        if not screen_path:
            continue
        added(screen_path, test_name)

    generate_master_diff_report(diff_tests, MASTERDIFF_PATH)


def main() -> None:
    create_dirs()
    html.set_image_dir(IMAGES_PATH)
    create_reports()
    index()
