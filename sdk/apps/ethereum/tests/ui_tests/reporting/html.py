from __future__ import annotations

import shutil
import urllib.parse
from pathlib import Path
from typing import Iterable

from dominate import document
from dominate.tags import a, i, img, span, table, td, th, tr

from ..common import UI_TESTS_DIR

_COLLAPSE_UNCHANGED_THRESHOLD = 10
_IMAGE_DIR = UI_TESTS_DIR / "images"


def set_image_dir(path: Path) -> None:
    global _IMAGE_DIR
    _IMAGE_DIR = path


def store_images(screens: Iterable[Path], hashes: Iterable[str]) -> None:
    for screen, hash in zip(screens, hashes):
        shutil.copy(screen, _IMAGE_DIR / f"{hash}.png")


def report_links(
    tests: list[Path], reports_path: Path, actual_hashes: dict[str, str] | None = None
) -> None:
    if actual_hashes is None:
        actual_hashes = {}

    if not tests:
        i("None!")
        return
    with table(border=1):
        with tr():
            th("Link to report")
        for test in sorted(tests):
            with tr(data_actual_hash=actual_hashes.get(test.stem, "")):
                urlsafe = urllib.parse.quote(test.name)
                path = test.with_name(urlsafe).relative_to(reports_path)
                td(a(test.name, href=path))


def write_raw(fixture_test_path: Path, doc: str, filename: str) -> Path:
    (fixture_test_path / filename).write_text(doc)
    return fixture_test_path / filename


def write(fixture_test_path: Path, doc: document, filename: str) -> Path:
    return write_raw(fixture_test_path, doc.render(), filename)


def image_column(hash: str | None, cur_dir: Path, img_id: str | None = None) -> None:
    """Put image into table as one cell."""
    with td():
        if hash:
            image_link(hash, cur_dir, img_id=img_id)
        else:
            i("missing")


def diff_column() -> None:
    """Put diff image into table as one cell."""
    with td(bgcolor="white"):
        a("N/A")


def _relative_path(cur_dir: Path, path_to: Path) -> str:
    """Find best relative path to refer to path_to from cur_dir."""
    cur_dir = cur_dir.resolve()
    path_to = path_to.resolve()
    if not cur_dir.is_dir():
        cur_dir = cur_dir.parent

    common = cur_dir
    while common not in path_to.parents:
        common = common.parent
    ascent = len(cur_dir.parts) - len(common.parts)
    relpath = path_to.relative_to(common)
    components = [".."] * ascent + list(relpath.parts)
    return "/".join(components)


def image_link(
    hash: str, cur_dir: Path, title: str = "", img_id: str | None = None
) -> None:
    """Put image into table as one cell."""
    path = _IMAGE_DIR / f"{hash}.png"
    img(
        id=img_id,
        src=_relative_path(cur_dir, path),
        title=title,
        loading="lazy",
        _class="image-link",
    )


def diff_row(
    left: str | None,
    right: str | None,
    cur_dir: Path,
    bgcolor: str,
    hidden: bool = False,
):
    with tr(bgcolor=bgcolor, _class="hidden" if hidden else ""):
        image_column(left, cur_dir)
        image_column(right, cur_dir)
        diff_column()


def collapsible_rows(rows, cur_dir):
    collapse = len(rows) > 0
    for left, right in rows:
        diff_row(left, right, cur_dir, "white", collapse)
    if collapse:
        with tr(bgcolor="yellow"):
            with td(colspan=3, _class="showLink"):
                span(f"{len(rows)} hidden")
                a("show all", _class="show-all-hidden", href="#")


def diff_table(diff: Iterable[tuple[str | None, str | None]], cur_dir: Path) -> None:
    rows = list(diff)
    has_diff = any(l != r for l, r in rows)

    if (
        not has_diff or len(rows) <= _COLLAPSE_UNCHANGED_THRESHOLD
    ):  # show all without collapsing
        for left, right in rows:
            color = "red" if left != right else "white"
            diff_row(left, right, cur_dir, color)
    else:
        unchanged_buffer = []
        for left, right in rows:
            is_diff = left != right
            if not is_diff:
                unchanged_buffer.append((left, right))
            else:
                collapsible_rows(unchanged_buffer, cur_dir)
                unchanged_buffer.clear()
                diff_row(left, right, cur_dir, "red")
        collapsible_rows(unchanged_buffer, cur_dir)
