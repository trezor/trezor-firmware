import base64
import filecmp
from itertools import zip_longest
from pathlib import Path
from typing import List, Optional

from dominate import document
from dominate.tags import a, i, img, table, td, th, tr


def report_links(tests: List[Path], reports_path: Path) -> None:

    if not tests:
        i("None!")
        return
    with table(border=1):
        with tr():
            th("Link to report")
        for test in sorted(tests):
            actual_hash = ""
            path = test.relative_to(reports_path)
            if path.is_relative_to("failed"):
                with open(test, "r") as report:
                    data = report.read()
                    actual_hash = data.split("<p>Actual: ")[1].split("</p>")[0].strip()
            with tr(data_actual_hash=actual_hash):
                td(a(test.name, href=path))


def write(fixture_test_path: Path, doc: document, filename: str) -> Path:
    (fixture_test_path / filename).write_text(doc.render())
    return fixture_test_path / filename


def image_column(src: Path, image_width: Optional[int] = None) -> None:
    """Put image into table as one cell."""
    with td():
        if src:
            image_raw(src, image_width)
        else:
            i("missing")


def image_raw(src: Path, image_width: Optional[int] = None) -> None:
    """Display image on the screen"""
    # open image file
    image = src.read_bytes()
    # encode image as base64
    image = base64.b64encode(image)
    # convert output to str
    image = image.decode()
    # img(src=src.relative_to(fixture_test_path))
    img(
        src="data:image/png;base64, " + image,
        style=f"width: {image_width}px; image-rendering: pixelated;"
        if image_width
        else "",
    )


def diff_table(
    left_screens: List[Path],
    right_screens: List[Path],
    image_width: Optional[int] = None,
) -> None:
    for left, right in zip_longest(left_screens, right_screens):
        if left and right and filecmp.cmp(right, left):
            background = "white"
        else:
            background = "red"
        with tr(bgcolor=background):
            image_column(left, image_width)
            image_column(right, image_width)
