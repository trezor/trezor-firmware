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

import time
from typing import Callable, Generator

from trezorlib import messages, models
from trezorlib.debuglink import DebugLink, LayoutContent
from trezorlib.debuglink import TrezorClientDebugLink as Client
from trezorlib.debuglink import multipage_content

from . import buttons
from . import translations as TR
from .common import (
    BRGeneratorType,
    check_pin_backoff_time,
    click_info_button_tt,
    click_through,
    get_text_possible_pagination,
    read_and_confirm_mnemonic,
    swipe_if_necessary,
)
from .input_flows_helpers import BackupFlow, EthereumFlow, PinFlow, RecoveryFlow

B = messages.ButtonRequestType


class InputFlowBase:
    def __init__(self, client: Client):
        self.client = client
        self.debug: DebugLink = client.debug
        self.PIN = PinFlow(self.client)
        self.REC = RecoveryFlow(self.client)
        self.BAK = BackupFlow(self.client)
        self.ETH = EthereumFlow(self.client)

    def model(self) -> str | models.TrezorModel:
        return self.client.model

    def get(self) -> Callable[[], BRGeneratorType]:
        self.client.watch_layout(True)

        # There could be one common input flow for all models
        if hasattr(self, "input_flow_common"):
            return getattr(self, "input_flow_common")
        elif self.model() is models.T2T1:
            return self.input_flow_tt
        elif self.model() is models.T2B1:
            return self.input_flow_tr
        elif self.model() is models.T3T1:
            return self.input_flow_t3t1
        else:
            raise ValueError("Unknown model")

    def input_flow_tt(self) -> BRGeneratorType:
        """Special for TT"""
        raise NotImplementedError

    def input_flow_tr(self) -> BRGeneratorType:
        """Special for TR"""
        raise NotImplementedError

    def input_flow_t3t1(self) -> BRGeneratorType:
        """Special for T3T1"""
        raise NotImplementedError

    def text_content(self) -> str:
        return self.debug.wait_layout().text_content()

    def main_component(self) -> str:
        return self.debug.wait_layout().main_component()

    def all_components(self) -> list[str]:
        return self.debug.wait_layout().all_components()

    def title(self) -> str:
        return self.debug.wait_layout().title()


class InputFlowSetupDevicePINWIpeCode(InputFlowBase):
    def __init__(self, client: Client, pin: str, wipe_code: str):
        super().__init__(client)
        self.pin = pin
        self.wipe_code = wipe_code

    def input_flow_common(self) -> BRGeneratorType:
        yield  # do you want to set/change the wipe code?
        self.debug.press_yes()

        if self.model() is models.T2B1:
            yield from swipe_if_necessary(self.debug)  # wipe code info
            self.debug.press_yes()

        yield  # enter current pin
        self.debug.input(self.pin)
        yield  # enter new wipe code
        self.debug.input(self.wipe_code)
        yield  # enter new wipe code again
        self.debug.input(self.wipe_code)
        yield  # success
        self.debug.press_yes()


class InputFlowNewCodeMismatch(InputFlowBase):
    def __init__(
        self,
        client: Client,
        first_code: str,
        second_code: str,
    ):
        super().__init__(client)
        self.first_code = first_code
        self.second_code = second_code

    def input_flow_common(self) -> BRGeneratorType:
        yield  # do you want to set/change the pin/wipe code?
        self.debug.press_yes()

        if self.model() is models.T2B1:
            yield from swipe_if_necessary(self.debug)  # code info
            self.debug.press_yes()

        def input_two_different_pins() -> BRGeneratorType:
            yield from self.PIN.setup_new_pin(self.first_code, self.second_code)

        yield from input_two_different_pins()

        yield  # PIN mismatch
        self.debug.press_yes()  # try again

        yield from input_two_different_pins()

        yield  # PIN mismatch
        self.debug.press_yes()  # try again

        yield  # PIN entry again

        self.debug.press_no()  # cancel


class InputFlowCodeChangeFail(InputFlowBase):
    def __init__(
        self, client: Client, current_pin: str, new_pin_1: str, new_pin_2: str
    ):
        super().__init__(client)
        self.current_pin = current_pin
        self.new_pin_1 = new_pin_1
        self.new_pin_2 = new_pin_2

    def input_flow_common(self) -> BRGeneratorType:
        yield  # do you want to change pin?
        self.debug.press_yes()
        yield  # enter current pin
        self.debug.input(self.current_pin)

        yield from self.PIN.setup_new_pin(self.new_pin_1, self.new_pin_2)

        yield  # PIN mismatch
        self.debug.press_yes()  # try again

        # failed retry
        yield  # enter current pin again
        self.client.cancel()


class InputFlowWrongPIN(InputFlowBase):
    def __init__(self, client: Client, wrong_pin: str):
        super().__init__(client)
        self.wrong_pin = wrong_pin

    def input_flow_common(self) -> BRGeneratorType:
        yield  # do you want to change pin?
        self.debug.press_yes()
        yield  # enter wrong current pin
        self.debug.input(self.wrong_pin)
        yield
        self.debug.press_no()


class InputFlowPINBackoff(InputFlowBase):
    def __init__(self, client: Client, wrong_pin: str, good_pin: str):
        super().__init__(client)
        self.wrong_pin = wrong_pin
        self.good_pin = good_pin

    def input_flow_common(self) -> BRGeneratorType:
        """Inputting some bad PINs and finally the correct one"""
        yield  # PIN entry
        for attempt in range(3):
            start = time.time()
            self.debug.input(self.wrong_pin)
            yield  # PIN entry
            check_pin_backoff_time(attempt, start)
        self.debug.input(self.good_pin)


class InputFlowSignMessagePagination(InputFlowBase):
    def __init__(self, client: Client):
        super().__init__(client)
        self.message_read = ""

    def input_flow_tt(self) -> BRGeneratorType:
        # collect screen contents into `message_read`.
        # Using a helper debuglink function to assemble the final text.
        layouts: list[LayoutContent] = []

        br = yield  # confirm address
        self.debug.wait_layout()
        self.debug.press_yes()

        br = yield
        assert br.pages is not None
        for i in range(br.pages):
            layout = self.debug.wait_layout()
            layouts.append(layout)

            if i < br.pages - 1:
                self.debug.swipe_up()

        self.message_read = multipage_content(layouts)

        self.debug.press_yes()

    def input_flow_tr(self) -> BRGeneratorType:
        # confirm address
        yield
        self.debug.press_yes()

        # press info
        yield
        self.debug.press_right()

        # paginate through the whole message
        br = yield
        # TODO: try load the message_read the same way as in model T
        if br.pages is not None:
            for i in range(br.pages):
                if i < br.pages - 1:
                    self.debug.swipe_up()
        self.debug.press_yes()

        # confirm message
        yield
        self.debug.press_yes()

    def input_flow_t3t1(self) -> BRGeneratorType:
        # collect screen contents into `message_read`.
        # Using a helper debuglink function to assemble the final text.
        layouts: list[LayoutContent] = []

        br = yield  # confirm address
        self.debug.wait_layout()
        self.debug.press_yes()

        br = yield
        assert br.pages is not None
        for i in range(br.pages):
            layout = self.debug.wait_layout()
            layouts.append(layout)

            if i < br.pages - 1:
                self.debug.swipe_up()

        self.message_read = multipage_content(layouts)

        self.debug.press_yes()


class InputFlowSignMessageInfo(InputFlowBase):
    def __init__(self, client: Client):
        super().__init__(client)

    def input_flow_tt(self) -> BRGeneratorType:
        yield
        # show address/message info
        self.debug.click(buttons.CORNER_BUTTON, wait=True)
        self.debug.click(buttons.CORNER_BUTTON, wait=True)
        self.debug.press_no(wait=True)
        self.debug.synchronize_at("IconDialog")
        # address mismatch?
        self.debug.press_no()
        yield
        self.debug.press_yes()
        yield
        self.debug.press_no()
        yield
        self.debug.press_no(wait=True)
        self.debug.press_yes(wait=True)

    def input_flow_t3t1(self) -> BRGeneratorType:
        yield
        # show address/message info
        self.debug.click(buttons.CORNER_BUTTON, wait=True)
        self.debug.click(buttons.CORNER_BUTTON, wait=True)
        self.debug.press_no(wait=True)
        self.debug.synchronize_at("IconDialog")
        # address mismatch?
        self.debug.press_no()
        yield
        self.debug.press_yes()
        yield
        self.debug.press_no()
        yield
        self.debug.press_no(wait=True)
        self.debug.press_yes(wait=True)


class InputFlowShowAddressQRCode(InputFlowBase):
    def __init__(self, client: Client):
        super().__init__(client)

    def input_flow_tt(self) -> BRGeneratorType:
        yield
        self.debug.click(buttons.CORNER_BUTTON, wait=True)
        # synchronize; TODO get rid of this once we have single-global-layout
        self.debug.synchronize_at("SimplePage")

        self.debug.swipe_left(wait=True)
        self.debug.swipe_right(wait=True)
        self.debug.swipe_left(wait=True)
        self.debug.click(buttons.CORNER_BUTTON, wait=True)
        self.debug.press_no(wait=True)
        self.debug.press_no(wait=True)
        self.debug.press_yes()

    def input_flow_tr(self) -> BRGeneratorType:
        # Find out the page-length of the address
        br = yield
        if br.pages is not None:
            address_swipes = br.pages - 1
        else:
            address_swipes = 0
        for _ in range(address_swipes):
            self.debug.press_right()

        # Go into details
        self.debug.press_right()
        # Go through details and back
        self.debug.press_right()
        self.debug.press_left()
        self.debug.press_left()
        # Confirm
        for _ in range(address_swipes):
            self.debug.press_right()
        self.debug.press_middle()

    def input_flow_t3t1(self) -> BRGeneratorType:
        yield
        self.debug.click(buttons.CORNER_BUTTON, wait=True)
        # synchronize; TODO get rid of this once we have single-global-layout
        self.debug.synchronize_at("VerticalMenu")
        # menu
        self.debug.click(buttons.VERTICAL_MENU[0], wait=True)
        self.debug.synchronize_at("Qr")
        # qr code
        self.debug.click(buttons.CORNER_BUTTON, wait=True)
        # menu
        self.debug.click(buttons.VERTICAL_MENU[1], wait=True)
        # address details
        self.debug.click(buttons.CORNER_BUTTON, wait=True)
        # menu
        self.debug.click(buttons.VERTICAL_MENU[2], wait=True)
        # cancel
        self.debug.swipe_up(wait=True)
        # really cancel
        self.debug.click(buttons.CORNER_BUTTON, wait=True)
        # menu
        layout = self.debug.click(buttons.CORNER_BUTTON, wait=True)

        while "PromptScreen" not in layout.all_components():
            layout = self.debug.swipe_up(wait=True)
        self.debug.synchronize_at("PromptScreen")
        # tap to confirm
        self.debug.click(buttons.TAP_TO_CONFIRM)


class InputFlowShowAddressQRCodeCancel(InputFlowBase):
    def __init__(self, client: Client):
        super().__init__(client)

    def input_flow_tt(self) -> BRGeneratorType:
        yield
        self.debug.click(buttons.CORNER_BUTTON, wait=True)
        # synchronize; TODO get rid of this once we have single-global-layout
        self.debug.synchronize_at("SimplePage")

        self.debug.swipe_left(wait=True)
        self.debug.click(buttons.CORNER_BUTTON, wait=True)
        self.debug.press_no(wait=True)
        self.debug.press_yes()

    def input_flow_tr(self) -> BRGeneratorType:
        yield
        # Go into details
        self.debug.press_right()
        # Go through details and back
        self.debug.press_right()
        self.debug.press_left()
        self.debug.press_left()
        # Cancel
        self.debug.press_left(wait=True)
        # Confirm address mismatch
        # Clicking right twice, as some languages can have two pages
        self.debug.press_right()
        self.debug.press_right()

    def input_flow_t3t1(self) -> BRGeneratorType:
        yield
        self.debug.click(buttons.CORNER_BUTTON, wait=True)
        # synchronize; TODO get rid of this once we have single-global-layout
        self.debug.synchronize_at("VerticalMenu")
        # menu
        self.debug.click(buttons.VERTICAL_MENU[0], wait=True)
        self.debug.synchronize_at("Qr")
        # qr code
        self.debug.click(buttons.CORNER_BUTTON, wait=True)
        # menu
        self.debug.click(buttons.VERTICAL_MENU[1], wait=True)
        # address details
        self.debug.click(buttons.CORNER_BUTTON, wait=True)
        # menu
        self.debug.click(buttons.VERTICAL_MENU[2], wait=True)
        # cancel
        self.debug.swipe_up(wait=True)
        self.debug.synchronize_at("PromptScreen")
        # really cancel
        self.debug.click(buttons.TAP_TO_CONFIRM, wait=True)


class InputFlowShowMultisigXPUBs(InputFlowBase):
    def __init__(self, client: Client, address: str, xpubs: list[str], index: int):
        super().__init__(client)
        self.address = address
        self.xpubs = xpubs
        self.index = index

    def input_flow_tt(self) -> BRGeneratorType:
        yield  # multisig address warning
        self.debug.press_yes()

        yield  # show address
        layout = self.debug.wait_layout()
        TR.assert_in(layout.title(), "address__title_receive_address")
        assert "(MULTISIG)" in layout.title()
        assert layout.text_content().replace(" ", "") == self.address

        self.debug.click(buttons.CORNER_BUTTON)
        assert "Qr" in self.all_components()

        layout = self.debug.swipe_left(wait=True)
        # address details
        assert "Multisig 2 of 3" in layout.screen_content()
        TR.assert_in(layout.screen_content(), "address_details__derivation_path_colon")

        # Three xpub pages with the same testing logic
        for xpub_num in range(3):
            expected_title = f"MULTISIG XPUB #{xpub_num + 1}"
            layout = self.debug.swipe_left(wait=True)
            assert expected_title in layout.title()
            content = layout.text_content().replace(" ", "")
            assert self.xpubs[xpub_num] in content

        self.debug.click(buttons.CORNER_BUTTON, wait=True)
        # show address
        self.debug.press_no(wait=True)
        # address mismatch
        self.debug.press_no(wait=True)
        # show address
        self.debug.press_yes()

    def input_flow_tr(self) -> BRGeneratorType:
        yield  # multisig address warning
        self.debug.press_middle()

        yield  # show address
        layout = self.debug.wait_layout()
        TR.assert_in(layout.title(), "address__title_receive_address")
        assert "(MULTISIG)" in layout.title()
        assert layout.text_content().replace(" ", "") == self.address

        self.debug.press_right()
        assert "Qr" in self.all_components()

        layout = self.debug.press_right(wait=True)
        # address details
        # TODO: locate it more precisely
        assert "Multisig 2 of 3" in layout.json_str

        # Three xpub pages with the same testing logic
        for xpub_num in range(3):
            expected_title = f"MULTISIG XPUB #{xpub_num + 1}"
            layout = self.debug.press_right(wait=True)
            assert expected_title in layout.title()
            xpub_part_1 = layout.text_content().replace(" ", "")
            # Press "SHOW MORE"
            layout = self.debug.press_middle(wait=True)
            xpub_part_2 = layout.text_content().replace(" ", "")
            # Go back
            self.debug.press_left(wait=True)
            assert self.xpubs[xpub_num] == xpub_part_1 + xpub_part_2

        for _ in range(5):
            self.debug.press_left()
        # show address
        self.debug.press_left()
        # address mismatch
        self.debug.press_left()
        # show address
        self.debug.press_middle()

    def input_flow_t3t1(self) -> BRGeneratorType:
        yield  # multisig address warning
        self.debug.click(buttons.CORNER_BUTTON, wait=True)
        self.debug.synchronize_at("VerticalMenu")
        self.debug.click(buttons.VERTICAL_MENU[1])

        yield  # show address
        layout = self.debug.wait_layout()
        TR.assert_in(layout.title(), "address__title_receive_address")
        assert layout.text_content().replace(" ", "") == self.address

        self.debug.click(buttons.CORNER_BUTTON, wait=True)
        assert "VerticalMenu" in self.all_components()
        # menu
        self.debug.click(buttons.VERTICAL_MENU[0], wait=True)
        self.debug.synchronize_at("Qr")
        # qr code
        assert "Qr" in self.all_components()
        self.debug.click(buttons.CORNER_BUTTON, wait=True)
        # menu
        assert "VerticalMenu" in self.all_components()
        self.debug.click(buttons.VERTICAL_MENU[1], wait=True)
        layout = self.debug.synchronize_at("AddressDetails")
        # address details
        assert "Multisig 2 of 3" in layout.screen_content()
        TR.assert_in(layout.screen_content(), "address_details__derivation_path")

        # three xpub pages with the same testing logic
        for _xpub_num in range(3):
            layout = self.debug.swipe_left(wait=True)
            layout = self.debug.swipe_left(wait=True)

        self.debug.click(buttons.CORNER_BUTTON, wait=True)
        layout = self.debug.synchronize_at("VerticalMenu")
        # menu
        self.debug.click(buttons.VERTICAL_MENU[2], wait=True)
        # cancel
        self.debug.swipe_up(wait=True)
        # really cancel
        self.debug.click(buttons.CORNER_BUTTON, wait=True)
        layout = self.debug.synchronize_at("VerticalMenu")
        # menu
        self.debug.click(buttons.CORNER_BUTTON, wait=True)
        layout = self.debug.synchronize_at("Paragraphs")
        # address
        while "PromptScreen" not in layout.all_components():
            layout = self.debug.swipe_up(wait=True)
        self.debug.synchronize_at("PromptScreen")
        # tap to confirm
        self.debug.press_yes()


class InputFlowShowXpubQRCode(InputFlowBase):
    def __init__(self, client: Client, passphrase: bool = False):
        super().__init__(client)
        self.passphrase = passphrase

    def input_flow_tt(self) -> BRGeneratorType:
        if self.passphrase:
            yield
            self.debug.press_yes()
            yield
            self.debug.press_yes()

        br = yield
        layout = self.debug.wait_layout()
        if "coinjoin" in layout.title().lower() or br.code == B.UnknownDerivationPath:
            self.debug.press_yes()
            br = yield

        self.debug.click(buttons.CORNER_BUTTON, wait=True)
        # synchronize; TODO get rid of this once we have single-global-layout
        self.debug.synchronize_at("SimplePage")

        self.debug.swipe_left(wait=True)
        self.debug.swipe_right(wait=True)
        self.debug.swipe_left(wait=True)
        self.debug.click(buttons.CORNER_BUTTON, wait=True)
        self.debug.press_no(wait=True)
        self.debug.press_no(wait=True)
        for _ in range(br.pages - 1):
            self.debug.swipe_up(wait=True)
        self.debug.press_yes()

    def input_flow_tr(self) -> BRGeneratorType:
        if self.passphrase:
            yield
            self.debug.press_right()
            yield
            self.debug.press_right()

        br = yield
        layout = self.debug.wait_layout()
        if "coinjoin" in layout.title().lower() or br.code == B.UnknownDerivationPath:
            self.debug.press_yes()
            br = yield

        # Go into details
        self.debug.press_right(wait=True)
        # Go through details and back
        self.debug.press_right(wait=True)
        self.debug.press_right(wait=True)
        self.debug.press_right(wait=True)
        self.debug.press_left(wait=True)
        self.debug.press_left(wait=True)
        assert br.pages is not None
        for _ in range(br.pages - 1):
            self.debug.press_right()
        # Confirm
        self.debug.press_middle()

    def input_flow_t3t1(self) -> BRGeneratorType:
        if self.passphrase:
            yield
            self.debug.press_yes()
            yield
            self.debug.press_yes()

        br = yield
        layout = self.debug.wait_layout()
        if "coinjoin" in layout.title().lower() or br.code == B.UnknownDerivationPath:
            self.debug.press_yes()
            br = yield
            layout = self.debug.wait_layout()

        TR.assert_in(layout.title(), "address__title_receive_address")

        self.debug.click(buttons.CORNER_BUTTON, wait=True)
        assert "VerticalMenu" in self.all_components()
        # menu
        self.debug.click(buttons.VERTICAL_MENU[0], wait=True)
        self.debug.synchronize_at("Qr")
        # qr code
        assert "Qr" in self.all_components()
        self.debug.click(buttons.CORNER_BUTTON, wait=True)
        # menu
        assert "VerticalMenu" in self.all_components()
        self.debug.click(buttons.VERTICAL_MENU[1], wait=True)
        layout = self.debug.synchronize_at("AddressDetails")
        # address details
        TR.assert_in(layout.screen_content(), "address_details__derivation_path")

        self.debug.click(buttons.CORNER_BUTTON, wait=True)
        layout = self.debug.synchronize_at("VerticalMenu")
        # menu
        self.debug.click(buttons.VERTICAL_MENU[2], wait=True)
        # cancel
        self.debug.swipe_up(wait=True)
        # really cancel
        self.debug.click(buttons.CORNER_BUTTON, wait=True)
        layout = self.debug.synchronize_at("VerticalMenu")
        # menu
        self.debug.click(buttons.CORNER_BUTTON, wait=True)
        layout = self.debug.synchronize_at("Paragraphs")
        # address
        while "PromptScreen" not in layout.all_components():
            layout = self.debug.swipe_up(wait=True)
        self.debug.synchronize_at("PromptScreen")
        # tap to confirm
        self.debug.press_yes()


class InputFlowPaymentRequestDetails(InputFlowBase):
    def __init__(self, client: Client, outputs: list[messages.TxOutputType]):
        super().__init__(client)
        self.outputs = outputs

    def input_flow_tt(self) -> BRGeneratorType:
        yield  # request to see details
        self.debug.wait_layout()
        self.debug.press_info()

        yield  # confirm first output
        assert self.outputs[0].address[:16] in self.text_content()  # type: ignore
        self.debug.press_yes()
        yield  # confirm first output
        self.debug.wait_layout()
        self.debug.press_yes()

        yield  # confirm second output
        assert self.outputs[1].address[:16] in self.text_content()  # type: ignore
        self.debug.press_yes()
        yield  # confirm second output
        self.debug.wait_layout()
        self.debug.press_yes()

        yield  # confirm transaction
        self.debug.press_yes()
        yield  # confirm transaction
        self.debug.press_yes()

    def input_flow_t3t1(self) -> BRGeneratorType:
        yield  # request to see details
        self.debug.wait_layout()
        self.debug.press_info()

        yield  # confirm first output
        assert self.outputs[0].address[:16] in self.text_content()  # type: ignore
        self.debug.press_yes()
        yield  # confirm first output
        self.debug.wait_layout()
        self.debug.press_yes()

        yield  # confirm second output
        assert self.outputs[1].address[:16] in self.text_content()  # type: ignore
        self.debug.press_yes()
        yield  # confirm second output
        self.debug.wait_layout()
        self.debug.press_yes()

        yield  # confirm transaction
        self.debug.press_yes()
        yield  # confirm transaction
        self.debug.press_yes()


class InputFlowSignTxHighFee(InputFlowBase):
    def __init__(self, client: Client):
        super().__init__(client)
        self.finished = False

    def go_through_all_screens(self, screens: list[B]) -> BRGeneratorType:
        for expected in screens:
            br = yield
            assert br.code == expected
            self.debug.press_yes()

        self.finished = True

    def input_flow_common(self) -> BRGeneratorType:
        screens = [
            B.ConfirmOutput,
            B.ConfirmOutput,
            B.FeeOverThreshold,
            B.SignTx,
        ]
        yield from self.go_through_all_screens(screens)


def sign_tx_go_to_info(client: Client) -> Generator[None, None, str]:
    yield  # confirm output
    client.debug.wait_layout()
    client.debug.press_yes()
    yield  # confirm output
    client.debug.wait_layout()
    client.debug.press_yes()

    yield  # confirm transaction
    client.debug.wait_layout()
    client.debug.press_info()

    layout = client.debug.wait_layout()
    content = layout.text_content()

    client.debug.click(buttons.CORNER_BUTTON, wait=True)

    return content


def sign_tx_go_to_info_tr(
    client: Client,
) -> Generator[None, None, str]:
    yield  # confirm address
    client.debug.wait_layout()
    client.debug.press_yes()  # CONTINUE
    yield  # confirm amount
    client.debug.wait_layout()
    client.debug.press_yes()  # CONFIRM

    screen_texts: list[str] = []

    yield  # confirm total
    layout = client.debug.wait_layout()
    if "multiple accounts" in layout.text_content().lower():
        client.debug.press_middle()
        yield

    layout = client.debug.press_right(wait=True)
    screen_texts.append(layout.text_content())

    layout = client.debug.press_right(wait=True)
    screen_texts.append(layout.text_content())

    client.debug.press_left()
    client.debug.press_left()

    return "\n".join(screen_texts)


class InputFlowSignTxInformation(InputFlowBase):
    def __init__(self, client: Client):
        super().__init__(client)

    def assert_content(self, content: str, title_path: str) -> None:
        TR.assert_in(content, title_path)
        assert "Legacy #6" in content
        TR.assert_in(content, "confirm_total__fee_rate")
        assert "71.56 sat" in content

    def input_flow_tt(self) -> BRGeneratorType:
        content = yield from sign_tx_go_to_info(self.client)
        self.assert_content(content, "confirm_total__sending_from_account")
        self.debug.press_yes()

    def input_flow_tr(self) -> BRGeneratorType:
        content = yield from sign_tx_go_to_info_tr(self.client)
        print("content", content)
        self.assert_content(content, "confirm_total__title_sending_from")
        self.debug.press_yes()

    def input_flow_t3t1(self) -> BRGeneratorType:
        content = yield from sign_tx_go_to_info(self.client)
        self.assert_content(content, "confirm_total__sending_from_account")
        self.debug.press_yes()


class InputFlowSignTxInformationMixed(InputFlowBase):
    def __init__(self, client: Client):
        super().__init__(client)

    def assert_content(self, content: str, title_path: str) -> None:
        TR.assert_in(content, title_path)
        TR.assert_in(content, "bitcoin__multiple_accounts")
        TR.assert_in(content, "confirm_total__fee_rate")
        assert "18.33 sat" in content

    def input_flow_tt(self) -> BRGeneratorType:
        # multiple accounts warning
        yield
        self.debug.press_yes()

        content = yield from sign_tx_go_to_info(self.client)
        self.assert_content(content, "confirm_total__sending_from_account")
        self.debug.press_yes()

    def input_flow_tr(self) -> BRGeneratorType:
        # multiple accounts warning
        yield
        self.debug.press_yes()

        content = yield from sign_tx_go_to_info_tr(self.client)
        self.assert_content(content, "confirm_total__title_sending_from")
        self.debug.press_yes()

    def input_flow_t3t1(self) -> BRGeneratorType:
        # multiple accounts warning
        yield
        self.debug.press_yes()

        content = yield from sign_tx_go_to_info(self.client)
        self.assert_content(content, "confirm_total__sending_from_account")
        self.debug.press_yes()


class InputFlowSignTxInformationCancel(InputFlowBase):
    def __init__(self, client: Client):
        super().__init__(client)

    def input_flow_tt(self) -> BRGeneratorType:
        yield from sign_tx_go_to_info(self.client)
        self.debug.press_no()

    def input_flow_tr(self) -> BRGeneratorType:
        yield from sign_tx_go_to_info_tr(self.client)
        self.debug.press_left()

    def input_flow_t3t1(self) -> BRGeneratorType:
        yield from sign_tx_go_to_info(self.client)
        self.debug.press_no()


class InputFlowSignTxInformationReplacement(InputFlowBase):
    def __init__(self, client: Client):
        super().__init__(client)

    def input_flow_tt(self) -> BRGeneratorType:
        yield  # confirm txid
        self.debug.press_yes()
        yield  # confirm address
        self.debug.press_yes()
        # go back to address
        self.debug.press_no()
        # confirm address
        self.debug.press_yes()
        yield  # confirm amount
        self.debug.press_yes()

        yield  # transaction summary, press info
        self.debug.click(buttons.CORNER_BUTTON, wait=True)
        self.debug.click(buttons.CORNER_BUTTON, wait=True)
        self.debug.press_yes()

    def input_flow_tr(self) -> BRGeneratorType:
        yield  # confirm txid
        self.debug.press_right()
        self.debug.press_right()
        yield  # confirm address
        self.debug.press_right()
        self.debug.press_right()
        self.debug.press_right()
        yield  # confirm amount
        self.debug.press_right()
        self.debug.press_right()
        self.debug.press_right()
        yield

    def input_flow_t3t1(self) -> BRGeneratorType:
        yield  # confirm txid
        self.debug.press_yes()
        yield  # confirm address
        self.debug.press_yes()
        # go back to address
        self.debug.press_no()
        # confirm address
        self.debug.press_yes()
        yield  # confirm amount
        self.debug.press_yes()

        yield  # transaction summary, press info
        self.debug.click(buttons.CORNER_BUTTON, wait=True)
        self.debug.click(buttons.CORNER_BUTTON, wait=True)
        self.debug.press_yes()


def lock_time_input_flow_tt(
    debug: DebugLink,
    layout_assert_func: Callable[[DebugLink, messages.ButtonRequest], None],
    double_confirm: bool = False,
) -> BRGeneratorType:
    yield  # confirm output
    debug.wait_layout()
    debug.press_yes()
    yield  # confirm output
    debug.wait_layout()
    debug.press_yes()

    br = yield  # confirm locktime
    layout_assert_func(debug, br)
    debug.press_yes()

    yield  # confirm transaction
    debug.press_yes()
    if double_confirm:
        yield  # confirm transaction
        debug.press_yes()


def lock_time_input_flow_tr(
    debug: DebugLink,
    layout_assert_func: Callable[[DebugLink, messages.ButtonRequest], None],
) -> BRGeneratorType:
    yield  # confirm address
    debug.wait_layout()
    debug.press_yes()
    yield  # confirm amount
    debug.wait_layout()
    debug.press_yes()

    br = yield  # confirm locktime
    layout_assert_func(debug, br)
    debug.press_yes()

    yield  # confirm transaction
    debug.press_yes()


class InputFlowLockTimeBlockHeight(InputFlowBase):
    def __init__(self, client: Client, block_height: str):
        super().__init__(client)
        self.block_height = block_height

    def assert_func(self, debug: DebugLink, br: messages.ButtonRequest) -> None:
        layout_text = get_text_possible_pagination(debug, br)
        TR.assert_in(layout_text, "bitcoin__locktime_set_to_blockheight")
        assert self.block_height in layout_text

    def input_flow_tt(self) -> BRGeneratorType:
        yield from lock_time_input_flow_tt(
            self.debug, self.assert_func, double_confirm=True
        )

    def input_flow_tr(self) -> BRGeneratorType:
        yield from lock_time_input_flow_tr(self.debug, self.assert_func)

    def input_flow_t3t1(self) -> BRGeneratorType:
        yield from lock_time_input_flow_tt(
            self.debug, self.assert_func, double_confirm=True
        )


class InputFlowLockTimeDatetime(InputFlowBase):
    def __init__(self, client: Client, lock_time_str: str):
        super().__init__(client)
        self.lock_time_str = lock_time_str

    def assert_func(self, debug: DebugLink, br: messages.ButtonRequest) -> None:
        layout_text = get_text_possible_pagination(debug, br)
        TR.assert_in(layout_text, "bitcoin__locktime_set_to")
        assert self.lock_time_str.replace(" ", "") in layout_text.replace(" ", "")

    def input_flow_tt(self) -> BRGeneratorType:
        yield from lock_time_input_flow_tt(self.debug, self.assert_func)

    def input_flow_tr(self) -> BRGeneratorType:
        yield from lock_time_input_flow_tr(self.debug, self.assert_func)

    def input_flow_t3t1(self) -> BRGeneratorType:
        yield from lock_time_input_flow_tt(self.debug, self.assert_func)


class InputFlowEIP712ShowMore(InputFlowBase):
    SHOW_MORE = (143, 167)

    def __init__(self, client: Client):
        super().__init__(client)
        self.same_for_all_models = True

    def _confirm_show_more(self) -> None:
        """Model-specific, either clicks a screen or presses a button."""
        if self.model() in (models.T2T1, models.T3T1):
            self.debug.click(self.SHOW_MORE)
        elif self.model() is models.T2B1:
            self.debug.press_right()

    def input_flow_common(self) -> BRGeneratorType:
        """Triggers show more wherever possible"""
        yield  # confirm address
        self.debug.press_yes()

        yield  # confirm domain
        self.debug.wait_layout()
        self._confirm_show_more()

        # confirm domain properties
        for _ in range(4):
            yield from swipe_if_necessary(self.debug)  # EIP712 DOMAIN
            self.debug.press_yes()

        yield  # confirm message
        self.debug.wait_layout()
        self._confirm_show_more()

        yield  # confirm message.from
        self.debug.wait_layout()
        self._confirm_show_more()

        # confirm message.from properties
        for _ in range(2):
            yield from swipe_if_necessary(self.debug)
            self.debug.press_yes()

        yield  # confirm message.to
        self.debug.wait_layout()
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
    def __init__(self, client: Client):
        super().__init__(client)

    def input_flow_common(self) -> BRGeneratorType:
        """Clicks cancelling button"""
        yield  # confirm address
        self.debug.press_yes()

        yield  # confirm domain
        self.debug.press_no()


class InputFlowEthereumSignTxShowFeeInfo(InputFlowBase):
    def __init__(self, client: Client):
        super().__init__(client)

    def input_flow_common(self) -> BRGeneratorType:
        yield from self.ETH.confirm_tx(info=True)


class InputFlowEthereumSignTxGoBackFromSummary(InputFlowBase):
    def __init__(self, client: Client):
        super().__init__(client)

    def input_flow_common(self) -> BRGeneratorType:
        yield from self.ETH.confirm_tx(go_back_from_summary=True)


class InputFlowEthereumSignTxDataSkip(InputFlowBase):
    def __init__(self, client: Client, cancel: bool = False):
        super().__init__(client)
        self.cancel = cancel

    def input_flow_common(self) -> BRGeneratorType:
        yield from self.ETH.confirm_data()
        yield from self.ETH.confirm_tx(cancel=self.cancel)


class InputFlowEthereumSignTxDataScrollDown(InputFlowBase):
    def __init__(self, client: Client, cancel: bool = False):
        super().__init__(client)
        self.cancel = cancel

    def input_flow_common(self) -> BRGeneratorType:
        yield from self.ETH.confirm_data(info=True)
        yield from self.ETH.paginate_data()
        if self.cancel:
            yield from self.ETH.confirm_data(cancel=True)
        else:
            yield from self.ETH.confirm_data()
            yield from self.ETH.confirm_tx()


class InputFlowEthereumSignTxDataGoBack(InputFlowBase):
    def __init__(self, client: Client, cancel: bool = False):
        super().__init__(client)
        self.cancel = cancel

    def input_flow_common(self) -> BRGeneratorType:
        yield from self.ETH.confirm_data(info=True)
        yield from self.ETH.paginate_data_go_back()
        if self.cancel:
            yield from self.ETH.confirm_data(cancel=True)
        else:
            yield from self.ETH.confirm_data()
            yield from self.ETH.confirm_tx()


class InputFlowEthereumSignTxStaking(InputFlowBase):
    def __init__(self, client: Client):
        super().__init__(client)

    def input_flow_common(self) -> BRGeneratorType:
        yield from self.ETH.confirm_tx_staking(info=True)


def get_mnemonic_and_confirm_success(
    debug: DebugLink,
) -> Generator[None, "messages.ButtonRequest", str]:
    # mnemonic phrases
    mnemonic = yield from read_and_confirm_mnemonic(debug)

    br = yield  # confirm recovery seed check
    assert br.code == B.Success
    debug.press_yes()

    br = yield  # confirm success
    assert br.code == B.Success
    debug.press_yes()

    assert mnemonic is not None
    return mnemonic


class InputFlowBip39Backup(InputFlowBase):
    def __init__(self, client: Client):
        super().__init__(client)
        self.mnemonic = None

    def input_flow_common(self) -> BRGeneratorType:
        # 1. Confirm Reset
        yield from click_through(self.debug, screens=1, code=B.ResetDevice)

        # mnemonic phrases and rest
        self.mnemonic = yield from get_mnemonic_and_confirm_success(self.debug)


class InputFlowBip39ResetBackup(InputFlowBase):
    def __init__(self, client: Client):
        super().__init__(client)
        self.mnemonic = None

    # NOTE: same as above, just two more YES
    def input_flow_tt(self) -> BRGeneratorType:
        # 1. Confirm Reset
        # 2. Backup your seed
        # 3. Confirm warning
        yield from click_through(self.debug, screens=3, code=B.ResetDevice)

        # mnemonic phrases and rest
        self.mnemonic = yield from get_mnemonic_and_confirm_success(self.debug)

    def input_flow_tr(self) -> BRGeneratorType:
        # 1. Confirm Reset
        # 2. Backup your seed
        # 3. Confirm warning
        yield from click_through(self.debug, screens=3, code=B.ResetDevice)

        # mnemonic phrases and rest
        self.mnemonic = yield from get_mnemonic_and_confirm_success(self.debug)

    def input_flow_t3t1(self) -> BRGeneratorType:
        # 1. Confirm Reset x3
        # 2. Backup your seed
        # 3. Confirm warning
        yield from click_through(self.debug, screens=3, code=B.ResetDevice)

        # mnemonic phrases and rest
        self.mnemonic = yield from get_mnemonic_and_confirm_success(self.debug)


class InputFlowBip39ResetPIN(InputFlowBase):
    def __init__(self, client: Client):
        super().__init__(client)
        self.mnemonic = None

    def input_flow_common(self) -> BRGeneratorType:
        br = yield  # Confirm Reset
        assert br.code == B.ResetDevice
        self.debug.press_yes()

        yield from self.PIN.setup_new_pin("654")

        br = yield  # Confirm entropy
        assert br.code == B.ResetDevice
        self.debug.press_yes()

        br = yield  # Backup your seed
        assert br.code == B.ResetDevice
        self.debug.press_yes()

        br = yield  # Confirm warning
        assert br.code == B.ResetDevice
        self.debug.press_yes()

        # mnemonic phrases
        self.mnemonic = yield from read_and_confirm_mnemonic(self.debug)

        br = yield  # confirm recovery seed check
        assert br.code == B.Success
        self.debug.press_yes()

        br = yield  # confirm success
        assert br.code == B.Success
        self.debug.press_yes()


class InputFlowBip39ResetFailedCheck(InputFlowBase):
    def __init__(self, client: Client):
        super().__init__(client)
        self.mnemonic = None

    def input_flow_common(self) -> BRGeneratorType:
        # 1. Confirm Reset
        # 2. Backup your seed
        # 3. Confirm warning
        yield from click_through(self.debug, screens=3, code=B.ResetDevice)

        # mnemonic phrases, wrong answer
        self.mnemonic = yield from read_and_confirm_mnemonic(
            self.debug, choose_wrong=True
        )

        br = yield  # warning screen
        assert br.code == B.ResetDevice
        self.debug.press_yes()

        # mnemonic phrases
        self.mnemonic = yield from read_and_confirm_mnemonic(self.debug)

        br = yield  # confirm recovery seed check
        assert br.code == B.Success
        self.debug.press_yes()

        br = yield  # confirm success
        assert br.code == B.Success
        self.debug.press_yes()


def load_5_shares(
    debug: DebugLink,
) -> Generator[None, "messages.ButtonRequest", list[str]]:
    mnemonics: list[str] = []

    for _ in range(5):
        # Phrase screen
        mnemonic = yield from read_and_confirm_mnemonic(debug)
        assert mnemonic is not None
        mnemonics.append(mnemonic)

        br = yield  # Confirm continue to next
        assert br.code == B.Success
        debug.press_yes()

    return mnemonics


class InputFlowSlip39BasicBackup(InputFlowBase):
    def __init__(self, client: Client, click_info: bool):
        super().__init__(client)
        self.mnemonics: list[str] = []
        self.click_info = click_info

    def input_flow_tt(self) -> BRGeneratorType:
        yield  # 1. Checklist
        self.debug.press_yes()
        if self.click_info:
            yield from click_info_button_tt(self.debug)
        yield  # 2. Number of shares (5)
        self.debug.press_yes()
        yield  # 3. Checklist
        self.debug.press_yes()
        if self.click_info:
            yield from click_info_button_tt(self.debug)
        yield  # 4. Threshold (3)
        self.debug.press_yes()
        yield  # 5. Checklist
        self.debug.press_yes()
        yield  # 6. Confirm show seeds
        self.debug.press_yes()

        # Mnemonic phrases
        self.mnemonics = yield from load_5_shares(self.debug)

        br = yield  # Confirm backup
        assert br.code == B.Success
        self.debug.press_yes()

    def input_flow_tr(self) -> BRGeneratorType:
        yield  # 1. Checklist
        self.debug.press_yes()
        yield  # 1.5 Number of shares info
        self.debug.press_yes()
        yield  # 2. Number of shares (5)
        self.debug.input("5")
        yield  # 3. Checklist
        self.debug.press_yes()
        yield  # 3.5 Threshold info
        self.debug.press_yes()
        yield  # 4. Threshold (3)
        self.debug.input("3")
        yield  # 5. Checklist
        self.debug.press_yes()
        yield  # 6. Confirm show seeds
        self.debug.press_yes()

        # Mnemonic phrases
        self.mnemonics = yield from load_5_shares(self.debug)

        br = yield  # Confirm backup
        assert br.code == B.Success
        self.debug.press_yes()

    def input_flow_t3t1(self) -> BRGeneratorType:
        yield  # 1. Checklist
        self.debug.press_yes()
        if self.click_info:
            yield from click_info_button_tt(self.debug)
        yield  # 2. Number of shares (5)
        self.debug.press_yes()
        yield  # 3. Checklist
        self.debug.press_yes()
        if self.click_info:
            yield from click_info_button_tt(self.debug)
        yield  # 4. Threshold (3)
        self.debug.press_yes()
        yield  # 5. Checklist
        self.debug.press_yes()
        yield  # 6. Confirm show seeds
        self.debug.press_yes()

        # Mnemonic phrases
        self.mnemonics = yield from load_5_shares(self.debug)

        br = yield  # Confirm backup
        assert br.code == B.Success
        self.debug.press_yes()


class InputFlowSlip39BasicResetRecovery(InputFlowBase):
    def __init__(self, client: Client):
        super().__init__(client)
        self.mnemonics: list[str] = []

    def input_flow_tt(self) -> BRGeneratorType:
        # 1. Confirm Reset
        # 2. Backup your seed
        # 3. Confirm warning
        # 4. shares info
        # 5. Set & Confirm number of shares
        # 6. threshold info
        # 7. Set & confirm threshold value
        # 8. Confirm show seeds
        yield from click_through(self.debug, screens=8, code=B.ResetDevice)

        # Mnemonic phrases
        self.mnemonics = yield from load_5_shares(self.debug)

        br = yield  # safety warning
        assert br.code == B.Success
        self.debug.press_yes()

    def input_flow_tr(self) -> BRGeneratorType:
        yield  # Confirm Reset
        self.debug.press_yes()
        yield  # Backup your seed
        self.debug.press_yes()
        yield  # Checklist
        self.debug.press_yes()
        yield  # Number of shares info
        self.debug.press_yes()
        yield  # Number of shares (5)
        self.debug.input("5")
        yield  # Checklist
        self.debug.press_yes()
        yield  # Threshold info
        self.debug.press_yes()
        yield  # Threshold (3)
        self.debug.input("3")
        yield  # Checklist
        self.debug.press_yes()
        yield  # Confirm show seeds
        self.debug.press_yes()

        # Mnemonic phrases
        self.mnemonics = yield from load_5_shares(self.debug)

        br = yield  # Confirm backup
        assert br.code == B.Success
        self.debug.press_yes()

    def input_flow_t3t1(self) -> BRGeneratorType:
        # 1. Confirm Reset
        # 2. Backup your seed
        # 3. Confirm warning
        # 4. shares info
        # 5. Set & Confirm number of shares
        # 6. threshold info
        # 7. Set & confirm threshold value
        # 8. Confirm show seeds
        yield from click_through(self.debug, screens=8, code=B.ResetDevice)

        # Mnemonic phrases
        self.mnemonics = yield from load_5_shares(self.debug)

        br = yield  # safety warning
        assert br.code == B.Success
        self.debug.press_yes()


def load_5_groups_5_shares(
    debug: DebugLink,
) -> Generator[None, "messages.ButtonRequest", list[str]]:
    mnemonics: list[str] = []

    for _g in range(5):
        for _s in range(5):
            # Phrase screen
            mnemonic = yield from read_and_confirm_mnemonic(debug)
            assert mnemonic is not None
            mnemonics.append(mnemonic)
            # Confirm continue to next
            yield from swipe_if_necessary(debug, B.Success)
            debug.press_yes()

    return mnemonics


class InputFlowSlip39AdvancedBackup(InputFlowBase):
    def __init__(self, client: Client, click_info: bool):
        super().__init__(client)
        self.mnemonics: list[str] = []
        self.click_info = click_info

    def input_flow_tt(self) -> BRGeneratorType:
        yield  # 1. Checklist
        self.debug.press_yes()
        if self.click_info:
            yield from click_info_button_tt(self.debug)
        yield  # 2. Set and confirm group count
        self.debug.press_yes()
        yield  # 3. Checklist
        self.debug.press_yes()
        if self.click_info:
            yield from click_info_button_tt(self.debug)
        yield  # 4. Set and confirm group threshold
        self.debug.press_yes()
        yield  # 5. Checklist
        self.debug.press_yes()
        for _ in range(5):  # for each of 5 groups
            if self.click_info:
                yield from click_info_button_tt(self.debug)
            yield  # Set & Confirm number of shares
            self.debug.press_yes()
            if self.click_info:
                yield from click_info_button_tt(self.debug)
            yield  # Set & confirm share threshold value
            self.debug.press_yes()
        yield  # Confirm show seeds
        self.debug.press_yes()

        # Mnemonic phrases - show & confirm shares for all groups
        self.mnemonics = yield from load_5_groups_5_shares(self.debug)

        br = yield  # Confirm backup
        assert br.code == B.Success
        self.debug.press_yes()

    def input_flow_tr(self) -> BRGeneratorType:
        yield  # 1. Checklist
        self.debug.press_yes()
        yield  # 2. Set and confirm group count
        self.debug.input("5")
        yield  # 3. Checklist
        self.debug.press_yes()
        yield  # 4. Set and confirm group threshold
        self.debug.input("3")
        yield  # 5. Checklist
        self.debug.press_yes()
        for _ in range(5):  # for each of 5 groups
            yield  # Number of shares info
            self.debug.press_yes()
            yield  # Number of shares (5)
            self.debug.input("5")
            yield  # Threshold info
            self.debug.press_yes()
            yield  # Threshold (3)
            self.debug.input("3")
        yield  # Confirm show seeds
        self.debug.press_yes()

        # Mnemonic phrases - show & confirm shares for all groups
        self.mnemonics = yield from load_5_groups_5_shares(self.debug)

        br = yield  # Confirm backup
        assert br.code == B.Success
        self.debug.press_yes()

    def input_flow_t3t1(self) -> BRGeneratorType:
        yield  # 1. Checklist
        self.debug.press_yes()
        if self.click_info:
            yield from click_info_button_tt(self.debug)
        yield  # 2. Set and confirm group count
        self.debug.press_yes()
        yield  # 3. Checklist
        self.debug.press_yes()
        if self.click_info:
            yield from click_info_button_tt(self.debug)
        yield  # 4. Set and confirm group threshold
        self.debug.press_yes()
        yield  # 5. Checklist
        self.debug.press_yes()
        for _ in range(5):  # for each of 5 groups
            if self.click_info:
                yield from click_info_button_tt(self.debug)
            yield  # Set & Confirm number of shares
            self.debug.press_yes()
            if self.click_info:
                yield from click_info_button_tt(self.debug)
            yield  # Set & confirm share threshold value
            self.debug.press_yes()
        yield  # Confirm show seeds
        self.debug.press_yes()

        # Mnemonic phrases - show & confirm shares for all groups
        self.mnemonics = yield from load_5_groups_5_shares(self.debug)

        br = yield  # Confirm backup
        assert br.code == B.Success
        self.debug.press_yes()


class InputFlowSlip39AdvancedResetRecovery(InputFlowBase):
    def __init__(self, client: Client, click_info: bool):
        super().__init__(client)
        self.mnemonics: list[str] = []
        self.click_info = click_info

    def input_flow_tt(self) -> BRGeneratorType:
        # 1. Confirm Reset
        # 2. Backup your seed
        # 3. Confirm warning
        # 4. shares info
        # 5. Set & Confirm number of groups
        # 6. threshold info
        # 7. Set & confirm group threshold value
        # 8-17: for each of 5 groups:
        #   1. Set & Confirm number of shares
        #   2. Set & confirm share threshold value
        # 18. Confirm show seeds
        yield from click_through(self.debug, screens=18, code=B.ResetDevice)

        # Mnemonic phrases - show & confirm shares for all groups
        self.mnemonics = yield from load_5_groups_5_shares(self.debug)

        br = yield  # safety warning
        assert br.code == B.Success
        self.debug.press_yes()

    def input_flow_tr(self) -> BRGeneratorType:
        yield  # Wallet backup
        self.debug.press_yes()
        yield  # Wallet creation
        self.debug.press_yes()
        yield  # Checklist
        self.debug.press_yes()
        yield  # Set and confirm group count
        self.debug.input("5")
        yield  # Checklist
        self.debug.press_yes()
        yield  # Set and confirm group threshold
        self.debug.input("3")
        yield  # Checklist
        self.debug.press_yes()
        for _ in range(5):  # for each of 5 groups
            yield  # Number of shares info
            self.debug.press_yes()
            yield  # Number of shares (5)
            self.debug.input("5")
            yield  # Threshold info
            self.debug.press_yes()
            yield  # Threshold (3)
            self.debug.input("3")
        yield  # Confirm show seeds
        self.debug.press_yes()

        # Mnemonic phrases - show & confirm shares for all groups
        self.mnemonics = yield from load_5_groups_5_shares(self.debug)

        br = yield  # safety warning
        assert br.code == B.Success
        self.debug.press_yes()

    def input_flow_t3t1(self) -> BRGeneratorType:
        # 1. Confirm Reset
        # 2. Backup your seed
        # 3. Confirm warning
        # 4. shares info
        # 5. Set & Confirm number of groups
        # 6. threshold info
        # 7. Set & confirm group threshold value
        # 8-17: for each of 5 groups:
        #   1. Set & Confirm number of shares
        #   2. Set & confirm share threshold value
        # 18. Confirm show seeds
        yield from click_through(self.debug, screens=18, code=B.ResetDevice)

        # Mnemonic phrases - show & confirm shares for all groups
        self.mnemonics = yield from load_5_groups_5_shares(self.debug)

        br = yield  # safety warning
        assert br.code == B.Success
        self.debug.press_yes()


class InputFlowBip39RecoveryDryRun(InputFlowBase):
    def __init__(self, client: Client, mnemonic: list[str], mismatch: bool = False):
        super().__init__(client)
        self.mnemonic = mnemonic
        self.mismatch = mismatch

    def input_flow_common(self) -> BRGeneratorType:
        yield from self.REC.confirm_dry_run()
        yield from self.REC.setup_bip39_recovery(len(self.mnemonic))
        yield from self.REC.input_mnemonic(self.mnemonic)
        if self.mismatch:
            yield from self.REC.warning_bip39_dryrun_mismatch()
        else:
            yield from self.REC.success_bip39_dry_run_valid()


class InputFlowBip39RecoveryDryRunInvalid(InputFlowBase):
    def __init__(self, client: Client):
        super().__init__(client)
        self.invalid_mnemonic = ["stick"] * 12

    def input_flow_common(self) -> BRGeneratorType:
        yield from self.REC.confirm_dry_run()
        yield from self.REC.setup_bip39_recovery(len(self.invalid_mnemonic))
        yield from self.REC.input_mnemonic(self.invalid_mnemonic)
        yield from self.REC.warning_invalid_recovery_seed()

        yield
        self.client.cancel()


class InputFlowBip39Recovery(InputFlowBase):
    def __init__(self, client: Client, mnemonic: list[str], pin: str | None = None):
        super().__init__(client)
        self.mnemonic = mnemonic
        self.pin = pin

    def input_flow_common(self) -> BRGeneratorType:
        yield from self.REC.confirm_recovery()
        if self.pin is not None:
            yield from self.PIN.setup_new_pin(self.pin)
        yield from self.REC.setup_bip39_recovery(len(self.mnemonic))
        yield from self.REC.input_mnemonic(self.mnemonic)
        yield from self.REC.success_wallet_recovered()


class InputFlowSlip39AdvancedRecoveryDryRun(InputFlowBase):
    def __init__(self, client: Client, shares: list[str], mismatch: bool = False):
        super().__init__(client)
        self.shares = shares
        self.mismatch = mismatch
        self.word_count = len(shares[0].split(" "))

    def input_flow_common(self) -> BRGeneratorType:
        yield from self.REC.confirm_dry_run()
        yield from self.REC.setup_slip39_recovery(self.word_count)
        yield from self.REC.input_all_slip39_shares(self.shares, has_groups=True)
        if self.mismatch:
            yield from self.REC.warning_slip39_dryrun_mismatch()
        else:
            yield from self.REC.success_slip39_dryrun_valid()


class InputFlowSlip39AdvancedRecovery(InputFlowBase):
    def __init__(self, client: Client, shares: list[str], click_info: bool):
        super().__init__(client)
        self.shares = shares
        self.click_info = click_info
        self.word_count = len(shares[0].split(" "))

    def input_flow_common(self) -> BRGeneratorType:
        yield from self.REC.confirm_recovery()
        yield from self.REC.setup_slip39_recovery(self.word_count)
        yield from self.REC.input_all_slip39_shares(
            self.shares, has_groups=True, click_info=self.click_info
        )
        yield from self.REC.success_wallet_recovered()


class InputFlowSlip39AdvancedRecoveryAbort(InputFlowBase):
    def __init__(self, client: Client):
        super().__init__(client)

    def input_flow_common(self) -> BRGeneratorType:
        yield from self.REC.confirm_recovery()
        if self.model() in (models.T2T1, models.T3T1):
            yield from self.REC.input_number_of_words(20)
        yield from self.REC.abort_recovery(True)


class InputFlowSlip39AdvancedRecoveryNoAbort(InputFlowBase):
    def __init__(self, client: Client, shares: list[str]):
        super().__init__(client)
        self.shares = shares
        self.word_count = len(shares[0].split(" "))

    def input_flow_common(self) -> BRGeneratorType:
        yield from self.REC.confirm_recovery()
        if self.model() in (models.T2T1, models.T3T1):
            yield from self.REC.input_number_of_words(self.word_count)
            yield from self.REC.abort_recovery(False)
        else:
            yield from self.REC.abort_recovery(False)
            yield from self.REC.tr_recovery_homescreen()
            yield from self.REC.input_number_of_words(self.word_count)
        yield from self.REC.enter_any_share()
        yield from self.REC.input_all_slip39_shares(self.shares, has_groups=True)
        yield from self.REC.success_wallet_recovered()


class InputFlowSlip39AdvancedRecoveryThresholdReached(InputFlowBase):
    def __init__(
        self,
        client: Client,
        first_share: list[str],
        second_share: list[str],
    ):
        super().__init__(client)
        self.first_share = first_share
        self.second_share = second_share

    def input_flow_common(self) -> BRGeneratorType:
        yield from self.REC.confirm_recovery()
        yield from self.REC.setup_slip39_recovery(len(self.first_share))
        yield from self.REC.input_mnemonic(self.first_share)
        yield from self.REC.success_share_group_entered()
        yield from self.REC.success_more_shares_needed()
        yield from self.REC.input_mnemonic(self.second_share)
        yield from self.REC.warning_group_threshold_reached()

        yield
        self.client.cancel()


class InputFlowSlip39AdvancedRecoveryShareAlreadyEntered(InputFlowBase):
    def __init__(
        self,
        client: Client,
        first_share: list[str],
        second_share: list[str],
    ):
        super().__init__(client)
        self.first_share = first_share
        self.second_share = second_share

    def input_flow_common(self) -> BRGeneratorType:
        yield from self.REC.confirm_recovery()
        yield from self.REC.setup_slip39_recovery(len(self.first_share))
        yield from self.REC.input_mnemonic(self.first_share)
        yield from self.REC.success_share_group_entered()
        yield from self.REC.success_more_shares_needed()
        yield from self.REC.input_mnemonic(self.second_share)
        yield from self.REC.warning_share_already_entered()

        yield
        self.client.cancel()


class InputFlowSlip39BasicRecoveryDryRun(InputFlowBase):
    def __init__(self, client: Client, shares: list[str], mismatch: bool = False):
        super().__init__(client)
        self.shares = shares
        self.mismatch = mismatch
        self.word_count = len(shares[0].split(" "))

    def input_flow_common(self) -> BRGeneratorType:
        yield from self.REC.confirm_dry_run()
        yield from self.REC.setup_slip39_recovery(self.word_count)
        yield from self.REC.input_all_slip39_shares(self.shares)
        if self.mismatch:
            yield from self.REC.warning_slip39_dryrun_mismatch()
        else:
            yield from self.REC.success_slip39_dryrun_valid()


class InputFlowSlip39BasicRecovery(InputFlowBase):
    def __init__(self, client: Client, shares: list[str], pin: str | None = None):
        super().__init__(client)
        self.shares = shares
        self.pin = pin
        self.word_count = len(shares[0].split(" "))

    def input_flow_common(self) -> BRGeneratorType:
        yield from self.REC.confirm_recovery()
        if self.pin is not None:
            yield from self.PIN.setup_new_pin(self.pin)
        yield from self.REC.setup_slip39_recovery(self.word_count)
        yield from self.REC.input_all_slip39_shares(self.shares)
        yield from self.REC.success_wallet_recovered()


class InputFlowSlip39BasicRecoveryAbort(InputFlowBase):
    def __init__(self, client: Client):
        super().__init__(client)

    def input_flow_common(self) -> BRGeneratorType:
        yield from self.REC.confirm_recovery()
        if self.model() in (models.T2T1, models.T3T1):
            yield from self.REC.input_number_of_words(20)
        yield from self.REC.abort_recovery(True)


class InputFlowSlip39BasicRecoveryNoAbort(InputFlowBase):
    def __init__(self, client: Client, shares: list[str]):
        super().__init__(client)
        self.shares = shares
        self.word_count = len(shares[0].split(" "))

    def input_flow_common(self) -> BRGeneratorType:
        yield from self.REC.confirm_recovery()

        if self.model() in (models.T2T1, models.T3T1):
            yield from self.REC.input_number_of_words(self.word_count)
            yield from self.REC.abort_recovery(False)
        else:
            yield from self.REC.abort_recovery(False)
            yield from self.REC.tr_recovery_homescreen()
            yield from self.REC.input_number_of_words(self.word_count)

        yield from self.REC.enter_any_share()
        yield from self.REC.input_all_slip39_shares(self.shares)
        yield from self.REC.success_wallet_recovered()


class InputFlowSlip39BasicRecoveryInvalidFirstShare(InputFlowBase):
    def __init__(self, client: Client):
        super().__init__(client)
        self.first_invalid = ["slush"] * 20
        self.second_invalid = ["slush"] * 33

    def input_flow_common(self) -> BRGeneratorType:
        yield from self.REC.confirm_recovery()
        yield from self.REC.setup_slip39_recovery(len(self.first_invalid))
        yield from self.REC.input_mnemonic(self.first_invalid)
        yield from self.REC.warning_invalid_recovery_share()
        yield from self.REC.setup_slip39_recovery(len(self.second_invalid))
        yield from self.REC.input_mnemonic(self.second_invalid)
        yield from self.REC.warning_invalid_recovery_share()

        yield
        self.client.cancel()


class InputFlowSlip39BasicRecoveryInvalidSecondShare(InputFlowBase):
    def __init__(self, client: Client, shares: list[str]):
        super().__init__(client)
        self.shares = shares
        self.first_share = shares[0].split(" ")
        self.invalid_share = self.first_share[:3] + ["slush"] * 17
        self.second_share = shares[1].split(" ")

    def input_flow_common(self) -> BRGeneratorType:
        yield from self.REC.confirm_recovery()
        yield from self.REC.setup_slip39_recovery(len(self.first_share))
        yield from self.REC.input_mnemonic(self.first_share)
        yield from self.REC.success_more_shares_needed(2)
        yield from self.REC.input_mnemonic(self.invalid_share)
        yield from self.REC.warning_invalid_recovery_share()
        yield from self.REC.input_mnemonic(self.second_share)
        yield from self.REC.success_more_shares_needed(1)

        yield
        self.client.cancel()


class InputFlowSlip39BasicRecoveryWrongNthWord(InputFlowBase):
    def __init__(self, client: Client, share: list[str], nth_word: int):
        super().__init__(client)
        self.share = share
        self.nth_word = nth_word
        # Invalid share - just enough words to trigger the warning
        self.modified_share = share[:nth_word] + [self.share[-1]]

    def input_flow_common(self) -> BRGeneratorType:
        yield from self.REC.confirm_recovery()
        yield from self.REC.setup_slip39_recovery(len(self.share))
        yield from self.REC.input_mnemonic(self.share)
        yield from self.REC.success_more_shares_needed()
        yield from self.REC.input_mnemonic(self.modified_share)
        yield from self.REC.warning_share_from_another_shamir()

        yield
        self.client.cancel()


class InputFlowSlip39BasicRecoverySameShare(InputFlowBase):
    def __init__(self, client: Client, share: list[str]):
        super().__init__(client)
        self.share = share
        # Second duplicate share - only 4 words are needed to verify it
        self.duplicate_share = self.share[:4]

    def input_flow_common(self) -> BRGeneratorType:
        yield from self.REC.confirm_recovery()
        yield from self.REC.setup_slip39_recovery(len(self.share))
        yield from self.REC.input_mnemonic(self.share)
        yield from self.REC.success_more_shares_needed()
        yield from self.REC.input_mnemonic(self.duplicate_share)
        yield from self.REC.warning_share_already_entered()

        yield
        self.client.cancel()


class InputFlowResetSkipBackup(InputFlowBase):
    def __init__(self, client: Client):
        super().__init__(client)

    def input_flow_common(self) -> BRGeneratorType:
        yield from self.BAK.confirm_new_wallet()
        yield  # Skip Backup
        info_path = (
            "backup__new_wallet_created"
            if self.model() is models.T2B1
            else "backup__new_wallet_successfully_created"
        )
        TR.assert_in(self.text_content(), info_path)
        if self.model() is models.T2B1:
            self.debug.press_right()
        self.debug.press_no()
        yield  # Confirm skip backup
        TR.assert_in(self.text_content(), "backup__want_to_skip")
        self.debug.press_no()
