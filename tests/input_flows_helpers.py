from trezorlib import messages
from trezorlib.debuglink import TrezorClientDebugLink as Client

from . import translations as TR
from .common import BRGeneratorType, get_text_possible_pagination

B = messages.ButtonRequestType


class PinFlow:
    def __init__(self, client: Client):
        self.client = client
        self.debug = self.client.debug

    def setup_new_pin(
        self, pin: str, second_different_pin: str | None = None
    ) -> BRGeneratorType:
        yield  # Enter PIN
        assert "PinKeyboard" in self.debug.wait_layout().all_components()
        self.debug.input(pin)
        if self.debug.model == "Safe 3":
            yield  # Reenter PIN
            TR.assert_in(
                self.debug.wait_layout().text_content(), "pin__reenter_to_confirm"
            )
            self.debug.press_yes()
        yield  # Enter PIN again
        assert "PinKeyboard" in self.debug.wait_layout().all_components()
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
        TR.assert_in(self.debug.wait_layout().text_content(), "reset__by_continuing")
        if self.debug.model == "Safe 3":
            self.debug.press_right()
        self.debug.press_yes()


class RecoveryFlow:
    def __init__(self, client: Client):
        self.client = client
        self.debug = self.client.debug

    def _text_content(self) -> str:
        return self.debug.wait_layout().text_content()

    def confirm_recovery(self) -> BRGeneratorType:
        yield
        TR.assert_in(self._text_content(), "reset__by_continuing")
        if self.debug.model == "Safe 3":
            self.debug.press_right()
        self.debug.press_yes()

    def confirm_dry_run(self) -> BRGeneratorType:
        yield
        TR.assert_in(self._text_content(), "recovery__check_dry_run")
        self.debug.press_yes()

    def setup_slip39_recovery(self, num_words: int) -> BRGeneratorType:
        if self.debug.model == "Safe 3":
            yield from self.tr_recovery_homescreen()
        yield from self.input_number_of_words(num_words)
        yield from self.enter_any_share()

    def setup_bip39_recovery(self, num_words: int) -> BRGeneratorType:
        if self.debug.model == "Safe 3":
            yield from self.tr_recovery_homescreen()
        yield from self.input_number_of_words(num_words)
        yield from self.enter_your_backup()

    def tr_recovery_homescreen(self) -> BRGeneratorType:
        yield
        TR.assert_in(self._text_content(), "recovery__num_of_words")
        self.debug.press_yes()

    def enter_your_backup(self) -> BRGeneratorType:
        yield
        TR.assert_in(self._text_content(), "recovery__enter_backup")
        is_dry_run = any(
            title in self.debug.wait_layout().title().lower()
            for title in TR.translate("recovery__title_dry_run", lower=True)
        )
        if self.debug.model == "Safe 3" and not is_dry_run:
            # Normal recovery has extra info (not dry run)
            self.debug.press_right(wait=True)
            self.debug.press_right(wait=True)
        self.debug.press_yes()

    def enter_any_share(self) -> BRGeneratorType:
        yield
        TR.assert_in(self._text_content(), "recovery__enter_any_share")
        is_dry_run = any(
            title in self.debug.wait_layout().title().lower()
            for title in TR.translate("recovery__title_dry_run", lower=True)
        )
        if self.debug.model == "Safe 3" and not is_dry_run:
            # Normal recovery has extra info (not dry run)
            self.debug.press_right(wait=True)
            self.debug.press_right(wait=True)
        self.debug.press_yes()

    def abort_recovery(self, confirm: bool) -> BRGeneratorType:
        yield
        if self.debug.model == "Safe 3":
            TR.assert_in(self._text_content(), "recovery__num_of_words")
        else:
            TR.assert_in(self._text_content(), "recovery__enter_any_share")
        self.debug.press_no()

        yield
        TR.assert_in(self._text_content(), "recovery__wanna_cancel_recovery")
        if self.debug.model == "Safe 3":
            self.debug.press_right()
        if confirm:
            self.debug.press_yes()
        else:
            self.debug.press_no()

    def input_number_of_words(self, num_words: int) -> BRGeneratorType:
        br = yield
        assert br.code == B.MnemonicWordCount
        if self.debug.model == "Safe 3":
            TR.assert_in(self.debug.wait_layout().title(), "word_count__title")
        else:
            TR.assert_in(self._text_content(), "recovery__num_of_words")
        self.debug.input(str(num_words))

    def warning_invalid_recovery_seed(self) -> BRGeneratorType:
        br = yield
        assert br.code == B.Warning
        TR.assert_in(self._text_content(), "recovery__invalid_seed_entered")
        self.debug.press_yes()

    def warning_invalid_recovery_share(self) -> BRGeneratorType:
        br = yield
        assert br.code == B.Warning
        TR.assert_in(self._text_content(), "recovery__invalid_share_entered")
        self.debug.press_yes()

    def warning_group_threshold_reached(self) -> BRGeneratorType:
        br = yield
        assert br.code == B.Warning
        TR.assert_in(self._text_content(), "recovery__group_threshold_reached")
        self.debug.press_yes()

    def warning_share_already_entered(self) -> BRGeneratorType:
        br = yield
        assert br.code == B.Warning
        TR.assert_in(self._text_content(), "recovery__share_already_entered")
        self.debug.press_yes()

    def warning_share_from_another_shamir(self) -> BRGeneratorType:
        br = yield
        assert br.code == B.Warning
        TR.assert_in(self._text_content(), "recovery__share_from_another_shamir")
        self.debug.press_yes()

    def success_share_group_entered(self) -> BRGeneratorType:
        yield
        TR.assert_in(self._text_content(), "recovery__you_have_entered")
        self.debug.press_yes()

    def success_wallet_recovered(self) -> BRGeneratorType:
        br = yield
        assert br.code == B.Success
        TR.assert_in(self._text_content(), "recovery__wallet_recovered")
        self.debug.press_yes()

    def success_bip39_dry_run_valid(self) -> BRGeneratorType:
        br = yield
        assert br.code == B.Success
        text = get_text_possible_pagination(self.debug, br)
        # TODO: make sure the translations fit on one page
        if self.client.debug.model != "T":
            TR.assert_in(text, "recovery__dry_run_bip39_valid_match")
        self.debug.press_yes()

    def success_slip39_dryrun_valid(self) -> BRGeneratorType:
        br = yield
        assert br.code == B.Success
        text = get_text_possible_pagination(self.debug, br)
        # TODO: make sure the translations fit on one page
        if self.client.debug.model != "T":
            TR.assert_in(text, "recovery__dry_run_slip39_valid_match")
        self.debug.press_yes()

    def warning_slip39_dryrun_mismatch(self) -> BRGeneratorType:
        br = yield
        assert br.code == B.Warning
        text = get_text_possible_pagination(self.debug, br)
        # TODO: make sure the translations fit on one page on TT
        if self.client.debug.model != "T":
            TR.assert_in(text, "recovery__dry_run_slip39_valid_mismatch")
        self.debug.press_yes()

    def warning_bip39_dryrun_mismatch(self) -> BRGeneratorType:
        br = yield
        assert br.code == B.Warning
        text = get_text_possible_pagination(self.debug, br)
        # TODO: make sure the translations fit on one page
        if self.client.debug.model != "T":
            TR.assert_in(text, "recovery__dry_run_bip39_valid_mismatch")
        self.debug.press_yes()

    def success_more_shares_needed(
        self, count_needed: int | None = None
    ) -> BRGeneratorType:
        br = yield
        text = get_text_possible_pagination(self.debug, br)
        if count_needed is not None:
            assert str(count_needed) in text
        self.debug.press_yes()

    def input_mnemonic(self, mnemonic: list[str]) -> BRGeneratorType:
        br = yield
        assert br.code == B.MnemonicInput
        assert "MnemonicKeyboard" in self.debug.wait_layout().all_components()
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
                if self.debug.model == "T" and click_info:
                    yield from self.tt_click_info()
                yield from self.success_more_shares_needed()

    def tt_click_info(
        self,
    ) -> BRGeneratorType:
        # Moving through the INFO button
        self.debug.press_info()
        yield
        self.debug.swipe_up()
        self.debug.press_yes()


class EthereumFlow:
    GO_BACK = (16, 220)

    def __init__(self, client: Client):
        self.client = client
        self.debug = self.client.debug

    def confirm_data(self, info: bool = False, cancel: bool = False) -> BRGeneratorType:
        yield
        TR.assert_equals(
            self.debug.wait_layout().title(), "ethereum__title_confirm_data"
        )
        if info:
            self.debug.press_info()
        elif cancel:
            self.debug.press_no()
        else:
            self.debug.press_yes()

    def paginate_data(self) -> BRGeneratorType:
        br = yield
        TR.assert_equals(
            self.debug.wait_layout().title(), "ethereum__title_confirm_data"
        )
        assert br.pages is not None
        for i in range(br.pages):
            self.debug.wait_layout()
            if i < br.pages - 1:
                self.debug.swipe_up()
        self.debug.press_yes()

    def paginate_data_go_back(self) -> BRGeneratorType:
        br = yield
        TR.assert_equals(
            self.debug.wait_layout().title(), "ethereum__title_confirm_data"
        )
        assert br.pages is not None
        assert br.pages > 2
        if self.debug.model == "T":
            self.debug.swipe_up(wait=True)
            self.debug.swipe_up(wait=True)
            self.debug.click(self.GO_BACK)
        else:
            self.debug.press_right()
            self.debug.press_right()
            self.debug.press_left()
            self.debug.press_left()
            self.debug.press_left()

    def confirm_tx(
        self,
        cancel: bool = False,
        info: bool = False,
        go_back_from_summary: bool = False,
    ) -> BRGeneratorType:
        yield
        TR.assert_equals(self.debug.wait_layout().title(), "words__recipient")

        if self.debug.model == "T":
            if cancel:
                self.debug.press_no()
            else:
                self.debug.press_yes()
                yield
                TR.assert_equals(
                    self.debug.wait_layout().title(), "words__title_summary"
                )
                TR.assert_in(
                    self.debug.wait_layout().text_content(), "send__maximum_fee"
                )
                if go_back_from_summary:
                    self.debug.press_no()
                    yield
                    self.debug.press_yes()
                    yield
                if info:
                    self.debug.press_info(wait=True)
                    TR.assert_in(
                        self.debug.wait_layout().text_content(), "ethereum__gas_limit"
                    )
                    TR.assert_in(
                        self.debug.wait_layout().text_content(), "ethereum__gas_price"
                    )
                    self.debug.press_no(wait=True)
                self.debug.press_yes()
        else:
            if cancel:
                self.debug.press_left()
            else:
                self.debug.press_right()
                yield
                TR.assert_in(
                    self.debug.wait_layout().text_content(), "send__maximum_fee"
                )
                if go_back_from_summary:
                    self.debug.press_left()
                    yield
                    self.debug.press_right()
                    yield
                if info:
                    self.debug.press_right(wait=True)
                    TR.assert_in(
                        self.debug.wait_layout().text_content(), "ethereum__gas_limit"
                    )
                    self.debug.press_right(wait=True)
                    TR.assert_in(
                        self.debug.wait_layout().text_content(), "ethereum__gas_price"
                    )
                    self.debug.press_left(wait=True)
                    self.debug.press_left(wait=True)
                self.debug.press_middle()

    def confirm_tx_staking(
        self,
        info: bool = False,
    ) -> BRGeneratorType:
        yield
        TR.assert_equals_multiple(
            self.debug.wait_layout().title(),
            [
                "ethereum__staking_stake",
                "ethereum__staking_unstake",
                "ethereum__staking_claim",
            ],
        )
        TR.assert_equals_multiple(
            self.debug.wait_layout().text_content(),
            [
                "ethereum__staking_stake_intro",
                "ethereum__staking_unstake_intro",
                "ethereum__staking_claim_intro",
            ],
        )
        if self.debug.model == "T":
            # confirm intro
            if info:
                self.debug.press_info(wait=True)
                TR.assert_equals_multiple(
                    self.debug.wait_layout().title(),
                    [
                        "ethereum__staking_stake_address",
                        "ethereum__staking_claim_address",
                    ],
                )
                self.debug.press_no(wait=True)
            self.debug.press_yes()
            yield

            # confirm summary
            if info:
                self.debug.press_info(wait=True)
                TR.assert_in(
                    self.debug.wait_layout().text_content(), "ethereum__gas_limit"
                )
                TR.assert_in(
                    self.debug.wait_layout().text_content(), "ethereum__gas_price"
                )
                self.debug.press_no(wait=True)
            self.debug.press_yes()
            yield
        else:
            # confirm intro
            if info:
                self.debug.press_right(wait=True)
                TR.assert_equals_multiple(
                    self.debug.wait_layout().title(),
                    [
                        "ethereum__staking_stake_address",
                        "ethereum__staking_claim_address",
                    ],
                )
                self.debug.press_left(wait=True)
            self.debug.press_middle()
            yield

            # confirm summary
            if info:
                self.debug.press_right(wait=True)
                TR.assert_in(
                    self.debug.wait_layout().text_content(), "ethereum__gas_limit"
                )
                self.debug.press_right(wait=True)
                TR.assert_in(
                    self.debug.wait_layout().text_content(), "ethereum__gas_price"
                )
                self.debug.press_left(wait=True)
                self.debug.press_left(wait=True)
            self.debug.press_middle()
            yield
