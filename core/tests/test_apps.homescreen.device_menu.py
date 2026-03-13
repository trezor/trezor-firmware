# flake8: noqa: F403,F405
from common import *  # isort:skip

from mock import Mock, MockAsync, patch
from trezorui_api import CANCELLED, DeviceMenuResult

from apps.homescreen.device_menu import ExitDeviceMenu, handle_device_menu


class TestHandleDeviceMenu(unittest.TestCase):
    def setUp(self):
        # Mock all the dependencies
        import apps.homescreen.device_menu as device_menu_module

        self.device_menu_module = device_menu_module

        # Create mock for interact that we'll configure per test
        self.mock_interact = MockAsync()

        # Mock all the modules and functions
        self.mock_utils = Mock()
        self.mock_utils.USE_THP = True
        self.mock_utils.USE_BLE = True
        self.mock_utils.USE_RGB_LED = False
        self.mock_utils.USE_HAPTIC = False
        self.mock_utils.EMULATOR = True
        self.mock_utils.USE_NRF = False
        self.mock_utils.BITCOIN_ONLY = False
        self.mock_utils.MODEL_FULL_NAME = "Test Model"
        self.mock_utils.VERSION = (1, 0, 0)

        self.mock_storage_device = Mock()
        self.mock_storage_device.is_initialized = Mock(return_value=True)
        self.mock_storage_device.unfinished_backup = Mock(return_value=False)
        self.mock_storage_device.needs_backup = Mock(return_value=False)
        self.mock_storage_device.no_backup = Mock(return_value=False)
        self.mock_storage_device.get_label = Mock(return_value="Test Device")
        self.mock_storage_device.get_haptic_feedback = Mock(return_value=False)
        self.mock_storage_device.get_rgb_led = Mock(return_value=False)

        self.mock_ble = Mock()
        self.mock_ble.get_bonds = Mock(return_value=[])
        self.mock_ble.get_enabled = Mock(return_value=False)
        self.mock_ble.connected_addr = Mock(return_value=None)

        self.mock_config = Mock()
        self.mock_config.has_pin = Mock(return_value=False)
        self.mock_config.has_wipe_code = Mock(return_value=False)

        self.mock_paired_cache = Mock()
        self.mock_paired_cache.load = Mock(return_value=[])

        self.mock_trezorui_api = Mock()
        self.mock_trezorui_api.show_device_menu = Mock(return_value="menu_layout")

        # Apply patches
        self.patches = [
            patch(device_menu_module, 'utils', self.mock_utils),
            patch(device_menu_module, 'storage_device', self.mock_storage_device),
            patch(device_menu_module, 'ble', self.mock_ble),
            patch(device_menu_module, 'config', self.mock_config),
            patch(device_menu_module, 'interact', self.mock_interact),
            patch(device_menu_module, 'trezorui_api', self.mock_trezorui_api),
        ]

        for p in self.patches:
            p.__enter__()

        # Mock paired_cache in thp module
        import trezor.wire.thp as thp_module
        self.thp_patch = patch(thp_module, 'paired_cache', self.mock_paired_cache)
        self.thp_patch.__enter__()

    def tearDown(self):
        for p in self.patches:
            p.__exit__(None, None, None)
        self.thp_patch.__exit__(None, None, None)

    def test_refresh_menu_continues_without_handler_error(self):
        """Test that RefreshMenu action continues the loop without raising handler error.

        This is the main bug fix: RefreshMenu should be handled before checking for
        a handler in _MENU_HANDLERS, preventing a RuntimeError.
        """
        # First call returns RefreshMenu action, second call returns CANCELLED to exit
        submenu_idx = 2
        menu_result = (DeviceMenuResult.RefreshMenu, submenu_idx, None)

        self.mock_interact.return_value = menu_result
        call_count = [0]

        async def side_effect_interact(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return menu_result
            else:
                return CANCELLED

        self.mock_interact.__call__ = side_effect_interact

        # Should not raise RuntimeError
        result = await_result(handle_device_menu())

        # Should have exited normally (returns None)
        self.assertIsNone(result)

        # Verify interact was called twice (once for RefreshMenu, once for CANCELLED)
        self.assertEqual(call_count[0], 2)

    def test_refresh_menu_sets_init_submenu_idx(self):
        """Test that RefreshMenu action correctly sets the init_submenu_idx for the next iteration."""
        submenu_idx = 3

        call_count = [0]

        async def side_effect_interact(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                # First call: RefreshMenu with submenu_idx
                return (DeviceMenuResult.RefreshMenu, submenu_idx, None)
            else:
                # Second call: verify init_submenu_idx was passed correctly
                # Check that show_device_menu was called with correct init_submenu_idx
                show_device_menu_call = self.mock_trezorui_api.show_device_menu.calls[-1]
                init_submenu_arg = show_device_menu_call[1].get('init_submenu_idx')
                self.assertEqual(init_submenu_arg, submenu_idx)
                return CANCELLED

        self.mock_interact.__call__ = side_effect_interact

        result = await_result(handle_device_menu())
        self.assertIsNone(result)

    def test_invalid_action_raises_runtime_error(self):
        """Test that an invalid action (not RefreshMenu, not in handlers) raises RuntimeError."""
        # Use a DeviceMenuResult value that's not in _MENU_HANDLERS and not RefreshMenu
        # We'll use an integer that doesn't map to any handler
        invalid_action = 99999
        menu_result = (invalid_action, None, None)

        self.mock_interact.return_value = menu_result

        # Should raise RuntimeError for unknown menu action
        with self.assertRaises(RuntimeError) as cm:
            await_result(handle_device_menu())

        self.assertIn("Unknown menu", str(cm.exception))

    def test_valid_action_calls_handler(self):
        """Test that a valid action (in _MENU_HANDLERS) calls the appropriate handler."""
        import apps.homescreen.device_menu as device_menu_module

        # Create a mock handler
        mock_handler = MockAsync()
        parent_idx = 1

        # Patch a handler into _MENU_HANDLERS
        # Use ToggleBluetooth which exists in the handlers
        action = DeviceMenuResult.ToggleBluetooth
        original_handler = device_menu_module._MENU_HANDLERS.get(action)
        device_menu_module._MENU_HANDLERS[action] = mock_handler

        try:
            call_count = [0]

            async def side_effect_interact(*args, **kwargs):
                call_count[0] += 1
                if call_count[0] == 1:
                    return (action, None, parent_idx)
                else:
                    return CANCELLED

            self.mock_interact.__call__ = side_effect_interact

            result = await_result(handle_device_menu())

            # Handler should have been called
            self.assertEqual(len(mock_handler.calls), 1)
            # Handler called with no args (since arg was None)
            self.assertEqual(mock_handler.calls[0], ((), {}))

        finally:
            # Restore original handler
            if original_handler is not None:
                device_menu_module._MENU_HANDLERS[action] = original_handler

    def test_valid_action_with_arg_calls_handler_with_arg(self):
        """Test that a valid action with an argument calls handler with that argument."""
        import apps.homescreen.device_menu as device_menu_module

        # Create a mock handler
        mock_handler = MockAsync()

        # Use UnpairDevice which takes an index argument
        action = DeviceMenuResult.UnpairDevice
        original_handler = device_menu_module._MENU_HANDLERS.get(action)
        device_menu_module._MENU_HANDLERS[action] = mock_handler

        try:
            device_index = 2
            parent_idx = 0

            call_count = [0]

            async def side_effect_interact(*args, **kwargs):
                call_count[0] += 1
                if call_count[0] == 1:
                    return (action, device_index, parent_idx)
                else:
                    return CANCELLED

            self.mock_interact.__call__ = side_effect_interact

            result = await_result(handle_device_menu())

            # Handler should have been called with the argument
            self.assertEqual(len(mock_handler.calls), 1)
            self.assertEqual(mock_handler.calls[0], ((device_index,), {}))

        finally:
            # Restore original handler
            if original_handler is not None:
                device_menu_module._MENU_HANDLERS[action] = original_handler

    def test_cancelled_exits_menu(self):
        """Test that CANCELLED result exits the menu normally."""
        self.mock_interact.return_value = CANCELLED

        result = await_result(handle_device_menu())

        # Should exit normally (return None)
        self.assertIsNone(result)

    def test_exit_device_menu_exception_breaks_loop(self):
        """Test that ExitDeviceMenu exception breaks the loop."""
        import apps.homescreen.device_menu as device_menu_module

        # Create a handler that raises ExitDeviceMenu
        async def exit_handler():
            raise ExitDeviceMenu()

        action = DeviceMenuResult.ToggleBluetooth
        original_handler = device_menu_module._MENU_HANDLERS.get(action)
        device_menu_module._MENU_HANDLERS[action] = exit_handler

        try:
            self.mock_interact.return_value = (action, None, None)

            result = await_result(handle_device_menu())

            # Should exit normally
            self.assertIsNone(result)

        finally:
            # Restore original handler
            if original_handler is not None:
                device_menu_module._MENU_HANDLERS[action] = original_handler

    def test_invalid_menu_result_format_raises_error(self):
        """Test that an invalid menu result format raises RuntimeError."""
        # Return a non-tuple result
        self.mock_interact.return_value = "invalid"

        with self.assertRaises(RuntimeError) as cm:
            await_result(handle_device_menu())

        self.assertIn("Unknown menu", str(cm.exception))

    def test_menu_result_wrong_length_raises_error(self):
        """Test that a menu result with wrong tuple length raises RuntimeError."""
        # Return a tuple with wrong length (not 3)
        self.mock_interact.return_value = (DeviceMenuResult.RefreshMenu, 1)

        with self.assertRaises(RuntimeError) as cm:
            await_result(handle_device_menu())

        self.assertIn("Unknown menu", str(cm.exception))

    def test_handler_order_refresh_before_lookup(self):
        """Test that RefreshMenu check happens before handler lookup.

        This verifies the fix: if handler lookup came first, RefreshMenu would
        fail because it's not in _MENU_HANDLERS.
        """
        import apps.homescreen.device_menu as device_menu_module

        # Verify that RefreshMenu is NOT in the handlers dict
        self.assertNotIn(DeviceMenuResult.RefreshMenu, device_menu_module._MENU_HANDLERS)

        # But RefreshMenu should still work without error
        submenu_idx = 1

        call_count = [0]

        async def side_effect_interact(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return (DeviceMenuResult.RefreshMenu, submenu_idx, None)
            else:
                return CANCELLED

        self.mock_interact.__call__ = side_effect_interact

        # Should not raise RuntimeError even though RefreshMenu is not in handlers
        result = await_result(handle_device_menu())
        self.assertIsNone(result)

    def test_multiple_refresh_menu_calls_in_sequence(self):
        """Test that multiple consecutive RefreshMenu actions work correctly.

        This is a regression test ensuring the fix handles multiple refresh
        operations without raising handler lookup errors.
        """
        call_count = [0]
        submenu_indices = [1, 3, 5]

        async def side_effect_interact(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] <= len(submenu_indices):
                # Return RefreshMenu multiple times with different submenu indices
                return (DeviceMenuResult.RefreshMenu, submenu_indices[call_count[0] - 1], None)
            else:
                # Finally exit
                return CANCELLED

        self.mock_interact.__call__ = side_effect_interact

        # Should handle multiple RefreshMenu actions without error
        result = await_result(handle_device_menu())
        self.assertIsNone(result)

        # Verify all RefreshMenu calls were processed plus the final CANCELLED
        self.assertEqual(call_count[0], len(submenu_indices) + 1)

    def test_action_cancelled_exception_returns_to_submenu(self):
        """Test that ActionCancelled exception returns to the parent submenu.

        When a handler raises ActionCancelled, the menu should return to the
        parent submenu (using parent_submenu_idx) and continue the loop.
        """
        import apps.homescreen.device_menu as device_menu_module
        from trezor.wire import ActionCancelled

        # Create a handler that raises ActionCancelled
        async def cancelling_handler():
            raise ActionCancelled()

        action = DeviceMenuResult.ToggleBluetooth
        original_handler = device_menu_module._MENU_HANDLERS.get(action)
        device_menu_module._MENU_HANDLERS[action] = cancelling_handler

        try:
            parent_idx = 2
            call_count = [0]

            async def side_effect_interact(*args, **kwargs):
                call_count[0] += 1
                if call_count[0] == 1:
                    # First call: action that will raise ActionCancelled
                    return (action, None, parent_idx)
                else:
                    # Second call: verify we returned to parent submenu
                    show_device_menu_call = self.mock_trezorui_api.show_device_menu.calls[-1]
                    init_submenu_arg = show_device_menu_call[1].get('init_submenu_idx')
                    self.assertEqual(init_submenu_arg, parent_idx)
                    return CANCELLED

            self.mock_interact.__call__ = side_effect_interact

            result = await_result(handle_device_menu())

            # Should have returned to submenu and then exited
            self.assertIsNone(result)
            self.assertEqual(call_count[0], 2)

        finally:
            # Restore original handler
            if original_handler is not None:
                device_menu_module._MENU_HANDLERS[action] = original_handler


if __name__ == "__main__":
    unittest.main()