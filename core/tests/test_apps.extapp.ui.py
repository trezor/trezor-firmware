# flake8: noqa: F403,F405
from common import *  # isort:skip

import trezorui_api

# rkyv-archived `TrezorUiEnum::SelectMenu` requests (trezor-app-sdk) with
# items "1".."7" and "1".."6", no cancel entry, br_code 0
SELECT_MENU_7 = bytes.fromhex(
    "3132333435363700f8ffffff01000000f1ffffff01000000eaffffff01000000"
    "e3ffffff01000000dcffffff01000000d5ffffff01000000ceffffff01000000"
    "00000000c4ffffff07000000" + "00" * 108
)
SELECT_MENU_6 = bytes.fromhex(
    "3132333435360000f8ffffff01000000f1ffffff01000000eaffffff01000000"
    "e3ffffff01000000dcffffff01000000d5ffffff0100000000000000ccffffff"
    "06000000" + "00" * 108
)


@unittest.skipUnless(
    hasattr(trezorui_api, "process_ipc_message"), "built without app loading"
)
class TestProcessIpcMessage(unittest.TestCase):
    def test_select_menu_max_items(self):
        _layout, br_code, br_name = trezorui_api.process_ipc_message(data=SELECT_MENU_6)
        self.assertEqual(br_code, 0)
        self.assertIsNone(br_name)

    def test_select_menu_too_many_items(self):
        # more items than MAX_MENU_ITEMS must be rejected, not crash Core
        with self.assertRaises(ValueError):
            trezorui_api.process_ipc_message(data=SELECT_MENU_7)


if __name__ == "__main__":
    unittest.main()
