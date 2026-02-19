# flake8: noqa: F403,F405
from common import *  # isort:skip

from mock import Mock, MockAsync, patch
from trezor import loop, ui, workflow
from trezor.ui import Layout, ProgressLayout, set_current_layout, CURRENT_LAYOUT
from trezorui_api import LayoutState


class MockLayoutObj:
    """Mock LayoutObj for testing."""

    def __init__(self, return_value=None):
        self._return_value = return_value
        self._state = LayoutState.INITIAL
        self._timers = {}
        self._button_request_result = None
        self._transition_out = None
        self._page_count = 1

    def attach_timer_fn(self, timer_fn, attach_type):
        return LayoutState.ATTACHED

    def button_event(self, *args):
        return None

    def touch_event(self, *args):
        return None

    def timer(self, token):
        return None

    def paint(self):
        return True

    def request_complete_repaint(self):
        return None

    def return_value(self):
        return self._return_value

    def button_request(self):
        return self._button_request_result

    def page_count(self):
        return self._page_count

    def get_transition_out(self):
        return self._transition_out

    def trace(self, callback):
        callback("MockLayout")

    def __del__(self):
        pass


class TestLayoutInitialization(unittest.TestCase):
    def setUp(self):
        # Reset global layout state
        set_current_layout(None)

    def tearDown(self):
        set_current_layout(None)

    def test_layout_initialization(self):
        """Test Layout initialization with LayoutObj."""
        layout_obj = MockLayoutObj()
        layout = Layout(layout_obj)

        self.assertEqual(layout.layout, layout_obj)
        self.assertEqual(len(layout.tasks), 0)
        self.assertEqual(len(layout.timers), 0)
        self.assertFalse(layout.button_request_ack_pending)
        self.assertIsNone(layout.transition_out)
        self.assertEqual(layout.state, LayoutState.INITIAL)

    def test_layout_is_ready_initially(self):
        """Test that a new layout is ready."""
        layout_obj = MockLayoutObj()
        layout = Layout(layout_obj)

        self.assertTrue(layout.is_ready())
        self.assertFalse(layout.is_running())
        self.assertFalse(layout.is_finished())

    def test_layout_should_resume_default_false(self):
        """Test that should_resume defaults to False."""
        layout_obj = MockLayoutObj()
        layout = Layout(layout_obj)

        self.assertFalse(layout.should_resume)


class TestSetCurrentLayout(unittest.TestCase):
    def setUp(self):
        set_current_layout(None)

    def tearDown(self):
        set_current_layout(None)

    def test_set_current_layout_none_to_layout(self):
        """Test setting current layout from None to a layout."""
        layout_obj = MockLayoutObj()
        layout = Layout(layout_obj)

        set_current_layout(layout)
        self.assertEqual(CURRENT_LAYOUT, layout)

    def test_set_current_layout_layout_to_none(self):
        """Test setting current layout from layout to None."""
        layout_obj = MockLayoutObj()
        layout = Layout(layout_obj)

        set_current_layout(layout)
        set_current_layout(None)
        self.assertIsNone(CURRENT_LAYOUT)

    def test_set_current_layout_assertion(self):
        """Test that setting layout requires transition through None."""
        layout_obj1 = MockLayoutObj()
        layout1 = Layout(layout_obj1)

        layout_obj2 = MockLayoutObj()
        layout2 = Layout(layout_obj2)

        set_current_layout(layout1)

        # Should not be able to set another layout without going through None
        with self.assertRaises(AssertionError):
            set_current_layout(layout2)


class TestLayoutStates(unittest.TestCase):
    def setUp(self):
        set_current_layout(None)

    def tearDown(self):
        set_current_layout(None)

    def test_is_ready_when_not_running(self):
        """Test is_ready returns True when layout not running and no result."""
        layout_obj = MockLayoutObj()
        layout = Layout(layout_obj)

        self.assertTrue(layout.is_ready())

    def test_is_running_when_current(self):
        """Test is_running returns True when layout is CURRENT_LAYOUT."""
        layout_obj = MockLayoutObj()
        layout = Layout(layout_obj)

        set_current_layout(layout)
        self.assertTrue(layout.is_running())

    def test_is_finished_with_result(self):
        """Test is_finished returns True when result is available."""
        layout_obj = MockLayoutObj(42)
        layout = Layout(layout_obj)

        # Simulate having a result
        layout.result_box.put(42)

        self.assertFalse(layout.is_ready())
        self.assertFalse(layout.is_running())
        self.assertTrue(layout.is_finished())

    def test_is_layout_attached(self):
        """Test is_layout_attached checks state."""
        layout_obj = MockLayoutObj()
        layout = Layout(layout_obj)

        self.assertFalse(layout.is_layout_attached())

        layout.state = LayoutState.ATTACHED
        self.assertTrue(layout.is_layout_attached())


class TestLayoutStop(unittest.TestCase):
    def setUp(self):
        set_current_layout(None)

    def tearDown(self):
        set_current_layout(None)

    def test_stop_clears_current_layout(self):
        """Test that stop() clears the current layout."""
        layout_obj = MockLayoutObj()
        layout = Layout(layout_obj)

        set_current_layout(layout)
        self.assertEqual(CURRENT_LAYOUT, layout)

        layout.stop()
        self.assertIsNone(CURRENT_LAYOUT)

    def test_stop_clears_timers(self):
        """Test that stop() clears all timers."""
        layout_obj = MockLayoutObj()
        layout = Layout(layout_obj)

        # Add some mock timers
        layout.timers[1] = Mock()
        layout.timers[2] = Mock()

        layout.stop()

        self.assertEqual(len(layout.timers), 0)

    def test_stop_stores_transition_out(self):
        """Test that stop() stores transition_out."""
        layout_obj = MockLayoutObj()
        layout_obj._transition_out = Mock()
        layout = Layout(layout_obj)

        set_current_layout(layout)
        layout.stop()

        self.assertEqual(layout.transition_out, layout_obj._transition_out)


class TestProgressLayout(unittest.TestCase):
    def setUp(self):
        set_current_layout(None)

    def tearDown(self):
        set_current_layout(None)

    def test_progress_layout_initialization(self):
        """Test ProgressLayout initialization."""
        layout_obj = MockLayoutObj()
        progress = ProgressLayout(layout_obj)

        self.assertEqual(progress.layout, layout_obj)
        self.assertIsNone(progress.transition_out)
        self.assertEqual(progress.value, 0)
        self.assertEqual(progress.progress_step, 20)

    def test_progress_layout_is_layout_attached(self):
        """Test that ProgressLayout is always attached."""
        layout_obj = MockLayoutObj()
        progress = ProgressLayout(layout_obj)

        self.assertTrue(progress.is_layout_attached())

    def test_progress_layout_report_starts_layout(self):
        """Test that report() starts the layout if not running."""
        layout_obj = MockLayoutObj()
        layout_obj.progress_event = Mock(return_value=None)
        progress = ProgressLayout(layout_obj)

        self.assertIsNone(CURRENT_LAYOUT)

        progress.report(100)

        self.assertEqual(CURRENT_LAYOUT, progress)

    def test_progress_layout_stop(self):
        """Test that ProgressLayout can be stopped."""
        layout_obj = MockLayoutObj()
        progress = ProgressLayout(layout_obj)

        set_current_layout(progress)
        self.assertEqual(CURRENT_LAYOUT, progress)

        progress.stop()
        self.assertIsNone(CURRENT_LAYOUT)


class TestLayoutButtonRequest(unittest.TestCase):
    def setUp(self):
        set_current_layout(None)

    def tearDown(self):
        set_current_layout(None)

    def test_put_button_request(self):
        """Test put_button_request creates ButtonRequest."""
        from trezor.messages import ButtonRequest
        from trezor.enums import ButtonRequestType

        layout_obj = MockLayoutObj()
        layout = Layout(layout_obj)

        layout.put_button_request((ButtonRequestType.Other, "test_name"))

        # Button request should be in the mailbox
        self.assertFalse(layout.button_request_box.is_empty())
        br = layout.button_request_box.value
        self.assertIsInstance(br, ButtonRequest)
        self.assertEqual(br.name, "test_name")

    def test_put_button_request_none(self):
        """Test put_button_request with None."""
        layout_obj = MockLayoutObj()
        layout = Layout(layout_obj)

        layout.put_button_request(None)

        # Should put None in the mailbox
        self.assertFalse(layout.button_request_box.is_empty())
        self.assertIsNone(layout.button_request_box.value)


class TestLayoutRepaint(unittest.TestCase):
    def setUp(self):
        set_current_layout(None)

    def tearDown(self):
        set_current_layout(None)

    def test_request_complete_repaint(self):
        """Test request_complete_repaint calls layout method."""
        layout_obj = MockLayoutObj()
        layout_obj.request_complete_repaint = Mock(return_value=None)
        layout = Layout(layout_obj)

        layout.request_complete_repaint()

        self.assertEqual(len(layout_obj.request_complete_repaint.calls), 1)

    def test_repaint_calls_paint(self):
        """Test repaint calls layout methods."""
        layout_obj = MockLayoutObj()
        layout_obj.request_complete_repaint = Mock(return_value=None)
        layout_obj.paint = Mock(return_value=True)
        layout = Layout(layout_obj)

        layout.repaint()

        self.assertEqual(len(layout_obj.request_complete_repaint.calls), 1)
        self.assertEqual(len(layout_obj.paint.calls), 1)


class TestLayoutEdgeCases(unittest.TestCase):
    def setUp(self):
        set_current_layout(None)

    def tearDown(self):
        set_current_layout(None)

    def test_layout_with_should_resume_true(self):
        """Test layout with should_resume set to True."""
        layout_obj = MockLayoutObj()
        layout = Layout(layout_obj)
        layout.should_resume = True

        self.assertTrue(layout.should_resume)

    def test_multiple_layouts_lifecycle(self):
        """Test creating multiple layouts in sequence."""
        layout_obj1 = MockLayoutObj()
        layout1 = Layout(layout_obj1)

        layout_obj2 = MockLayoutObj()
        layout2 = Layout(layout_obj2)

        # Both should be ready initially
        self.assertTrue(layout1.is_ready())
        self.assertTrue(layout2.is_ready())

        # Set first as current
        set_current_layout(layout1)
        self.assertTrue(layout1.is_running())
        self.assertFalse(layout2.is_running())

        # Clear and set second
        set_current_layout(None)
        set_current_layout(layout2)
        self.assertFalse(layout1.is_running())
        self.assertTrue(layout2.is_running())

    def test_layout_state_transitions(self):
        """Test Layout state transitions."""
        layout_obj = MockLayoutObj()
        layout = Layout(layout_obj)

        self.assertEqual(layout.state, LayoutState.INITIAL)

        layout.state = LayoutState.ATTACHED
        self.assertEqual(layout.state, LayoutState.ATTACHED)

        layout.state = LayoutState.TRANSITIONING
        self.assertEqual(layout.state, LayoutState.TRANSITIONING)


if __name__ == "__main__":
    unittest.main()