# flake8: noqa: F403,F405
from common import *  # isort:skip

from mock import Mock, MockAsync, patch
from trezor import ui, workflow
from trezor.enums import ButtonRequestType
from trezor.ui.layouts import common
from trezor.wire import ActionCancelled
from trezorui_api import CANCELLED, CONFIRMED, INFO


class MockLayoutObj:
    """Mock LayoutObj for testing."""

    def __init__(self, return_value=CONFIRMED):
        self._return_value = return_value
        self._attach_called = False

    def attach_timer_fn(self, timer_fn, attach_type):
        self._attach_called = True
        return None

    def button_request(self):
        return None

    def page_count(self):
        return 1

    def get_transition_out(self):
        return None

    def return_value(self):
        return self._return_value

    def paint(self):
        return True

    def request_complete_repaint(self):
        return None

    def trace(self, callback):
        callback("MockLayout")

    def __del__(self):
        pass


class TestInteract(unittest.TestCase):
    def setUp(self):
        # Reset global state
        ui.set_current_layout(None)
        workflow.tasks.clear()

    def tearDown(self):
        ui.set_current_layout(None)
        workflow.tasks.clear()

    def test_interact_returns_confirmed_result(self):
        """Test that interact returns result when confirmed."""
        layout_obj = MockLayoutObj(CONFIRMED)

        async def test():
            # Mock the Layout.get_result to return immediately
            with patch(ui.Layout, "__init__", lambda self, obj: setattr(self, "layout", obj)):
                with patch(
                    ui.Layout, "get_result", MockAsync(return_value=CONFIRMED)
                ):
                    with patch(ui.Layout, "start", Mock()):
                        with patch(ui.Layout, "put_button_request", Mock()):
                            result = await common.interact(
                                layout_obj, "test_button", ButtonRequestType.Other
                            )
                            return result

        from trezor import loop

        result = loop.run(test())
        self.assertEqual(result, CONFIRMED)

    def test_interact_raises_on_cancel(self):
        """Test that interact raises ActionCancelled when cancelled."""
        layout_obj = MockLayoutObj(CANCELLED)

        async def test():
            with patch(ui.Layout, "__init__", lambda self, obj: setattr(self, "layout", obj)):
                with patch(
                    ui.Layout, "get_result", MockAsync(return_value=CANCELLED)
                ):
                    with patch(ui.Layout, "start", Mock()):
                        with patch(ui.Layout, "put_button_request", Mock()):
                            return await common.interact(
                                layout_obj, "test_button", ButtonRequestType.Other
                            )

        from trezor import loop

        with self.assertRaises(ActionCancelled):
            loop.run(test())

    def test_interact_with_custom_exception(self):
        """Test that interact raises custom exception on cancel."""

        class CustomException(Exception):
            pass

        layout_obj = MockLayoutObj(CANCELLED)

        async def test():
            with patch(ui.Layout, "__init__", lambda self, obj: setattr(self, "layout", obj)):
                with patch(
                    ui.Layout, "get_result", MockAsync(return_value=CANCELLED)
                ):
                    with patch(ui.Layout, "start", Mock()):
                        with patch(ui.Layout, "put_button_request", Mock()):
                            return await common.interact(
                                layout_obj,
                                "test_button",
                                ButtonRequestType.Other,
                                raise_on_cancel=CustomException,
                            )

        from trezor import loop

        with self.assertRaises(CustomException):
            loop.run(test())

    def test_interact_with_none_raise_on_cancel(self):
        """Test that interact returns CANCELLED when raise_on_cancel is None."""
        layout_obj = MockLayoutObj(CANCELLED)

        async def test():
            with patch(ui.Layout, "__init__", lambda self, obj: setattr(self, "layout", obj)):
                with patch(
                    ui.Layout, "get_result", MockAsync(return_value=CANCELLED)
                ):
                    with patch(ui.Layout, "start", Mock()):
                        with patch(ui.Layout, "put_button_request", Mock()):
                            result = await common.interact(
                                layout_obj,
                                "test_button",
                                ButtonRequestType.Other,
                                raise_on_cancel=None,
                            )
                            return result

        from trezor import loop

        result = loop.run(test())
        self.assertEqual(result, CANCELLED)

    def test_interact_confirm_only_returns_none(self):
        """Test that interact with confirm_only=True returns None on confirm."""
        layout_obj = MockLayoutObj(CONFIRMED)

        async def test():
            with patch(ui.Layout, "__init__", lambda self, obj: setattr(self, "layout", obj)):
                with patch(
                    ui.Layout, "get_result", MockAsync(return_value=CONFIRMED)
                ):
                    with patch(ui.Layout, "start", Mock()):
                        with patch(ui.Layout, "put_button_request", Mock()):
                            result = await common.interact(
                                layout_obj,
                                "test_button",
                                ButtonRequestType.Other,
                                confirm_only=True,
                            )
                            return result

        from trezor import loop

        result = loop.run(test())
        self.assertIsNone(result)

    def test_interact_confirm_only_raises_on_cancel(self):
        """Test that interact with confirm_only=True raises on cancel."""
        layout_obj = MockLayoutObj(CANCELLED)

        async def test():
            with patch(ui.Layout, "__init__", lambda self, obj: setattr(self, "layout", obj)):
                with patch(
                    ui.Layout, "get_result", MockAsync(return_value=CANCELLED)
                ):
                    with patch(ui.Layout, "start", Mock()):
                        with patch(ui.Layout, "put_button_request", Mock()):
                            return await common.interact(
                                layout_obj,
                                "test_button",
                                ButtonRequestType.Other,
                                confirm_only=True,
                            )

        from trezor import loop

        with self.assertRaises(ActionCancelled):
            loop.run(test())

    def test_interact_confirm_only_raises_runtime_error_on_unexpected(self):
        """Test that confirm_only raises RuntimeError on unexpected result."""
        layout_obj = MockLayoutObj(INFO)

        async def test():
            with patch(ui.Layout, "__init__", lambda self, obj: setattr(self, "layout", obj)):
                with patch(ui.Layout, "get_result", MockAsync(return_value=INFO)):
                    with patch(ui.Layout, "start", Mock()):
                        with patch(ui.Layout, "put_button_request", Mock()):
                            return await common.interact(
                                layout_obj,
                                "test_button",
                                ButtonRequestType.Other,
                                confirm_only=True,
                            )

        from trezor import loop

        with self.assertRaises(RuntimeError):
            loop.run(test())


class TestRaiseIfNotConfirmed(unittest.TestCase):
    def test_raise_if_not_confirmed_is_coroutine(self):
        """Test that raise_if_not_confirmed returns a coroutine."""
        layout_obj = MockLayoutObj(CONFIRMED)
        result = common.raise_if_not_confirmed(
            layout_obj, "test_button", ButtonRequestType.Other
        )

        # Should be a coroutine
        self.assertTrue(hasattr(result, "send"))


class TestDrawSimple(unittest.TestCase):
    def setUp(self):
        ui.set_current_layout(None)

    def tearDown(self):
        ui.set_current_layout(None)

    def test_draw_simple_starts_layout(self):
        """Test that draw_simple starts the layout."""
        layout_obj = MockLayoutObj()

        with patch(ui.Layout, "__init__", lambda self, obj: setattr(self, "layout", obj)):
            with patch(ui.Layout, "start", Mock()) as mock_start:
                common.draw_simple(layout_obj)
                self.assertEqual(len(mock_start.calls), 1)


class TestWithInfo(unittest.TestCase):
    def test_with_info_returns_on_confirmed(self):
        """Test that with_info returns when main layout is confirmed."""
        main_layout = MockLayoutObj(CONFIRMED)
        info_layout = MockLayoutObj(CONFIRMED)

        async def test():
            with patch(ui.Layout, "__init__", lambda self, obj: setattr(self, "layout", obj)):
                with patch(
                    ui.Layout, "get_result", MockAsync(return_value=CONFIRMED)
                ):
                    with patch(ui.Layout, "start", Mock()):
                        with patch(ui.Layout, "put_button_request", Mock()):
                            await common.with_info(
                                main_layout,
                                info_layout,
                                "test_button",
                                ButtonRequestType.Other,
                            )

        from trezor import loop

        loop.run(test())
        # Should complete without raising

    def test_with_info_raises_on_cancel(self):
        """Test that with_info raises ActionCancelled on cancel."""
        main_layout = MockLayoutObj(CANCELLED)
        info_layout = MockLayoutObj(CONFIRMED)

        async def test():
            with patch(ui.Layout, "__init__", lambda self, obj: setattr(self, "layout", obj)):
                with patch(
                    ui.Layout, "get_result", MockAsync(return_value=CANCELLED)
                ):
                    with patch(ui.Layout, "start", Mock()):
                        with patch(ui.Layout, "put_button_request", Mock()):
                            await common.with_info(
                                main_layout,
                                info_layout,
                                "test_button",
                                ButtonRequestType.Other,
                            )

        from trezor import loop

        with self.assertRaises(ActionCancelled):
            loop.run(test())


class TestConfirmLinearFlow(unittest.TestCase):
    def test_confirm_linear_flow_progresses_forward(self):
        """Test that confirm_linear_flow progresses through layouts."""

        async def layout1():
            return CONFIRMED

        async def layout2():
            return CONFIRMED

        async def test():
            await common.confirm_linear_flow(layout1, layout2)

        from trezor import loop

        loop.run(test())
        # Should complete without raising

    def test_confirm_linear_flow_raises_on_cancel(self):
        """Test that confirm_linear_flow raises on cancel."""

        async def layout1():
            return CANCELLED

        async def test():
            await common.confirm_linear_flow(layout1)

        from trezor import loop

        with self.assertRaises(ActionCancelled):
            loop.run(test())


class TestInteractEdgeCases(unittest.TestCase):
    def setUp(self):
        ui.set_current_layout(None)
        workflow.tasks.clear()

    def tearDown(self):
        ui.set_current_layout(None)
        workflow.tasks.clear()

    def test_interact_without_button_request_name(self):
        """Test interact with br_name=None."""
        layout_obj = MockLayoutObj(CONFIRMED)

        async def test():
            with patch(ui.Layout, "__init__", lambda self, obj: setattr(self, "layout", obj)):
                with patch(
                    ui.Layout, "get_result", MockAsync(return_value=CONFIRMED)
                ):
                    with patch(ui.Layout, "start", Mock()):
                        with patch(ui.Layout, "put_button_request", Mock()) as mock_put:
                            result = await common.interact(
                                layout_obj, None, ButtonRequestType.Other
                            )
                            # put_button_request should not be called when br_name is None
                            self.assertEqual(len(mock_put.calls), 0)
                            return result

        from trezor import loop

        result = loop.run(test())
        self.assertEqual(result, CONFIRMED)

    def test_interact_with_different_button_request_types(self):
        """Test interact with different button request types."""
        layout_obj = MockLayoutObj(CONFIRMED)

        button_types = [
            ButtonRequestType.Other,
            ButtonRequestType.Address,
            ButtonRequestType.SignTx,
        ]

        for btn_type in button_types:

            async def test():
                with patch(ui.Layout, "__init__", lambda self, obj: setattr(self, "layout", obj)):
                    with patch(
                        ui.Layout, "get_result", MockAsync(return_value=CONFIRMED)
                    ):
                        with patch(ui.Layout, "start", Mock()):
                            with patch(ui.Layout, "put_button_request", Mock()):
                                result = await common.interact(
                                    layout_obj, "test", btn_type
                                )
                                return result

            from trezor import loop

            result = loop.run(test())
            self.assertEqual(result, CONFIRMED)


if __name__ == "__main__":
    unittest.main()