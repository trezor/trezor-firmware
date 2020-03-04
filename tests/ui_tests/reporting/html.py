import base64
import filecmp
from itertools import zip_longest

from dominate.tags import a, i, img, table, td, th, tr


def report_links(tests, reports_path):
    if not tests:
        i("None!")
        return
    with table(border=1):
        with tr():
            th("Link to report")
        for test in sorted(tests):
            with tr():
                path = test.relative_to(reports_path)
                td(a(test.name, href=path))


def write(fixture_test_path, doc, filename):
    (fixture_test_path / filename).write_text(doc.render())
    return fixture_test_path / filename


def image(src):
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


def diff_table(left_screens, right_screens):
    for left, right in zip_longest(left_screens, right_screens):
        if left and right and filecmp.cmp(right, left):
            background = "white"
        else:
            background = "red"
        with tr(bgcolor=background):
            image(left)
            image(right)
