"""
Central place for defining all input flows for the device tests.

Each model has potentially its own input flow, and in most cases
we need to distinguish between them. Doing it at one place
offers a better overview of the differences and makes it easier
to maintain. The whole `device_tests` folder can then focus
only on the actual tests and data-assertions, not on the lower-level
input flow details.
"""

from __future__ import annotations

from typing import Callable

from trezorlib import messages as trezor_messages
from trezorlib.client import Session
from trezorlib.debuglink import DebugLink, DebugSession, LayoutContent, LayoutType
from trezorlib.debuglink import TrezorTestContext as Client
from trezorlib.debuglink import multipage_content
from trezorlib.testing import translations as TR
from trezorlib.testing.common import (
    BRGeneratorType,
    swipe_if_necessary,
)

B = trezor_messages.ButtonRequestType


class EthereumFlow:

    def __init__(self, client: Client):
        self.client = client
        self.debug = self.client.debug

    def confirm_data(self, info: bool = False, cancel: bool = False) -> BRGeneratorType:
        assert (yield).name == "confirm_data"
        TR.regexp("ethereum__title_all_input_data_template").fullmatch(
            self.debug.read_layout().title().strip()
        )
        if info:
            self.debug.press_info()
        elif cancel:
            self.debug.press_no()
        else:
            self.debug.press_yes()

    def paginate_data(self) -> BRGeneratorType:
        br = yield
        assert br.name == "confirm_data"
        assert br.pages is not None
        assert self.client.layout_type is LayoutType.Eckhart
        TR.regexp("ethereum__title_all_input_data_template").fullmatch(
            self.debug.read_layout().title().strip()
        )
        for _ in range(br.pages - 1):
            self.debug.read_layout()
            self.debug.click(self.debug.screen_buttons.ok())


        self.debug.read_layout()
        self.debug.click(self.debug.screen_buttons.ok())

    def paginate_data_go_back(self) -> BRGeneratorType:
        br = yield
        assert br.name == "confirm_data"
        assert br.pages is not None
        assert br.pages > 2
        assert self.client.layout_type is LayoutType.Eckhart

        TR.regexp("ethereum__title_all_input_data_template").fullmatch(
            self.debug.read_layout().title().strip()
        )

        # Scroll to the last page
        for _ in range(br.pages - 1):
            self.debug.click(self.debug.screen_buttons.ok())
        # Go back to the first page and then cancel
        for _ in range(br.pages):
            self.debug.click(self.debug.screen_buttons.cancel())

    def _confirm_tx(
        self, cancel: bool, info: bool, go_back_from_summary: bool
    ) -> BRGeneratorType:

        assert (yield).name == "confirm_output"
        title_exp = (
            TR.words__send
            if self.client.layout_type is LayoutType.Eckhart
            else TR.words__address
        )
        assert title_exp in self.debug.read_layout().title()
        if cancel:
            self.debug.press_no()
            return

        self.debug.click(self.debug.screen_buttons.ok())
        assert (yield).name == "confirm_total"
        layout = self.debug.read_layout()
        title_exp = (
            TR.words__send
            if self.client.layout_type is LayoutType.Eckhart
            else TR.words__title_summary
        )
        assert layout.title() == title_exp
        assert TR.send__maximum_fee in layout.text_content()
        if go_back_from_summary:
            # Get back to the address screen
            self.debug.click(self.debug.screen_buttons.cancel())
            assert (yield).name == "confirm_output"
            title = self.debug.read_layout().title()
            assert title_exp in title
            # Get back to the summary screen
            self.debug.click(self.debug.screen_buttons.ok())
            assert (yield).name == "confirm_total"
            layout = self.debug.read_layout()
            assert layout.title() == title_exp
            assert TR.send__maximum_fee in layout.text_content()
        if info:
            self.debug.click(self.debug.screen_buttons.menu())
            self.debug.synchronize_at("VerticalMenu")
            self.debug.button_actions.navigate_to_menu_item(0)
            text = self.debug.read_layout().text_content()
            assert TR.ethereum__gas_limit in text
            assert TR.ethereum__gas_price in text
            self.debug.click(self.debug.screen_buttons.menu())
            self.debug.click(self.debug.screen_buttons.menu())
        self.debug.click(self.debug.screen_buttons.ok())
        self.debug.read_layout()
        assert (yield).name == "confirm_ethereum_tx"

    def confirm_tx(
        self,
        cancel: bool = False,
        info: bool = False,
        go_back_from_summary: bool = False,
    ) -> BRGeneratorType:

        assert self.client.layout_type is LayoutType.Eckhart

        yield from self._confirm_tx(cancel, info, go_back_from_summary)

    def confirm_tx_staking(
        self,
        info: bool = False,
    ) -> BRGeneratorType:
        br = yield
        assert br.code == B.SignTx
        assert br.name == "confirm_ethereum_staking_tx"
        assert self.debug.read_layout().title() in (
            TR.ethereum__staking_stake,
            TR.ethereum__staking_unstake,
            TR.ethereum__staking_claim,
        )
        assert self.debug.read_layout().text_content() in (
            TR.ethereum__staking_stake_intro,
            TR.ethereum__staking_unstake_intro,
            TR.ethereum__staking_claim_intro,
        )
        assert self.client.layout_type is LayoutType.Eckhart

        # confirm intro
        if info:
            self.debug.click(self.debug.screen_buttons.menu())
            self.debug.synchronize_at("VerticalMenu")
            self.debug.button_actions.navigate_to_menu_item(0)
            assert self.debug.read_layout().title() in (
                TR.ethereum__staking_stake_address,
                TR.ethereum__staking_claim_address,
            )
            self.debug.click(self.debug.screen_buttons.menu())
            self.debug.click(self.debug.screen_buttons.menu())

        self.debug.click(self.debug.screen_buttons.ok())
        br = yield
        assert br.code == B.SignTx
        assert br.name == "confirm_total"

        # confirm summary
        if info:
            self.debug.click(self.debug.screen_buttons.menu())
            self.debug.synchronize_at("VerticalMenu")
            self.debug.button_actions.navigate_to_menu_item(0)
            assert TR.ethereum__gas_limit in self.debug.read_layout().text_content()
            assert TR.ethereum__gas_price in self.debug.read_layout().text_content()
            self.debug.click(self.debug.screen_buttons.menu())
            self.debug.click(self.debug.screen_buttons.menu())

        self.debug.press_yes()


class InputFlowBase:
    def __init__(self, client: Client | DebugSession):
        if isinstance(client, Session):
            client = client.test_ctx
        self.client = client
        self.debug: DebugLink = client.debug
        self.ETH = EthereumFlow(self.client)
        self.layout_type = client.layout_type

    def get(self) -> Callable[[], BRGeneratorType]:
        self.client.watch_layout(True)

        # There is currently just one input flow for all models
        assert hasattr(self, "input_flow")
        return getattr(self, "input_flow")

    def text_content(self) -> str:
        return self.debug.read_layout().text_content()

    def main_component(self) -> str:
        return self.debug.read_layout().main_component()

    def all_components(self) -> list[str]:
        return self.debug.read_layout().all_components()

    def title(self) -> str:
        return self.debug.read_layout().title()


class InputFlowSignVerifyMessageLong(InputFlowBase):
    def __init__(self, client: Client | DebugSession, verify=False):
        super().__init__(client)
        self.message_read = ""
        self.verify = verify

    def input_flow(self) -> BRGeneratorType:
        # collect screen contents into `message_read`.
        # Using a helper debuglink function to assemble the final text.
        layouts: list[LayoutContent] = []

        br = yield  # confirm address
        self.debug.read_layout()
        self.debug.press_yes()

        br = yield  # confirm address intro

        self.debug.click(self.debug.screen_buttons.menu())
        self.debug.synchronize_at("VerticalMenu")
        self.debug.button_actions.navigate_to_menu_item(0)

        br = yield  # confirm address long
        self.debug.read_layout()
        assert br.pages is not None
        for i in range(br.pages):
            layout = self.debug.read_layout()
            layouts.append(layout)

            if i < br.pages - 1:
                self.debug.click(self.debug.screen_buttons.ok())

        self.message_read = multipage_content(layouts)

        self.debug.press_yes()

        if self.verify:
            # "The signature is valid!" screen
            self.debug.press_yes()
            br = yield


class InputFlowSignMessageInfo(InputFlowBase):
    def __init__(self, client: Client):
        super().__init__(client)

    def input_flow(self) -> BRGeneratorType:
        yield
        # go to info menu
        self.debug.click(self.debug.screen_buttons.menu())
        # close menu
        self.debug.click(self.debug.screen_buttons.menu())
        # cancel flow
        self.debug.press_no()
        # confirm cancel
        self.debug.press_yes()
        yield


class InputFlowShowAddressQRCode(InputFlowBase):
    def __init__(self, client: Client):
        super().__init__(client)

    def input_flow(self) -> BRGeneratorType:
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


class InputFlowEIP712ShowMore(InputFlowBase):
    def __init__(self, client: Client | DebugSession):
        super().__init__(client)
        self.same_for_all_models = True

    def _confirm_show_more(self) -> None:
        """Model-specific, either clicks a screen or presses a button."""

        assert self.layout_type is LayoutType.Eckhart
        self.debug.click(self.debug.screen_buttons.menu())
        self.debug.button_actions.navigate_to_menu_item(0)

    def input_flow(self) -> BRGeneratorType:
        """Triggers show more wherever possible"""
        yield  # confirm address
        self.debug.press_yes()

        yield  # confirm domain
        self.debug.read_layout()
        self._confirm_show_more()

        # confirm domain properties
        for _ in range(4):
            yield from swipe_if_necessary(self.debug)  # EIP712 DOMAIN
            self.debug.press_yes()

        yield  # confirm message
        self.debug.read_layout()
        self._confirm_show_more()

        yield  # confirm message.from
        self.debug.read_layout()
        self._confirm_show_more()

        # confirm message.from properties
        for _ in range(2):
            yield from swipe_if_necessary(self.debug)
            self.debug.press_yes()

        yield  # confirm message.to
        self.debug.read_layout()
        self._confirm_show_more()

        # confirm message.to properties
        for _ in range(2):
            yield from swipe_if_necessary(self.debug)
            self.debug.press_yes()

        yield  # confirm message.contents
        self.debug.press_yes()

        yield  # confirm final hash
        self.debug.press_yes()


class InputFlowEIP712Cancel(InputFlowBase):
    def __init__(self, client: Client | DebugSession):
        super().__init__(client)

    def input_flow(self) -> BRGeneratorType:
        """Clicks cancelling button"""
        yield  # confirm address
        self.debug.press_yes()

        yield  # confirm domain
        self.debug.press_no()


class InputFlowSignTxShowFeeInfo(InputFlowBase):
    def __init__(self, client: Client | DebugSession):
        super().__init__(client)

    def input_flow(self) -> BRGeneratorType:
        yield from self.ETH.confirm_tx(info=True)


class InputFlowSignTxGoBackFromSummary(InputFlowBase):
    def __init__(self, client: Client | DebugSession):
        super().__init__(client)

    def input_flow(self) -> BRGeneratorType:
        yield from self.ETH.confirm_tx(go_back_from_summary=True)


class InputFlowSignTxDataSkip(InputFlowBase):
    def __init__(self, client: Client | DebugSession, cancel: bool = False):
        super().__init__(client)
        self.cancel = cancel

    def input_flow(self) -> BRGeneratorType:
        yield from self.ETH.confirm_data()
        yield from self.ETH.confirm_tx(cancel=self.cancel)


class InputFlowSignTxDataScrollDown(InputFlowBase):
    def __init__(self, client: Client | DebugSession, cancel: bool = False):
        super().__init__(client)
        self.cancel = cancel

    def input_flow(self) -> BRGeneratorType:
        # this flow will not test for the cancel case,
        # because once we enter the "view all data",
        # the only way to cancel is by going back to the 1st page view
        # but that case would be covered by InputFlowSignTxDataGoBack
        assert not self.cancel

        yield from self.ETH.confirm_data(info=True)
        yield from self.ETH.paginate_data()
        yield from self.ETH.confirm_tx()


class InputFlowSignTxDataGoBack(InputFlowBase):
    def __init__(self, client: Client | DebugSession, cancel: bool = False):
        super().__init__(client)
        self.cancel = cancel

    def input_flow(self) -> BRGeneratorType:
        yield from self.ETH.confirm_data(info=True)
        yield from self.ETH.paginate_data_go_back()
        if self.cancel:
            yield from self.ETH.confirm_data(cancel=True)
        else:
            yield from self.ETH.confirm_data()
            yield from self.ETH.confirm_tx()


class InputFlowSignTxStaking(InputFlowBase):
    def __init__(self, client: Client | DebugSession):
        super().__init__(client)

    def input_flow(self) -> BRGeneratorType:
        yield from self.ETH.confirm_tx_staking(info=True)


class InputFlowConfirmAllWarnings(InputFlowBase):

    def input_flow(self) -> BRGeneratorType:
        br = yield
        while True:
            # Paginating (going as further as possible) and pressing Yes
            if br.pages is not None:
                for _ in range(br.pages - 1):
                    self.client.ui.visit_menu_items()
                    self.debug.click(self.debug.screen_buttons.ok())

            layout = self.client.ui.visit_menu_items()
            text = layout.action_bar().lower()
            # hi priority warning
            hi_prio = (
                TR.words__cancel_and_exit,
                TR.send__cancel_sign,
                TR.send__cancel_transaction,
            )
            if any(needle.lower() in text for needle in hi_prio):
                self.debug.click(self.debug.screen_buttons.menu())
                self.debug.synchronize_at("VerticalMenu")
                self.debug.button_actions.navigate_to_menu_item(1)
            else:
                self.debug.click(self.debug.screen_buttons.ok())
            br = yield
