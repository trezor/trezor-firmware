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
    def __init__(self, *items: "Item"):
        self.items = items

class Item:
    def __init__(self, name: str, *items: tuple[str, str]):
        self.name = name
        self.items = items

async def test_menu():
    menu_items = Menu(
        Item(
            "Account info",
            ("Account", "ETH #2"),
            ("Derivation path", "m/1/2/3/4"),
        ),
        Item("Block hash",
             ("Block hash", "1355557e447b95b89c75a5d4909701d52faf2716eb30c55a6c9fcbb735748f9e"),
        ),
        Item("Fee info",
            ("Gas limit", "21000 units"),
            ("Max fee per gas", "3.28 Gwei"),
            ("Max priority fee", "1.7 Gwei"),
        ),
    )
    location = []
    while True:
        menu = menu_items
        for i in location:
            menu = menu.items[i]

        if isinstance(menu, Item):
            items = [f'{k}\n{v}' for k, v in menu.items]
            layout = trezorui_api.multiple_pages_texts(title=menu.name, verb="OK", items=items)
        else:
            items = [i.name for i in menu.items]
            layout = trezorui_api.select_menu(items=items)

        try:
            res = await interact(layout, "menu")
            print([res])
            if isinstance(res, int):
                assert 0 <= res < len(items)
                location.append(res)
                continue
        except wire.ActionCancelled:
            pass

        if not location:
            return
        location.pop()

workflow.spawn(test_menu())

# start the event loop
loop.run()

if __debug__:
    log.debug(__name__, "Restarting main loop")
