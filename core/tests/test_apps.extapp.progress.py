# flake8: noqa: F403,F405
from common import *  # isort:skip

if utils.USE_APP_LOADING:
    from trezor import ui

    from apps.extapp import progress as progress_module


class FakeLayout:
    """A progress layout that records its reports; a report puts it on the
    screen, as the real one does."""

    def __init__(self, indeterminate: bool) -> None:
        self.indeterminate = indeterminate
        self.reports = []

    def report(self, value: int, description: str | None = None) -> None:
        ui.CURRENT_LAYOUT = self
        self.reports.append((value, description))


class FakeSession:
    def __init__(self) -> None:
        self.progress = None
        self.progress_state = None


@unittest.skipUnless(utils.USE_APP_LOADING, "built without app loading")
class TestShow(unittest.TestCase):
    def setUp(self):
        self.built = []
        self.saved = (progress_module.progress, ui.CURRENT_LAYOUT)

        def build(description: str, indeterminate: bool) -> FakeLayout:
            layout = FakeLayout(indeterminate)
            self.built.append(layout)
            return layout

        progress_module.progress = build
        self.session = FakeSession()

    def tearDown(self):
        progress_module.progress, ui.CURRENT_LAYOUT = self.saved

    def show(self, label: str, done: int, total: int) -> None:
        progress_module.show(self.session, label, done, total)

    def test_a_bar_moves_forward_and_is_drawn_anew_otherwise(self):
        self.show("Signing", 1, 4)
        self.show("Signing", 2, 4)
        self.assertEqual(len(self.built), 1)  # moved forward: the same bar
        self.assertEqual(self.built[0].reports, [(250, "Signing"), (500, "Signing")])

        for label, done, total in (
            ("Finalizing", 2, 4),  # the label changed
            ("Finalizing", 2, 8),  # the total changed
            ("Finalizing", 1, 8),  # done went back
        ):
            built = len(self.built)
            self.show(label, done, total)
            self.assertEqual(len(self.built), built + 1, (label, done, total))

        # A screen covered the bar: the same state is drawn anew.
        ui.CURRENT_LAYOUT = None
        self.show("Finalizing", 1, 8)
        self.assertEqual(len(self.built), 5)

        # An unknown total is motion, and past the total the bar is full.
        self.show("Deriving", 0, 0)
        self.assertTrue(self.built[-1].indeterminate)
        self.show("Signing", 9, 4)
        self.assertEqual(self.built[-1].reports, [(1000, "Signing")])


if __name__ == "__main__":
    unittest.main()
