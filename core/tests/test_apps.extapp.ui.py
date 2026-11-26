# flake8: noqa: F403,F405
from common import *  # isort:skip

import trezorui_api
from trezor import utils

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
# `TrezorUiEnum::ShowProperties` with title "t" and properties "1".."5" or
# "1".."4", each with value "v", no subtitle, no br_name, br_code 0
SHOW_PROPERTIES_5 = bytes.fromhex(
    "743176327633763476357600f5ffffff01000000eeffffff0100000000000000"
    "e3ffffff01000000dcffffff0100000000000000d1ffffff01000000caffffff"
    "0100000000000000bfffffff01000000b8ffffff0100000000000000adffffff"
    "01000000a6ffffff01000000000000000c0000008cffffff0100000090ffffff"
    "05000000" + "00" * 100
)
SHOW_PROPERTIES_4 = bytes.fromhex(
    "743176327633763476000000f5ffffff01000000eeffffff0100000000000000"
    "e3ffffff01000000dcffffff0100000000000000d1ffffff01000000caffffff"
    "0100000000000000bfffffff01000000b8ffffff01000000000000000c000000"
    "a0ffffff01000000a4ffffff04000000" + "00" * 100
)
# `TrezorUiEnum::ShowAddress` for "addr1", account "acc", path "m/44h" and one
# xpub ("XPUB #1", "xpub6abc"), br_code 0
SHOW_ADDRESS_XPUB = bytes.fromhex(
    "616464723161646472316163636d2f3434685850554220233178707562366162"
    "63000000eeffffff07000000edffffff080000000100000010000000c4ffffff"
    "05000000c1ffffff050000000000000000000000000000000000000000000000"
    "0000000001000000a2ffffff030000000100000099ffffff05000000a8ffffff"
    "01000000000000000000000001000000" + "00" * 32
)


# the functions exist without app loading too, but only to fail
@unittest.skipUnless(utils.USE_APP_LOADING, "built without app loading")
class TestProcessIpcMessage(unittest.TestCase):
    def test_select_menu_max_items(self):
        _layout, br_code, br_name = trezorui_api.process_ipc_message(data=SELECT_MENU_6)
        self.assertEqual(br_code, 0)
        self.assertIsNone(br_name)

    def test_select_menu_too_many_items(self):
        # more items than MAX_MENU_ITEMS must be rejected, not crash Core
        with self.assertRaises(ValueError):
            trezorui_api.process_ipc_message(data=SELECT_MENU_7)

    def test_show_properties_max(self):
        _layout, br_code, br_name = trezorui_api.process_ipc_message(
            data=SHOW_PROPERTIES_4
        )
        self.assertEqual(br_code, 0)
        self.assertIsNone(br_name)

    @unittest.skipUnless(
        utils.UI_LAYOUT in ("DELIZIA", "ECKHART"), "limit of 4 properties"
    )
    def test_show_properties_too_many(self):
        # more properties than the layout holds must be rejected, not crash Core
        with self.assertRaises(ValueError):
            trezorui_api.process_ipc_message(data=SHOW_PROPERTIES_5)

    def test_show_address_with_xpub(self):
        # the address flows unpack each xpub as a (title, xpub) pair
        _layout, br_code, br_name = trezorui_api.process_ipc_message(
            data=SHOW_ADDRESS_XPUB
        )
        self.assertEqual(br_code, 0)
        self.assertIsNone(br_name)

    def test_not_a_buffer(self):
        with self.assertRaises(TypeError):
            trezorui_api.process_ipc_message(data=123)
        with self.assertRaises(TypeError):
            trezorui_api.deserialize_progress_message(data=123)

    def test_serialize_ui_result(self):
        # rkyv-archived `TrezorUiResult`s, as the app decodes them
        self.assertEqual(
            trezorui_api.serialize_ui_result(result=trezorui_api.CONFIRMED),
            bytes.fromhex("0000000000000000"),
        )
        self.assertEqual(
            trezorui_api.serialize_ui_result(result=3),
            bytes.fromhex("0400000003000000"),
        )

    def test_serialize_ui_result_invalid(self):
        with self.assertRaises(TypeError):
            trezorui_api.serialize_ui_result(result="x")


if __name__ == "__main__":
    unittest.main()
