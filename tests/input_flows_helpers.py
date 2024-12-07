import typing as t

from trezorlib import messages
from trezorlib.debuglink import LayoutType
from trezorlib.debuglink import TrezorClientDebugLink as Client

from . import buttons
from . import translations as TR
from .click_tests.common import go_next
from .common import BRGeneratorType, get_text_possible_pagination

B = messages.ButtonRequestType


class PinFlow:
    def __init__(self, client: Client):
        self.client = client
        self.debug = self.client.debug

    def setup_new_pin(
        self,
        pin: str,
        second_different_pin: str | None = None,
        what: str = "pin",
    ) -> BRGeneratorType:
        assert (yield).name == "pin_device"  # Enter PIN
        assert "PinKeyboard" in self.debug.read_layout().all_components()
        self.debug.input(pin)
        if self.client.layout_type is LayoutType.TR:
            assert (yield).name == f"reenter_{what}"  # Reenter PIN
            assert (
                TR.translate(f"{what}__reenter_to_confirm")
                in self.debug.read_layout().text_content()
            )
            self.debug.press_yes()
        assert (yield).name == "pin_device"  # Enter PIN again
        assert "PinKeyboard" in self.debug.read_layout().all_components()
        if second_different_pin is not None:
            self.debug.input(second_different_pin)
        else:
            self.debug.input(pin)


class BackupFlow:
    def __init__(self, client: Client):
        self.client = client
        self.debug = self.client.debug

    def confirm_new_wallet(self) -> BRGeneratorType:
        yield
        assert TR.reset__by_continuing in self.debug.read_layout().text_content()
        if self.client.layout_type is LayoutType.TR:
            self.debug.press_right()
        self.debug.press_yes()


class RecoveryFlow:
    def __init__(self, client: Client):
        self.client = client
        self.debug = self.client.debug

    def _text_content(self) -> str:
        layout = self.debug.read_layout()
        return layout.title() + " " + layout.text_content()

    def confirm_recovery(self) -> BRGeneratorType:
        assert (yield).name == "recover_device"
        assert TR.reset__by_continuing in self._text_content()
        if self.client.layout_type is LayoutType.TR:
            self.debug.press_right()
        self.debug.press_yes()

    def confirm_dry_run(self) -> BRGeneratorType:
        assert (yield).name == "confirm_seedcheck"
        assert TR.recovery__check_dry_run in self._text_content()
        self.debug.press_yes()

    def setup_slip39_recovery(self, num_words: int) -> BRGeneratorType:
        if self.client.layout_type is LayoutType.TR:
            yield from self.tr_recovery_homescreen()
        yield from self.input_number_of_words(num_words)
        yield from self.enter_any_share()

    def setup_repeated_backup_recovery(self, num_words: int) -> BRGeneratorType:
        if self.client.layout_type is LayoutType.TR:
            yield from self.tr_recovery_homescreen()
        yield from self.input_number_of_words(num_words)
        yield from self.enter_your_backup()

    def setup_bip39_recovery(self, num_words: int) -> BRGeneratorType:
        if self.client.layout_type is LayoutType.TR:
            yield from self.tr_recovery_homescreen()
        yield from self.input_number_of_words(num_words)
        yield from self.enter_your_backup()

    def tr_recovery_homescreen(self) -> BRGeneratorType:
        yield
        assert TR.recovery__num_of_words in self._text_content()
        self.debug.press_yes()

    def enter_your_backup(self) -> BRGeneratorType:
        assert (yield).name == "recovery"
        if self.debug.layout_type is LayoutType.Mercury:
            assert TR.recovery__enter_each_word in self._text_content()
        else:
            assert TR.recovery__enter_backup in self._text_content()
        is_dry_run = (
            TR.recovery__title_dry_run.lower()
            in self.debug.read_layout().title().lower()
        )
        if self.client.layout_type is LayoutType.TR and not is_dry_run:
            # Normal recovery has extra info (not dry run)
            self.debug.press_right()
            self.debug.press_right()
        self.debug.press_yes()

    def enter_any_share(self) -> BRGeneratorType:
        assert (yield).name == "recovery"
        assert (
            TR.recovery__enter_any_share in self._text_content()
            or TR.recovery__enter_each_word in self._text_content()
        )
        is_dry_run = (
            TR.recovery__title_dry_run.lower()
            in self.debug.read_layout().title().lower()
        )
        if self.client.layout_type is LayoutType.TR and not is_dry_run:
            # Normal recovery has extra info (not dry run)
            self.debug.press_right()
            self.debug.press_right()
        self.debug.press_yes()

    def abort_recovery(self, confirm: bool) -> BRGeneratorType:
        yield
        if self.client.layout_type is LayoutType.TR:
            assert TR.recovery__num_of_words in self._text_content()
            self.debug.press_no()
            yield
            assert TR.recovery__wanna_cancel_recovery in self._text_content()
            self.debug.press_right()
            if confirm:
                self.debug.press_yes()
            else:
                self.debug.press_no()
        elif self.client.layout_type is LayoutType.Mercury:
            assert TR.recovery__enter_each_word in self._text_content()
            self.debug.click(buttons.CORNER_BUTTON)
            self.debug.synchronize_at("VerticalMenu")
            if confirm:
                self.debug.click(buttons.VERTICAL_MENU[0])
            else:
                self.debug.click(buttons.CORNER_BUTTON)
        else:
            assert TR.recovery__enter_any_share in self._text_content()
            self.debug.press_no()
            yield
            assert TR.recovery__wanna_cancel_recovery in self._text_content()
            if confirm:
                self.debug.press_yes()
            else:
                self.debug.press_no()

    def abort_recovery_between_shares(self) -> BRGeneratorType:
        yield
        if self.client.layout_type is LayoutType.TR:
            assert TR.regexp("recovery__x_of_y_entered_template").search(
                self._text_content()
            )
            self.debug.press_no()
            assert (yield).name == "abort_recovery"
            assert TR.recovery__wanna_cancel_recovery in self._text_content()
            self.debug.press_right()
            self.debug.press_yes()
        elif self.client.layout_type is LayoutType.Mercury:
            assert TR.regexp("recovery__x_of_y_entered_template").search(
                self._text_content()
            )
            self.debug.click(buttons.CORNER_BUTTON)
            self.debug.synchronize_at("VerticalMenu")
            self.debug.click(buttons.VERTICAL_MENU[0])
            assert (yield).name == "abort_recovery"
            layout = self.debug.swipe_up()
            assert layout.title() == TR.recovery__title_cancel_recovery
            self.debug.click(buttons.TAP_TO_CONFIRM)
        else:
            assert TR.regexp("recovery__x_of_y_entered_template").search(
                self._text_content()
            )
            self.debug.press_no()
            assert (yield).name == "abort_recovery"
            assert TR.recovery__wanna_cancel_recovery in self._text_content()
            self.debug.press_yes()

    def input_number_of_words(self, num_words: int) -> BRGeneratorType:
        br = yield
        assert br.code == B.MnemonicWordCount
        assert br.name == "recovery_word_count"
        if self.client.layout_type is LayoutType.TR:
            assert TR.word_count__title in self.debug.read_layout().title()
        else:
            assert TR.recovery__num_of_words in self._text_content()
        self.debug.input(str(num_words))

    def warning_invalid_recovery_seed(self) -> BRGeneratorType:
        br = yield
        assert br.code == B.Warning
        assert TR.recovery__invalid_wallet_backup_entered in self._text_content()
        self.debug.press_yes()

    def warning_invalid_recovery_share(self) -> BRGeneratorType:
        br = yield
        assert br.code == B.Warning
        assert TR.recovery__invalid_share_entered in self._text_content()
        self.debug.press_yes()

    def warning_group_threshold_reached(self) -> BRGeneratorType:
        br = yield
        assert br.code == B.Warning
        assert TR.recovery__group_threshold_reached in self._text_content()
        self.debug.press_yes()

    def warning_share_already_entered(self) -> BRGeneratorType:
        br = yield
        assert br.code == B.Warning
        assert TR.recovery__share_already_entered in self._text_content()
        self.debug.press_yes()

    def warning_share_from_another_shamir(self) -> BRGeneratorType:
        br = yield
        assert br.code == B.Warning
        assert (
            TR.recovery__share_from_another_multi_share_backup in self._text_content()
        )
        self.debug.press_yes()

    def success_share_group_entered(self) -> BRGeneratorType:
        assert (yield).name == "share_success"
        assert TR.recovery__you_have_entered in self._text_content()
        self.debug.press_yes()

    def success_wallet_recovered(self) -> BRGeneratorType:
        br = yield
        assert br.code == B.Success
        assert TR.recovery__wallet_recovered in self._text_content()
        self.debug.press_yes()

    def success_bip39_dry_run_valid(self) -> BRGeneratorType:
        br = yield
        assert br.code == B.Success
        text = get_text_possible_pagination(self.debug, br)
        # TODO: make sure the translations fit on one page
        if self.client.layout_type not in (LayoutType.TT, LayoutType.Mercury):
            assert TR.recovery__dry_run_bip39_valid_match in text
        self.debug.press_yes()

    def success_slip39_dryrun_valid(self) -> BRGeneratorType:
        br = yield
        assert br.code == B.Success
        text = get_text_possible_pagination(self.debug, br)
        # TODO: make sure the translations fit on one page
        if self.client.layout_type not in (LayoutType.TT, LayoutType.Mercury):
            assert TR.recovery__dry_run_slip39_valid_match in text
        self.debug.press_yes()

    def warning_slip39_dryrun_mismatch(self) -> BRGeneratorType:
        br = yield
        assert br.code == B.Warning
        text = get_text_possible_pagination(self.debug, br)
        # TODO: make sure the translations fit on one page on TT
        if self.client.layout_type not in (LayoutType.TT, LayoutType.Mercury):
            assert TR.recovery__dry_run_slip39_valid_mismatch in text
        self.debug.press_yes()

    def warning_bip39_dryrun_mismatch(self) -> BRGeneratorType:
        br = yield
        assert br.code == B.Warning
        text = get_text_possible_pagination(self.debug, br)
        # TODO: make sure the translations fit on one page
        if self.client.layout_type not in (LayoutType.TT, LayoutType.Mercury):
            assert TR.recovery__dry_run_bip39_valid_mismatch in text
        self.debug.press_yes()

    def success_more_shares_needed(
        self, count_needed: int | None = None, click_ok: bool = True
    ) -> BRGeneratorType:
        br = yield
        assert br.name == "recovery"
        text = get_text_possible_pagination(self.debug, br)
        if count_needed is not None:
            assert str(count_needed) in text
        if click_ok:
            self.debug.press_yes()

    def input_mnemonic(self, mnemonic: list[str]) -> BRGeneratorType:
        br = yield
        assert br.code == B.MnemonicInput
        assert br.name == "mnemonic"
        assert "MnemonicKeyboard" in self.debug.read_layout().all_components()
        for _, word in enumerate(mnemonic):
            self.debug.input(word)

    def input_all_slip39_shares(
        self,
        shares: list[str],
        has_groups: bool = False,
        click_info: bool = False,
    ) -> BRGeneratorType:
        for index, share in enumerate(shares):
            mnemonic = share.split(" ")
            yield from self.input_mnemonic(mnemonic)

            if index < len(shares) - 1:
                if has_groups:
                    yield from self.success_share_group_entered()

                yield from self.success_more_shares_needed(click_ok=not click_info)
                if click_info:
                    if self.client.layout_type is LayoutType.TT:
                        yield from self.tt_click_info()
                    elif self.client.layout_type is LayoutType.Mercury:
                        yield from self.mercury_click_info()
                    else:
                        raise ValueError("Unknown model!")
                    yield from self.success_more_shares_needed()

    def tt_click_info(self) -> t.Generator[t.Any, t.Any, None]:
        self.debug.press_info()
        br = yield
        assert br.name == "show_shares"
        for _ in range(br.pages):
            self.debug.swipe_up()
        self.debug.press_yes()

    def mercury_click_info(self) -> BRGeneratorType:
        # Moving through the menu into the show_shares screen
        self.debug.click(buttons.CORNER_BUTTON)
        self.debug.synchronize_at("VerticalMenu")
        self.debug.click(buttons.VERTICAL_MENU[0])
        br = yield
        assert br.name == "show_shares"
        assert br.code == B.Other
        # Getting back to the homepage
        self.debug.click(buttons.CORNER_BUTTON)
        self.debug.click(buttons.CORNER_BUTTON)


class EthereumFlow:
    GO_BACK = (16, 220)

    def __init__(self, client: Client):
        self.client = client
        self.debug = self.client.debug

    def confirm_data(self, info: bool = False, cancel: bool = False) -> BRGeneratorType:
        assert (yield).name == "confirm_data"
        assert self.debug.read_layout().title() == TR.ethereum__title_input_data
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
        assert self.debug.read_layout().title() == TR.ethereum__title_input_data
        for _ in range(br.pages):
            self.debug.read_layout()
            go_next(self.debug)
        self.debug.read_layout()

    def paginate_data_go_back(self) -> BRGeneratorType:
        br = yield
        assert br.name == "confirm_data"
        assert br.pages is not None
        assert br.pages > 2
        assert self.debug.read_layout().title() == TR.ethereum__title_input_data
        if self.client.layout_type is LayoutType.TR:
            self.debug.press_right()
            self.debug.press_right()
            self.debug.press_left()
            self.debug.press_left()
            self.debug.press_left()
        elif self.client.layout_type in (LayoutType.TT, LayoutType.Mercury):
            self.debug.swipe_up()
            self.debug.swipe_up()
            self.debug.click(self.GO_BACK)
        else:
            raise ValueError(f"Unknown layout: {self.client.layout_type}")

    def _confirm_tx_tt(
        self, cancel: bool, info: bool, go_back_from_summary: bool
    ) -> BRGeneratorType:
        assert (yield).name == "confirm_ethereum_tx"
        assert self.debug.read_layout().title() == TR.words__address
        if cancel:
            self.debug.press_no()
            return

        self.debug.press_yes()
        assert (yield).name == "confirm_ethereum_tx"
        assert self.debug.read_layout().title() == TR.words__title_summary
        assert TR.send__maximum_fee in self.debug.read_layout().text_content()
        if go_back_from_summary:
            self.debug.press_no()
            assert (yield).name == "confirm_ethereum_tx"
            self.debug.press_yes()
            assert (yield).name == "confirm_ethereum_tx"
        if info:
            self.debug.press_info()
            assert TR.ethereum__gas_limit in self.debug.read_layout().text_content()
            assert TR.ethereum__gas_price in self.debug.read_layout().text_content()
            self.debug.press_no()
        self.debug.press_yes()
        assert (yield).name == "confirm_ethereum_tx"

    def _confirm_tx_tr(
        self, cancel: bool, info: bool, go_back_from_summary: bool
    ) -> BRGeneratorType:
        assert (yield).name == "confirm_ethereum_tx"
        assert (
            TR.ethereum__interaction_contract in self.debug.read_layout().title()
            or TR.words__recipient in self.debug.read_layout().title()
        )
        if cancel:
            self.debug.press_left()
            return
        self.debug.press_right()
        assert (yield).name == "confirm_ethereum_tx"
        assert TR.send__maximum_fee in self.debug.read_layout().text_content()
        if go_back_from_summary:
            self.debug.press_left()
            assert (yield).name == "confirm_ethereum_tx"
            self.debug.press_right()
            assert (yield).name == "confirm_ethereum_tx"
        if info:
            self.debug.press_right()
            assert TR.ethereum__gas_limit in self.debug.read_layout().text_content()
            self.debug.press_right()
            assert TR.ethereum__gas_price in self.debug.read_layout().text_content()
            self.debug.press_left()
            self.debug.press_left()
        self.debug.press_middle()
        assert (yield).name == "confirm_ethereum_tx"

    def _confirm_tx_mercury(
        self, cancel: bool, info: bool, go_back_from_summary: bool
    ) -> BRGeneratorType:
        assert (yield).name == "confirm_output"
        title = self.debug.read_layout().title()
        assert TR.words__address in title
        assert TR.words__recipient in title

        if cancel:
            self.debug.press_no()
            return

        self.debug.swipe_up()
        assert (yield).name == "confirm_total"
        layout = self.debug.read_layout()
        assert layout.title() == TR.words__title_summary
        assert TR.send__maximum_fee in layout.text_content()
        if go_back_from_summary:
            self.debug.press_no()
            assert (yield).name == "confirm_ethereum_tx"
            self.debug.press_yes()
            assert (yield).name == "confirm_ethereum_tx"
        if info:
            self.debug.click(buttons.CORNER_BUTTON)
            self.debug.synchronize_at("VerticalMenu")
            self.debug.click(buttons.VERTICAL_MENU[0])
            text = self.debug.read_layout().text_content()
            assert TR.ethereum__gas_limit in text
            assert TR.ethereum__gas_price in text
            self.debug.click(buttons.CORNER_BUTTON)
            self.debug.click(buttons.CORNER_BUTTON)
        self.debug.swipe_up()
        self.debug.read_layout()
        self.debug.click(buttons.TAP_TO_CONFIRM)
        assert (yield).name == "confirm_ethereum_tx"

    def confirm_tx(
        self,
        cancel: bool = False,
        info: bool = False,
        go_back_from_summary: bool = False,
    ) -> BRGeneratorType:
        if self.client.layout_type is LayoutType.TT:
            yield from self._confirm_tx_tt(cancel, info, go_back_from_summary)
        elif self.client.layout_type is LayoutType.TR:
            yield from self._confirm_tx_tr(cancel, info, go_back_from_summary)
        elif self.client.layout_type is LayoutType.Mercury:
            yield from self._confirm_tx_mercury(cancel, info, go_back_from_summary)
        else:
            raise ValueError("Unknown model!")

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
        if self.client.layout_type is LayoutType.TT:
            # confirm intro
            if info:
                self.debug.click(
                    buttons.CORNER_BUTTON,
                )
                assert self.debug.read_layout().title() in (
                    TR.ethereum__staking_stake_address,
                    TR.ethereum__staking_claim_address,
                )
                self.debug.press_no()
            self.debug.press_yes()
            yield

            # confirm summary
            if info:
                self.debug.press_info()
                assert TR.ethereum__gas_limit in self.debug.read_layout().text_content()
                assert TR.ethereum__gas_price in self.debug.read_layout().text_content()
                self.debug.press_no()
            self.debug.press_yes()
            yield

            self.debug.press_yes()

        elif self.client.layout_type is LayoutType.Mercury:
            # confirm intro
            if info:
                self.debug.click(buttons.CORNER_BUTTON)
                self.debug.synchronize_at("VerticalMenu")
                self.debug.click(buttons.VERTICAL_MENU[0])
                assert self.debug.read_layout().title() in (
                    TR.ethereum__staking_stake_address,
                    TR.ethereum__staking_claim_address,
                )
                self.debug.click(buttons.CORNER_BUTTON)
                self.debug.click(buttons.CORNER_BUTTON)

            self.debug.swipe_up()
            br = yield
            assert br.code == B.SignTx
            assert br.name == "confirm_total"

            # confirm summary
            if info:
                self.debug.click(buttons.CORNER_BUTTON)
                self.debug.synchronize_at("VerticalMenu")
                self.debug.click(buttons.VERTICAL_MENU[0])
                assert TR.ethereum__gas_limit in self.debug.read_layout().text_content()
                assert TR.ethereum__gas_price in self.debug.read_layout().text_content()
                self.debug.click(buttons.CORNER_BUTTON)
                self.debug.click(buttons.CORNER_BUTTON)
            self.debug.swipe_up()
            # br = yield  # FIXME: no BR on sign transaction

            self.debug.press_yes()

        elif self.client.layout_type is LayoutType.TR:
            # confirm intro
            if info:
                self.debug.press_right()
                assert self.debug.read_layout().title() in (
                    TR.ethereum__staking_stake_address,
                    TR.ethereum__staking_claim_address,
                )
                self.debug.press_left()
            self.debug.press_middle()
            yield

            # confirm summary
            if info:
                self.debug.press_right()
                assert TR.ethereum__gas_limit in self.debug.read_layout().text_content()
                self.debug.press_right()
                assert TR.ethereum__gas_price in self.debug.read_layout().text_content()
                self.debug.press_left()
                self.debug.press_left()
            self.debug.press_middle()
            yield

            self.debug.press_yes()

        else:
            raise ValueError("Unknown model!")
