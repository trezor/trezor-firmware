# flake8: noqa: F403,F405
from common import *  # isort:skip

import trezorui_api
from trezor import utils

# `usb_event` takes the raw event code, see `USBEvent::new`.
USB_CONFIGURED = 1
USB_DECONFIGURED = 2


def menu_params(**overrides):
    """The full parameter set the device menu is constructed from."""
    params = {
        "init_submenu_idx": None,
        "init_submenu_offset": 0,
        "backup_failed": False,
        "backup_needed": False,
        "ble_enabled": True,
        "paired_devices": [],
        "connected_idx": None,
        "host_connected": False,
        "pin_enabled": True,
        "auto_lock": ("Auto-lock", "10 minutes"),
        "wipe_code_enabled": False,
        "backup_check_allowed": True,
        "device_name": "Trezor",
        "brightness": "Brightness",
        "tap_to_wake_enabled": True,
        "haptics_enabled": True,
        "led_enabled": True,
        "about_items": [("Firmware", "0.0.0.0", False)],
        "production_year": "(2026)",
    }
    params.update(overrides)
    return params


@unittest.skipUnless(utils.UI_LAYOUT == "ECKHART", "device menu is Eckhart only")
class TestParamsRequest(unittest.TestCase):
    """The device menu names the parameters that went stale, and keeps running."""

    def make_menu(self, **overrides):
        # collect the timers the layout asks for, to replay one later
        self.timers = []
        layout = trezorui_api.show_device_menu(menu_params(**overrides)).__enter__()
        layout.attach_timer_fn(lambda token, deadline: self.timers.append(token), None)
        layout.paint()
        return layout

    def test_fresh_layout_asks_for_nothing(self):
        layout = self.make_menu()
        self.assertIsNone(layout.params_request())

    def test_usb_event_asks_for_the_connection_indicator(self):
        layout = self.make_menu()
        layout.usb_event(USB_CONFIGURED)
        # USB feeds exactly one displayed value, so one key is named
        self.assertEqual(layout.params_request(), ("host_connected",))

    def test_request_is_taken_out_on_read(self):
        layout = self.make_menu()
        layout.usb_event(USB_CONFIGURED)
        self.assertEqual(layout.params_request(), ("host_connected",))
        # the second read comes up empty; the request was served by the reader
        self.assertIsNone(layout.params_request())

    def test_unread_requests_merge(self):
        layout = self.make_menu()
        layout.usb_event(USB_CONFIGURED)
        layout.usb_event(USB_DECONFIGURED)
        # a later pass must not drop what an earlier one asked for
        self.assertEqual(layout.params_request(), ("host_connected",))

    def test_update_params_does_not_re_ask(self):
        layout = self.make_menu()
        layout.usb_event(USB_DECONFIGURED)
        layout.params_request()
        layout.update_params(menu_params(device_name="Renamed"))
        self.assertIsNone(layout.params_request())

    def test_request_survives_until_read(self):
        layout = self.make_menu()
        layout.usb_event(USB_CONFIGURED)
        # an unrelated event pass in between must not drop the pending request
        if self.timers:
            layout.timer(self.timers[0])
        self.assertEqual(layout.params_request(), ("host_connected",))

    def test_keys_name_real_params(self):
        # every key the layout asks for must exist in the set it is built from,
        # or the provider could not serve it
        layout = self.make_menu()
        layout.usb_event(USB_CONFIGURED)
        full = menu_params()
        for key in layout.params_request():
            self.assertIn(key, full)


if __name__ == "__main__":
    unittest.main()
