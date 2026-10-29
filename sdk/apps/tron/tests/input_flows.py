"""
The input flows the Tron device tests drive, per model.

On Delizia, signing follows core's own `tests/input_flows.py`, and the address
follows the testapp's `test_showcase.py`, which drives the same library verify
screen. Tron builds only for Delizia (T3T1) and Eckhart (T3W1).
"""

from __future__ import annotations

from collections.abc import Callable

from trezorlib.client import Session
from trezorlib.debuglink import DebugLink, DebugSession, LayoutContent, LayoutType
from trezorlib.debuglink import TrezorTestContext as Client
from trezorlib.testing import translations as TR
from trezorlib.testing.common import BRGeneratorType


def _is_hi_prio(text: str) -> bool:
    """A high-priority warning: its way forward sits in the menu, not the button."""
    needles = (
        TR.words__cancel_and_exit,
        TR.send__cancel_sign,
        TR.send__cancel_transaction,
    )
    return any(needle.lower() in text.lower() for needle in needles)


class InputFlowBase:
    def __init__(self, client: Client | DebugSession):
        if isinstance(client, Session):
            client = client.test_ctx
        self.client = client
        self.debug: DebugLink = client.debug
        self.layout_type = client.layout_type

    def get(self) -> Callable[[], BRGeneratorType]:
        if self.layout_type is LayoutType.Delizia:
            return self.input_flow_delizia
        if self.layout_type is LayoutType.Eckhart:
            return self.input_flow_eckhart
        raise ValueError(f"No input flow for {self.layout_type}")

    def input_flow_delizia(self) -> BRGeneratorType:
        raise NotImplementedError

    def input_flow_eckhart(self) -> BRGeneratorType:
        raise NotImplementedError


class InputFlowShowAddressQRCode(InputFlowBase):
    def input_flow_delizia(self) -> BRGeneratorType:
        yield
        self.debug.click(self.debug.screen_buttons.menu())
        self.debug.synchronize_at("VerticalMenu")
        # menu
        self.debug.button_actions.navigate_to_menu_item(0)
        self.debug.synchronize_at("Qr")
        # qr code
        self.debug.click(self.debug.screen_buttons.menu())
        # menu
        self.debug.button_actions.navigate_to_menu_item(1)
        # account info
        self.debug.click(self.debug.screen_buttons.menu())
        # menu: close it
        self.debug.click(self.debug.screen_buttons.menu())

        layout = self.debug.read_layout()
        while "PromptScreen" not in layout.all_components():
            self.debug.swipe_up()
            layout = self.debug.read_layout()
        # tap to confirm
        self.debug.click(self.debug.screen_buttons.tap_to_confirm())
        # "confirmed": continue to the app
        self.debug.press_yes()

    def input_flow_eckhart(self) -> BRGeneratorType:
        yield
        self.debug.click(self.debug.screen_buttons.menu())
        self.debug.synchronize_at("VerticalMenu")
        # menu
        self.debug.button_actions.navigate_to_menu_item(0)
        self.debug.synchronize_at("Qr")
        # qr code
        self.debug.click(self.debug.screen_buttons.menu())
        # menu
        self.debug.button_actions.navigate_to_menu_item(1)
        # address details
        self.debug.click(self.debug.screen_buttons.menu())
        # menu
        self.debug.button_actions.navigate_to_menu_item(2)
        # cancel
        self.debug.click(self.debug.screen_buttons.cancel())
        # address
        self.debug.synchronize_at("TextScreen")
        self.debug.click(self.debug.screen_buttons.ok())
        # continue to the app
        self.debug.press_yes()


class InputFlowConfirmAllWarnings(InputFlowBase):
    def __init__(
        self,
        client: Client | DebugSession,
        on_page: Callable[["LayoutContent"], None] | None = None,
    ) -> None:
        super().__init__(client)
        self.on_page = on_page

    def input_flow_delizia(self) -> BRGeneratorType:
        br = yield
        while True:
            # Paginating (going as further as possible) and pressing Yes
            if br.pages is not None:
                for _ in range(br.pages - 1):
                    layout = self.client.ui.visit_menu_items()
                    if self.on_page is not None:
                        self.on_page(layout)
                    self.debug.swipe_up()

            layout = self.client.ui.visit_menu_items()

            if self.on_page is not None:
                self.on_page(layout)

            if _is_hi_prio(layout.footer()):
                self.debug.click(self.debug.screen_buttons.menu())
                self.debug.synchronize_at("VerticalMenu")
                self.debug.button_actions.navigate_to_menu_item(1)
            elif "PromptScreen" in layout.all_components():
                self.debug.press_yes()
            elif "SwipeContent" in layout.all_components():
                self.debug.swipe_up()
            else:
                self.debug.press_yes()
            br = yield

    def input_flow_eckhart(self) -> BRGeneratorType:
        br = yield
        while True:
            # Paginating (going as further as possible) and pressing Yes
            if br.pages is not None:
                for _ in range(br.pages - 1):
                    layout = self.client.ui.visit_menu_items()
                    if self.on_page is not None:
                        self.on_page(layout)
                    self.debug.click(self.debug.screen_buttons.ok())

            layout = self.client.ui.visit_menu_items()

            if self.on_page is not None:
                self.on_page(layout)

            if _is_hi_prio(layout.action_bar()):
                self.debug.click(self.debug.screen_buttons.menu())
                self.debug.synchronize_at("VerticalMenu")
                self.debug.button_actions.navigate_to_menu_item(1)
            else:
                self.debug.click(self.debug.screen_buttons.ok())
            br = yield
