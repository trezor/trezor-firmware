# flake8: noqa: F403,F405
from common import *  # isort:skip

from trezor import ui
from trezor.ui import Shutdown, set_current_layout


class TestShutdownException(unittest.TestCase):
    def test_shutdown_is_exception(self):
        """Test that Shutdown is an Exception."""
        exc = Shutdown()
        self.assertIsInstance(exc, Exception)

    def test_shutdown_can_be_raised(self):
        """Test that Shutdown can be raised and caught."""
        with self.assertRaises(Shutdown):
            raise Shutdown()


class TestSetCurrentLayout(unittest.TestCase):
    def setUp(self):
        # Save original state
        self.original_layout = ui.CURRENT_LAYOUT
        ui.CURRENT_LAYOUT = None

    def tearDown(self):
        # Restore original state
        ui.CURRENT_LAYOUT = self.original_layout

    def test_set_current_layout_from_none(self):
        """Test setting layout from None."""
        # Can't create real Layout without full UI setup, so we use a mock object
        mock_layout = object()
        ui.CURRENT_LAYOUT = None
        set_current_layout(mock_layout)
        self.assertIs(ui.CURRENT_LAYOUT, mock_layout)

    def test_set_current_layout_to_none(self):
        """Test clearing the current layout."""
        mock_layout = object()
        ui.CURRENT_LAYOUT = mock_layout
        set_current_layout(None)
        self.assertIsNone(ui.CURRENT_LAYOUT)

    def test_set_current_layout_assertion(self):
        """Test that setting layout requires valid transition."""
        # Setting from non-None to non-None should fail assertion
        mock_layout1 = object()
        mock_layout2 = object()
        ui.CURRENT_LAYOUT = mock_layout1

        with self.assertRaises(AssertionError):
            set_current_layout(mock_layout2)


class TestLayoutConstants(unittest.TestCase):
    def test_width_constant(self):
        """Test that WIDTH constant exists and is reasonable."""
        self.assertIsInstance(ui.WIDTH, int)
        self.assertGreater(ui.WIDTH, 0)

    def test_height_constant(self):
        """Test that HEIGHT constant exists and is reasonable."""
        self.assertIsInstance(ui.HEIGHT, int)
        self.assertGreater(ui.HEIGHT, 0)


class TestAlertFunction(unittest.TestCase):
    def test_alert_accepts_count(self):
        """Test that alert function accepts a count parameter."""
        # Alert schedules async task, so we just verify it doesn't raise
        ui.alert(1)
        ui.alert(3)
        ui.alert(5)

    def test_alert_default_parameter(self):
        """Test alert with default count parameter."""
        # Default should be 3
        ui.alert()


class TestUIGlobals(unittest.TestCase):
    def test_current_layout_global_exists(self):
        """Test that CURRENT_LAYOUT global exists."""
        # It should be None or a layout object
        self.assertTrue(hasattr(ui, 'CURRENT_LAYOUT'))

    def test_shutdown_exception_hierarchy(self):
        """Test Shutdown exception can be caught as BaseException."""
        try:
            raise Shutdown()
        except BaseException as e:
            self.assertIsInstance(e, Shutdown)


if __name__ == "__main__":
    unittest.main()