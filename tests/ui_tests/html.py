import base64
import filecmp
from itertools import zip_longest

import dominate
from dominate.tags import div, h1, hr, i, img, p, table, td, th, tr

from . import download


def _image(src):
    with td():
        if src:
            # open image file
            image = open(src, "rb")
            # encode image as base64
            image = base64.b64encode(image.read())
            # convert output to str
            image = image.decode()
            # img(src=src.relative_to(fixture_test_path))
            img(src="data:image/png;base64, " + image)
        else:
            i("missing")


def diff_file(fixture_test_path, test_name, actual_hash, expected_hash):
    doc = dominate.document(title=test_name)
    recorded_path = fixture_test_path / "recorded"
    actual_path = fixture_test_path / "actual"

    if not recorded_path.exists():
        recorded_path.mkdir()

    download.fetch_recorded(expected_hash, recorded_path)

    recorded = sorted(recorded_path.iterdir())
    actual = sorted(actual_path.iterdir())

    if not recorded:
        return

    with doc:
        h1(test_name)
        with div():
            p("This test failed on UI comparison.")
            p("Expected: ", expected_hash)
            p("Actual: ", actual_hash)
        hr()

        with table(border=1, width=600):
            with tr():
                th("Expected")
                th("Actual")

            for r, a in zip_longest(recorded, actual):
                if r and a and filecmp.cmp(a, r):
                    background = "white"
                else:
                    background = "red"
                with tr(bgcolor=background):
                    _image(r)
                    _image(a)

    (fixture_test_path / "diff.html").write_text(doc.render())
    return fixture_test_path / "diff.html"
