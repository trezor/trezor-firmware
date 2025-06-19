# isort: skip_file
from trezor import log, loop, utils, wire, workflow

import apps.base
import usb

apps.base.boot()

if not utils.BITCOIN_ONLY and usb.ENABLE_IFACE_WEBAUTHN:
    import apps.webauthn

    apps.webauthn.boot()

if __debug__:
    import apps.debug

    apps.debug.boot()

# run main event loop and specify which screen is the default
apps.base.set_homescreen()
workflow.start_default()

# initialize the wire codec over USB
wire.setup(usb.iface_wire)

if utils.USE_BLE:
    import trezorble as ble

    # initialize the wire codec over BLE
    wire.setup(ble.interface)

import trezorui_api
from trezor.ui.layouts.common import interact

class Menu:
    def __init__(self, *children: "Details"):
        self.children = children

class Details:
    def __init__(self, name: str, *items: tuple[str, str]):
        self.name = name
        self.items = items

async def test_menu():
    menu_items = Menu(
        Details(
            "Account info",
            ("Account", "ETH #2"),
            ("Derivation path", "m/1/2/3/4"),
        ),
        Details("Block hash",
             (None, "0x1355557e447b95b89c75a5d4909701d52faf2716eb30c55a6c9fcbb735748f9e", True),
        ),
        Details("Fee info",
            ("Gas limit", "21000 units"),
            ("Max fee per gas", "3.28 Gwei"),
            ("Max priority fee", "1.7 Gwei"),
        ),
    )
    menu_path = []
    menu_init = None
    while True:
        menu = menu_items
        for i in menu_path:
            menu = menu.children[i]

        if isinstance(menu, Menu):
            items = [child.name for child in menu.children]
            layout = trezorui_api.select_menu(items=items, init=menu_init)
        else:
            items = [(item + (False,))[:3] for item in menu.items]
            layout = trezorui_api.confirm_properties(title=menu.name, items=items)

        try:
            res = await interact(layout, "menu")
            print([res])
            if isinstance(res, int):
                assert 0 <= res < len(items)
                menu_path.append(res)
                menu_init = None
                continue
        except wire.ActionCancelled:
            pass

        if menu_path:
            menu_init = menu_path.pop()
        else:
            return

workflow.spawn(test_menu())

# start the event loop
loop.run()

if __debug__:
    log.debug(__name__, "Restarting main loop")
