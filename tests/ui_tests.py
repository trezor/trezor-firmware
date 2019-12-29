import filecmp
from itertools import zip_longest

import dominate
from dominate.tags import div, h1, hr, i, img, p, table, td, th, tr


def create_diff_html(fixture_test_path, test_name, actual_hash, expected_hash):
    doc = dominate.document(title=test_name)
    recorded_path = fixture_test_path / "recorded"
    actual_path = fixture_test_path / "actual"

    if not recorded_path.exists():
        return

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
                    _image(r, fixture_test_path)
                    _image(a, fixture_test_path)

    with open(fixture_test_path / "diff.html", "w") as f:
        f.write(doc.render())
        f.close()


def _image(src, fixture_test_path):
    with td():
        if src:
            img(src=src.relative_to(fixture_test_path))
        else:
            i("missing")
