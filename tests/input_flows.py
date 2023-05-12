"""
Central place for defining all input flows for the device tests.

Each model has potentially its own input flow, and in most cases
we need to distinguish between them. Doing it at one place
offers a better overview of the differences and makes it easier
to maintain. The whole `device_tests` folder can then focus
only on the actual tests and data-assertions, not on the lower-level
input flow details.
"""

import time
from typing import Callable, Generator, Optional

from trezorlib import messages
from trezorlib.debuglink import (
    DebugLink,
    LayoutContent,
    TrezorClientDebugLink as Client,
    multipage_content,
)

from . import buttons
from .common import (
    check_pin_backoff_time,
    click_info_button,
    click_through,
    read_and_confirm_mnemonic,
    recovery_enter_shares,
)

GeneratorType = Generator[None, messages.ButtonRequest, None]

B = messages.ButtonRequestType


def swipe_if_necessary(
    debug: DebugLink, br_code: Optional[messages.ButtonRequestType] = None
) -> GeneratorType:
    br = yield
    if br_code is not None:
        assert br.code == br_code
    if br.pages is not None:
        for _ in range(br.pages - 1):
            debug.swipe_up()


class InputFlowBase:
    def __init__(self, client: Client):
        self.client = client
        self.debug: DebugLink = client.debug
        self.layout = client.debug.wait_layout

    def model(self) -> Optional[str]:
        return self.client.features.model

    def get(self) -> Callable[[], GeneratorType]:
        self.client.watch_layout(True)

        # There could be one common input flow for all models
        if hasattr(self, "input_flow_common"):
            return getattr(self, "input_flow_common")
        elif self.model() == "T":
            return self.input_flow_tt
        elif self.model() == "R":
            return self.input_flow_tr
        else:
            raise ValueError("Unknown model")

    def input_flow_tt(self) -> GeneratorType:
        """Special for TT"""
        raise NotImplementedError

    def input_flow_tr(self) -> GeneratorType:
        """Special for TR"""
        raise NotImplementedError


class InputFlowSetupDevicePINWIpeCode(InputFlowBase):
    def __init__(self, client: Client, pin: str, wipe_code: str):
        super().__init__(client)
        self.pin = pin
        self.wipe_code = wipe_code

    def input_flow_tt(self) -> GeneratorType:
        yield  # do you want to set/change the wipe code?
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

    def input_flow_tt(self) -> GeneratorType:
        yield  # do you want to set/change the pin/wipe code?
        self.debug.press_yes()

        def input_two_different_pins():
            yield  # enter new PIN/wipe_code
            self.debug.input(self.first_code)
            yield  # enter new PIN/wipe_code again (but different)
            self.debug.input(self.second_code)

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

    def input_flow_tt(self) -> GeneratorType:
        yield  # do you want to change pin?
        self.debug.press_yes()
        yield  # enter current pin
        self.debug.input(self.current_pin)

        yield  # enter new pin
        self.debug.input(self.new_pin_1)
        yield  # enter new pin again (but different)
        self.debug.input(self.new_pin_2)

        yield  # PIN mismatch
        self.debug.press_yes()  # try again

        # failed retry
        yield  # enter current pin again
        self.client.cancel()


class InputFlowWrongPIN(InputFlowBase):
    def __init__(self, client: Client, wrong_pin: str):
        super().__init__(client)
        self.wrong_pin = wrong_pin

    def input_flow_tt(self) -> GeneratorType:
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

    def input_flow_tt(self) -> GeneratorType:
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

    def input_flow_tt(self) -> GeneratorType:
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


class InputFlowShowAddressQRCode(InputFlowBase):
    def __init__(self, client: Client):
        super().__init__(client)

    def input_flow_tt(self) -> GeneratorType:
        yield
        self.debug.click(buttons.CORNER_BUTTON, wait=True)
        # synchronize; TODO get rid of this once we have single-global-layout
        self.debug.synchronize_at("HorizontalPage")

        self.debug.swipe_left(wait=True)
        self.debug.swipe_right(wait=True)
        self.debug.swipe_left(wait=True)
        self.debug.click(buttons.CORNER_BUTTON, wait=True)
        self.debug.press_no(wait=True)
        self.debug.press_no(wait=True)
        self.debug.press_yes()


class InputFlowShowAddressQRCodeCancel(InputFlowBase):
    def __init__(self, client: Client):
        super().__init__(client)

    def input_flow_tt(self) -> GeneratorType:
        yield
        self.debug.click(buttons.CORNER_BUTTON, wait=True)
        # synchronize; TODO get rid of this once we have single-global-layout
        self.debug.synchronize_at("HorizontalPage")

        self.debug.swipe_left(wait=True)
        self.debug.click(buttons.CORNER_BUTTON, wait=True)
        self.debug.press_no(wait=True)
        self.debug.press_yes()


class InputFlowShowMultisigXPUBs(InputFlowBase):
    def __init__(self, client: Client, address: str, xpubs: list[str], index: int):
        super().__init__(client)
        self.address = address
        self.xpubs = xpubs
        self.index = index

    def input_flow_tt(self) -> GeneratorType:
        yield  # show address
        layout = self.debug.wait_layout()
        assert "RECEIVE ADDRESS\n(MULTISIG)" == layout.title()
        assert layout.text_content().replace(" ", "") == self.address

        self.debug.click(buttons.CORNER_BUTTON)
        assert "Qr" in self.debug.wait_layout().all_components()

        layout = self.debug.swipe_left(wait=True)
        # address details
        assert "Multisig 2 of 3" in layout.screen_content()
        assert "Derivation path:" in layout.screen_content()

        # Three xpub pages with the same testing logic
        for xpub_num in range(3):
            expected_title = f"MULTISIG XPUB #{xpub_num + 1}\n" + (
                "(YOURS)" if self.index == xpub_num else "(COSIGNER)"
            )
            layout = self.debug.swipe_left(wait=True)
            assert expected_title == layout.title()
            content = layout.text_content().replace(" ", "")
            assert self.xpubs[xpub_num] in content

        self.debug.click(buttons.CORNER_BUTTON, wait=True)
        # show address
        self.debug.press_no(wait=True)
        # address mismatch
        self.debug.press_no(wait=True)
        # show address
        self.debug.press_yes()


class InputFlowPaymentRequestDetails(InputFlowBase):
    def __init__(self, client: Client, outputs: list[messages.TxOutputType]):
        super().__init__(client)
        self.outputs = outputs

    def input_flow_tt(self) -> GeneratorType:
        yield  # request to see details
        self.debug.wait_layout()
        self.debug.press_info()

        yield  # confirm first output
        assert self.outputs[0].address[:16] in self.layout().text_content()
        self.debug.press_yes()
        yield  # confirm first output
        self.debug.wait_layout()
        self.debug.press_yes()

        yield  # confirm second output
        assert self.outputs[1].address[:16] in self.layout().text_content()
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

    def go_through_all_screens(self, screens: list[B]) -> GeneratorType:
        for expected in screens:
            br = yield
            assert br.code == expected
            self.debug.press_yes()

        self.finished = True

    def input_flow_tt(self) -> GeneratorType:
        screens = [
            B.ConfirmOutput,
            B.ConfirmOutput,
            B.FeeOverThreshold,
            B.SignTx,
        ]
        yield from self.go_through_all_screens(screens)


def lock_time_input_flow_tt(
    debug: DebugLink,
    layout_assert_func: Callable[[str], None],
    double_confirm: bool = False,
) -> GeneratorType:
    yield  # confirm output
    debug.wait_layout()
    debug.press_yes()
    yield  # confirm output
    debug.wait_layout()
    debug.press_yes()

    yield  # confirm locktime
    layout_text = debug.wait_layout().text_content()
    layout_assert_func(layout_text)
    debug.press_yes()

    yield  # confirm transaction
    debug.press_yes()
    if double_confirm:
        yield  # confirm transaction
        debug.press_yes()


class InputFlowLockTimeBlockHeight(InputFlowBase):
    def __init__(self, client: Client, block_height: str):
        super().__init__(client)
        self.block_height = block_height

    def layout_assert_func(self, layout_text: str) -> None:
        assert "blockheight" in layout_text
        assert self.block_height in layout_text

    def input_flow_tt(self) -> GeneratorType:
        yield from lock_time_input_flow_tt(
            self.debug, self.layout_assert_func, double_confirm=True
        )


class InputFlowLockTimeDatetime(InputFlowBase):
    def __init__(self, client: Client, lock_time_str: str):
        super().__init__(client)
        self.lock_time_str = lock_time_str

    def layout_assert_func(self, layout_text: str) -> None:
        assert self.lock_time_str in layout_text

    def input_flow_tt(self) -> GeneratorType:
        yield from lock_time_input_flow_tt(self.debug, self.layout_assert_func)


class InputFlowEIP712ShowMore(InputFlowBase):
    SHOW_MORE = (143, 167)

    def __init__(self, client: Client):
        super().__init__(client)
        self.same_for_all_models = True

    def _confirm_show_more(self) -> None:
        """Model-specific, either clicks a screen or presses a button."""
        self.debug.click(self.SHOW_MORE)

    def input_flow_tt(self) -> GeneratorType:
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

    def input_flow_tt(self) -> GeneratorType:
        """Clicks cancelling button"""
        yield  # confirm address
        self.debug.press_yes()

        yield  # confirm domain
        self.debug.press_no()


class InputFlowEthereumSignTxSkip(InputFlowBase):
    def __init__(self, client: Client, cancel: bool = False):
        super().__init__(client)
        self.cancel = cancel

    def input_flow_tt(self) -> GeneratorType:
        yield  # confirm address
        self.debug.press_yes()
        yield  # confirm amount
        self.debug.wait_layout()
        self.debug.press_yes()
        yield  # confirm data
        if self.cancel:
            self.debug.press_no()
        else:
            self.debug.press_yes()
            yield  # gas price
            self.debug.press_yes()
            yield  # maximum fee
            self.debug.press_yes()
            yield  # hold to confirm
            self.debug.press_yes()


class InputFlowEthereumSignTxScrollDown(InputFlowBase):
    SHOW_ALL = (143, 167)

    def __init__(self, client: Client, cancel: bool = False):
        super().__init__(client)
        self.cancel = cancel

    def input_flow_tt(self) -> GeneratorType:
        yield  # confirm address
        self.debug.wait_layout()
        self.debug.press_yes()
        yield  # confirm amount
        self.debug.wait_layout()
        self.debug.press_yes()
        yield  # confirm data
        self.debug.wait_layout()
        self.debug.click(self.SHOW_ALL)

        br = yield  # paginated data
        assert br.pages is not None
        for i in range(br.pages):
            self.debug.wait_layout()
            if i < br.pages - 1:
                self.debug.swipe_up()

        self.debug.press_yes()
        yield  # confirm data
        if self.cancel:
            self.debug.press_no()
        else:
            self.debug.press_yes()
            yield  # gas price
            self.debug.press_yes()
            yield  # maximum fee
            self.debug.press_yes()
            yield  # hold to confirm
            self.debug.press_yes()


class InputFlowEthereumSignTxGoBack(InputFlowBase):
    SHOW_ALL = (143, 167)
    GO_BACK = (16, 220)

    def __init__(self, client: Client, cancel: bool = False):
        super().__init__(client)
        self.cancel = cancel

    def input_flow_tt(self) -> GeneratorType:
        br = yield  # confirm address
        self.debug.wait_layout()
        self.debug.press_yes()
        br = yield  # confirm amount
        self.debug.wait_layout()
        self.debug.press_yes()
        br = yield  # confirm data
        self.debug.wait_layout()
        self.debug.click(self.SHOW_ALL)

        br = yield  # paginated data
        assert br.pages is not None
        for i in range(br.pages):
            self.debug.wait_layout()
            if i == 2:
                self.debug.click(self.GO_BACK)
                yield  # confirm data
                self.debug.wait_layout()
                if self.cancel:
                    self.debug.press_no()
                else:
                    self.debug.press_yes()
                    yield  # confirm address
                    self.debug.wait_layout()
                    self.debug.press_yes()
                    yield  # confirm amount
                    self.debug.wait_layout()
                    self.debug.press_yes()
                    yield  # hold to confirm
                    self.debug.wait_layout()
                    self.debug.press_yes()
                return

            elif i < br.pages - 1:
                self.debug.swipe_up()


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

    def input_flow_tt(self) -> GeneratorType:
        # 1. Confirm Reset
        yield from click_through(self.debug, screens=1, code=B.ResetDevice)

        # mnemonic phrases and rest
        self.mnemonic = yield from get_mnemonic_and_confirm_success(self.debug)


class InputFlowBip39ResetBackup(InputFlowBase):
    def __init__(self, client: Client):
        super().__init__(client)
        self.mnemonic = None

    # NOTE: same as above, just two more YES
    def input_flow_tt(self) -> GeneratorType:
        # 1. Confirm Reset
        # 2. Backup your seed
        # 3. Confirm warning
        yield from click_through(self.debug, screens=3, code=B.ResetDevice)

        # mnemonic phrases and rest
        self.mnemonic = yield from get_mnemonic_and_confirm_success(self.debug)


class InputFlowBip39ResetPIN(InputFlowBase):
    def __init__(self, client: Client):
        super().__init__(client)
        self.mnemonic = None

    def input_flow_tt(self) -> GeneratorType:
        br = yield  # Confirm Reset
        assert br.code == B.ResetDevice
        self.debug.press_yes()

        yield  # Enter new PIN
        self.debug.input("654")

        yield  # Confirm PIN
        self.debug.input("654")

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

    def input_flow_tt(self) -> GeneratorType:
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

    def input_flow_tt(self) -> GeneratorType:
        yield  # 1. Checklist
        self.debug.press_yes()
        if self.click_info:
            yield from click_info_button(self.debug)
        yield  # 2. Number of shares (5)
        self.debug.press_yes()
        yield  # 3. Checklist
        self.debug.press_yes()
        if self.click_info:
            yield from click_info_button(self.debug)
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

    def input_flow_tt(self) -> GeneratorType:
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

    def input_flow_tt(self) -> GeneratorType:
        yield  # 1. Checklist
        self.debug.press_yes()
        if self.click_info:
            yield from click_info_button(self.debug)
        yield  # 2. Set and confirm group count
        self.debug.press_yes()
        yield  # 3. Checklist
        self.debug.press_yes()
        if self.click_info:
            yield from click_info_button(self.debug)
        yield  # 4. Set and confirm group threshold
        self.debug.press_yes()
        yield  # 5. Checklist
        self.debug.press_yes()
        for _ in range(5):  # for each of 5 groups
            if self.click_info:
                yield from click_info_button(self.debug)
            yield  # Set & Confirm number of shares
            self.debug.press_yes()
            if self.click_info:
                yield from click_info_button(self.debug)
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

    def input_flow_tt(self) -> GeneratorType:
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


def enter_recovery_seed_dry_run(debug: DebugLink, mnemonic: list[str]) -> GeneratorType:
    yield
    assert "check the recovery seed" in debug.wait_layout().text_content()
    debug.click(buttons.OK)

    yield
    assert "number of words" in debug.wait_layout().text_content()
    debug.click(buttons.OK)

    yield
    assert "SelectWordCount" in debug.wait_layout().all_components()
    # click the correct number
    word_option_offset = 6
    word_options = (12, 18, 20, 24, 33)
    index = word_option_offset + word_options.index(len(mnemonic))
    debug.click(buttons.grid34(index % 3, index // 3))

    yield
    assert "Enter recovery seed" in debug.wait_layout().text_content()
    debug.click(buttons.OK)

    yield
    for word in mnemonic:
        assert debug.wait_layout().main_component() == "MnemonicKeyboard"
        debug.input(word)


class InputFlowBip39RecoveryDryRun(InputFlowBase):
    def __init__(self, client: Client, mnemonic: list[str]):
        super().__init__(client)
        self.mnemonic = mnemonic

    def input_flow_tt(self) -> GeneratorType:
        yield from enter_recovery_seed_dry_run(self.debug, self.mnemonic)

        yield
        self.debug.wait_layout()
        self.debug.click(buttons.OK)


class InputFlowBip39RecoveryDryRunInvalid(InputFlowBase):
    def __init__(self, client: Client):
        super().__init__(client)

    def input_flow_tt(self) -> GeneratorType:
        mnemonic = ["stick"] * 12
        yield from enter_recovery_seed_dry_run(self.debug, mnemonic)

        br = yield
        assert br.code == messages.ButtonRequestType.Warning
        assert "invalid recovery seed" in self.layout().text_content()
        self.debug.click(buttons.OK)

        yield  # retry screen
        assert "number of words" in self.layout().text_content()
        self.debug.click(buttons.CANCEL)

        yield
        assert "ABORT SEED CHECK" == self.layout().title()
        self.debug.click(buttons.OK)


def bip39_recovery_possible_pin(
    debug: DebugLink, mnemonic: list[str], pin: Optional[str]
) -> GeneratorType:
    yield
    assert "By continuing you agree to" in debug.wait_layout().text_content()
    debug.press_yes()

    # PIN when requested
    if pin is not None:
        yield
        assert debug.wait_layout().main_component() == "PinKeyboard"
        debug.input(pin)

        yield
        assert debug.wait_layout().main_component() == "PinKeyboard"
        debug.input(pin)

    yield
    assert "number of words" in debug.wait_layout().text_content()
    debug.press_yes()

    yield
    assert "SelectWordCount" in debug.wait_layout().all_components()
    debug.input(str(len(mnemonic)))

    yield
    assert "Enter recovery seed" in debug.wait_layout().text_content()
    debug.press_yes()

    yield
    for word in mnemonic:
        assert debug.wait_layout().main_component() == "MnemonicKeyboard"
        debug.input(word)

    yield
    assert (
        "You have finished recovering your wallet."
        in debug.wait_layout().text_content()
    )
    debug.press_yes()


class InputFlowBip39RecoveryPIN(InputFlowBase):
    def __init__(self, client: Client, mnemonic: list[str]):
        super().__init__(client)
        self.mnemonic = mnemonic

    def input_flow_tt(self) -> GeneratorType:
        yield from bip39_recovery_possible_pin(self.debug, self.mnemonic, pin="654")


class InputFlowBip39RecoveryNoPIN(InputFlowBase):
    def __init__(self, client: Client, mnemonic: list[str]):
        super().__init__(client)
        self.mnemonic = mnemonic

    def input_flow_tt(self) -> GeneratorType:
        yield from bip39_recovery_possible_pin(self.debug, self.mnemonic, pin=None)


class InputFlowSlip39AdvancedRecoveryDryRun(InputFlowBase):
    def __init__(self, client: Client, shares: list[str]):
        super().__init__(client)
        self.shares = shares

    def input_flow_tt(self) -> GeneratorType:
        yield  # Confirm Dryrun
        self.debug.press_yes()
        # run recovery flow
        yield from recovery_enter_shares(self.debug, self.shares, groups=True)


class InputFlowSlip39AdvancedRecovery(InputFlowBase):
    def __init__(self, client: Client, shares: list[str], click_info: bool):
        super().__init__(client)
        self.shares = shares
        self.click_info = click_info

    def input_flow_tt(self) -> GeneratorType:
        yield  # Confirm Recovery
        self.debug.press_yes()
        # Proceed with recovery
        yield from recovery_enter_shares(
            self.debug, self.shares, groups=True, click_info=self.click_info
        )


class InputFlowSlip39AdvancedRecoveryAbort(InputFlowBase):
    def __init__(self, client: Client):
        super().__init__(client)

    def input_flow_tt(self) -> GeneratorType:
        yield  # Confirm Recovery
        self.debug.press_yes()
        yield  # Homescreen - abort process
        self.debug.press_no()
        yield  # Homescreen - confirm abort
        self.debug.press_yes()


class InputFlowSlip39AdvancedRecoveryNoAbort(InputFlowBase):
    def __init__(self, client: Client, shares: list[str]):
        super().__init__(client)
        self.shares = shares

    def input_flow_tt(self) -> GeneratorType:
        yield  # Confirm Recovery
        self.debug.press_yes()
        yield  # Homescreen - abort process
        self.debug.press_no()
        yield  # Homescreen - go back to process
        self.debug.press_no()
        yield from recovery_enter_shares(self.debug, self.shares, groups=True)


class InputFlowSlip39AdvancedRecoveryTwoSharesWarning(InputFlowBase):
    def __init__(self, client: Client, first_share: list[str], second_share: list[str]):
        super().__init__(client)
        self.first_share = first_share
        self.second_share = second_share

    def input_flow_tt(self) -> GeneratorType:
        yield  # Confirm Recovery
        self.debug.press_yes()
        yield  # Homescreen - start process
        self.debug.press_yes()
        yield  # Enter number of words
        self.debug.input(str(len(self.first_share)))
        yield  # Homescreen - proceed to share entry
        self.debug.press_yes()
        yield  # Enter first share
        for word in self.first_share:
            self.debug.input(word)

        yield  # Continue to next share
        self.debug.press_yes()
        yield  # Homescreen - next share
        self.debug.press_yes()
        yield  # Enter next share
        for word in self.second_share:
            self.debug.input(word)

        br = yield
        assert br.code == messages.ButtonRequestType.Warning

        self.client.cancel()


def slip39_recovery_possible_pin(
    debug: DebugLink, shares: list[str], pin: Optional[str]
) -> GeneratorType:
    yield  # Confirm Recovery/Dryrun
    debug.press_yes()

    if pin is not None:
        yield  # Enter PIN
        debug.input(pin)
        yield  # Enter PIN again
        debug.input(pin)

    # Proceed with recovery
    yield from recovery_enter_shares(debug, shares)


class InputFlowSlip39BasicRecovery(InputFlowBase):
    def __init__(self, client: Client, shares: list[str]):
        super().__init__(client)
        self.shares = shares

    def input_flow_tt(self) -> GeneratorType:
        yield from slip39_recovery_possible_pin(self.debug, self.shares, pin=None)


class InputFlowSlip39BasicRecoveryPIN(InputFlowBase):
    def __init__(self, client: Client, shares: list[str], pin: str):
        super().__init__(client)
        self.shares = shares
        self.pin = pin

    def input_flow_tt(self) -> GeneratorType:
        yield from slip39_recovery_possible_pin(self.debug, self.shares, pin=self.pin)


class InputFlowSlip39BasicRecoveryAbort(InputFlowBase):
    def __init__(self, client: Client):
        super().__init__(client)

    def input_flow_tt(self) -> GeneratorType:
        yield  # Confirm Recovery
        self.debug.press_yes()
        yield  # Homescreen - abort process
        self.debug.press_no()
        yield  # Homescreen - confirm abort
        self.debug.press_yes()


class InputFlowSlip39BasicRecoveryNoAbort(InputFlowBase):
    def __init__(self, client: Client, shares: list[str]):
        super().__init__(client)
        self.shares = shares

    def input_flow_tt(self) -> GeneratorType:
        yield  # Confirm Recovery
        self.debug.press_yes()
        yield  # Homescreen - abort process
        self.debug.press_no()
        yield  # Homescreen - go back to process
        self.debug.press_no()
        # run recovery flow
        yield from recovery_enter_shares(self.debug, self.shares)


def slip39_recovery_setup_and_first_share(
    debug: DebugLink, first_share: list[str]
) -> GeneratorType:
    yield  # Homescreen - start process
    debug.press_yes()
    yield  # Enter number of words
    debug.input(str(len(first_share)))
    yield  # Homescreen - proceed to share entry
    debug.press_yes()
    yield  # Enter first share
    for word in first_share:
        debug.input(word)


class InputFlowSlip39BasicRecoveryRetryFirst(InputFlowBase):
    def __init__(self, client: Client):
        super().__init__(client)

    def input_flow_tt(self) -> GeneratorType:
        yield  # Confirm Recovery
        self.debug.press_yes()

        first_share = ["slush"] * 20
        yield from slip39_recovery_setup_and_first_share(self.debug, first_share)

        br = yield  # Invalid share
        assert br.code == messages.ButtonRequestType.Warning
        self.debug.press_yes()

        first_share = ["slush"] * 33
        yield from slip39_recovery_setup_and_first_share(self.debug, first_share)

        br = yield  # Invalid share
        assert br.code == messages.ButtonRequestType.Warning
        self.debug.press_yes()

        yield  # Homescreen
        self.debug.press_no()
        yield  # Confirm abort
        self.debug.press_yes()


class InputFlowSlip39BasicRecoveryRetrySecond(InputFlowBase):
    def __init__(self, client: Client, shares: list[str]):
        super().__init__(client)
        self.shares = shares

    def input_flow_tt(self) -> GeneratorType:
        yield  # Confirm Recovery
        self.debug.press_yes()

        # First valid share
        first_share = self.shares[0].split(" ")
        yield from slip39_recovery_setup_and_first_share(self.debug, first_share)

        yield  # More shares needed
        self.debug.press_yes()

        yield  # Enter another share
        invalid_share = first_share[:3] + ["slush"] * 17
        for word in invalid_share:
            self.debug.input(word)

        br = yield  # Invalid share
        assert br.code == messages.ButtonRequestType.Warning
        self.debug.press_yes()

        yield  # Proceed to next share
        second_share = self.shares[1].split(" ")
        for word in second_share:
            self.debug.input(word)

        yield  # More shares needed
        self.debug.press_no()
        yield  # Confirm abort
        self.debug.press_yes()


class InputFlowSlip39BasicRecoveryWrongNthWord(InputFlowBase):
    def __init__(self, client: Client, share: list[str], nth_word: int):
        super().__init__(client)
        self.share = share
        self.nth_word = nth_word

    def input_flow_tt(self) -> GeneratorType:
        yield  # Confirm Recovery
        self.debug.press_yes()

        # First complete share
        yield from slip39_recovery_setup_and_first_share(self.debug, self.share)

        yield  # Continue to next share
        self.debug.press_yes()
        yield  # Enter next share
        for i, word in enumerate(self.share):
            if i < self.nth_word:
                self.debug.input(word)
            else:
                self.debug.input(self.share[-1])
                break

        br = yield
        assert br.code == messages.ButtonRequestType.Warning

        self.client.cancel()


class InputFlowSlip39BasicRecoverySameShare(InputFlowBase):
    def __init__(self, client: Client, first_share: list[str], second_share: list[str]):
        super().__init__(client)
        self.first_share = first_share
        self.second_share = second_share

    def input_flow_tt(self) -> GeneratorType:
        yield  # Confirm Recovery
        self.debug.press_yes()

        # First complete share
        yield from slip39_recovery_setup_and_first_share(self.debug, self.first_share)

        yield  # Continue to next share
        self.debug.press_yes()
        yield  # Enter next share
        for word in self.second_share:
            self.debug.input(word)

        br = yield
        assert br.code == messages.ButtonRequestType.Warning

        # To catch the WARNING screen
        self.debug.press_yes()
        yield

        self.client.cancel()


class InputFlowResetSkipBackup(InputFlowBase):
    def __init__(self, client: Client):
        super().__init__(client)

    def input_flow_tt(self) -> GeneratorType:
        yield  # Confirm Recovery
        self.debug.press_yes()
        yield  # Skip Backup
        self.debug.press_no()
        yield  # Confirm skip backup
        self.debug.press_no()
