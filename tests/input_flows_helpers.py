from trezorlib import messages
from trezorlib.debuglink import TrezorClientDebugLink as Client

from .common import BRGeneratorType

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
            assert "re-enter PIN" in self.debug.wait_layout().text_content()
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
        assert "By continuing you agree" in self.debug.wait_layout().text_content()
        if self.debug.model == "Safe 3":
            self.debug.press_right()
        self.debug.press_yes()


class RecoveryFlow:
    def __init__(self, client: Client):
        self.client = client
        self.debug = self.client.debug

    def confirm_recovery(self) -> BRGeneratorType:
        yield
        assert "By continuing you agree" in self.debug.wait_layout().text_content()
        if self.debug.model == "Safe 3":
            self.debug.press_right()
        self.debug.press_yes()

    def confirm_dry_run(self) -> BRGeneratorType:
        yield
        assert "Check your backup" in self.debug.wait_layout().text_content()
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
        assert "number of words" in self.debug.wait_layout().text_content()
        self.debug.press_yes()

    def enter_your_backup(self) -> BRGeneratorType:
        yield
        assert "Enter your backup" in self.debug.wait_layout().text_content()
        if (
            self.debug.model == "Safe 3"
            and "BACKUP CHECK" not in self.debug.wait_layout().title()
        ):
            # Normal recovery has extra info (not dry run)
            self.debug.press_right(wait=True)
            self.debug.press_right(wait=True)
        self.debug.press_yes()

    def enter_any_share(self) -> BRGeneratorType:
        yield
        assert "Enter any share" in self.debug.wait_layout().text_content()
        if (
            self.debug.model == "Safe 3"
            and "BACKUP CHECK" not in self.debug.wait_layout().title()
        ):
            # Normal recovery has extra info (not dry run)
            self.debug.press_right(wait=True)
            self.debug.press_right(wait=True)
        self.debug.press_yes()

    def abort_recovery(self, confirm: bool) -> BRGeneratorType:
        yield
        if self.debug.model == "Safe 3":
            assert "number of words" in self.debug.wait_layout().text_content()
        else:
            assert "Enter any share" in self.debug.wait_layout().text_content()
        self.debug.press_no()

        yield
        assert "cancel the recovery" in self.debug.wait_layout().text_content()
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
            assert "NUMBER OF WORDS" in self.debug.wait_layout().title()
        else:
            assert "number of words" in self.debug.wait_layout().text_content()
        self.debug.input(str(num_words))

    def warning_invalid_recovery_seed(self) -> BRGeneratorType:
        br = yield
        assert br.code == B.Warning
        assert "Invalid recovery seed" in self.debug.wait_layout().text_content()
        self.debug.press_yes()

    def warning_invalid_recovery_share(self) -> BRGeneratorType:
        br = yield
        assert br.code == B.Warning
        assert "Invalid recovery share" in self.debug.wait_layout().text_content()
        self.debug.press_yes()

    def warning_group_threshold_reached(self) -> BRGeneratorType:
        br = yield
        assert br.code == B.Warning
        assert "Group threshold reached" in self.debug.wait_layout().text_content()
        self.debug.press_yes()

    def warning_share_already_entered(self) -> BRGeneratorType:
        br = yield
        assert br.code == B.Warning
        assert "Share already entered" in self.debug.wait_layout().text_content()
        self.debug.press_yes()

    def warning_share_from_another_shamir(self) -> BRGeneratorType:
        br = yield
        assert br.code == B.Warning
        assert (
            "You have entered a share from another Shamir Backup"
            in self.debug.wait_layout().text_content()
        )
        self.debug.press_yes()

    def success_share_group_entered(self) -> BRGeneratorType:
        yield
        assert "You have entered" in self.debug.wait_layout().text_content()
        assert "Group" in self.debug.wait_layout().text_content()
        self.debug.press_yes()

    def success_wallet_recovered(self) -> BRGeneratorType:
        br = yield
        assert br.code == B.Success
        assert (
            "Wallet recovered successfully" in self.debug.wait_layout().text_content()
        )
        self.debug.press_yes()

    def success_bip39_dry_run_valid(self) -> BRGeneratorType:
        br = yield
        assert br.code == B.Success
        assert "recovery seed is valid" in self.debug.wait_layout().text_content()
        self.debug.press_yes()

    def success_slip39_dryrun_valid(self) -> BRGeneratorType:
        br = yield
        assert br.code == B.Success
        assert "recovery shares are valid" in self.debug.wait_layout().text_content()
        self.debug.press_yes()

    def warning_slip39_dryrun_mismatch(self) -> BRGeneratorType:
        br = yield
        assert br.code == B.Warning
        assert "do not match" in self.debug.wait_layout().text_content()
        self.debug.press_yes()

    def warning_bip39_dryrun_mismatch(self) -> BRGeneratorType:
        br = yield
        assert br.code == B.Warning
        assert "does not match" in self.debug.wait_layout().text_content()
        self.debug.press_yes()

    def success_more_shares_needed(
        self, count_needed: int | None = None
    ) -> BRGeneratorType:
        yield
        assert (
            "1 more share needed" in self.debug.wait_layout().text_content().lower()
            or "more shares needed" in self.debug.wait_layout().text_content().lower()
        )
        if count_needed is not None:
            assert str(count_needed) in self.debug.wait_layout().text_content()
        self.debug.press_yes()

    def input_mnemonic(self, mnemonic: list[str]) -> BRGeneratorType:
        br = yield
        assert br.code == B.MnemonicInput
        assert "MnemonicKeyboard" in self.debug.wait_layout().all_components()
        for index, word in enumerate(mnemonic):
            if self.debug.model == "Safe 3":
                assert f"WORD {index + 1}" in self.debug.wait_layout().title()
            else:
                assert (
                    f"Type word {index + 1}" in self.debug.wait_layout().text_content()
                )
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
        assert self.debug.wait_layout().title() == "CONFIRM DATA"
        assert "Size:" in self.debug.wait_layout().text_content()
        if info:
            self.debug.press_info()
        elif cancel:
            self.debug.press_no()
        else:
            self.debug.press_yes()

    def paginate_data(self) -> BRGeneratorType:
        br = yield
        assert self.debug.wait_layout().title() == "CONFIRM DATA"
        assert br.pages is not None
        for i in range(br.pages):
            self.debug.wait_layout()
            if i < br.pages - 1:
                self.debug.swipe_up()
        self.debug.press_yes()

    def paginate_data_go_back(self) -> BRGeneratorType:
        br = yield
        assert self.debug.wait_layout().title() == "CONFIRM DATA"
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

    def confirm_tx(self, cancel: bool = False, info: bool = False) -> BRGeneratorType:
        yield
        assert self.debug.wait_layout().title() == "RECIPIENT"

        if self.debug.model == "T":
            if cancel:
                self.debug.press_no()
            else:
                self.debug.press_yes()
                yield
                assert self.debug.wait_layout().title() == "SUMMARY"
                assert "Maximum fee:" in self.debug.wait_layout().text_content()
                if info:
                    self.debug.press_info(wait=True)
                    assert "Gas limit:" in self.debug.wait_layout().text_content()
                    assert "Gas price:" in self.debug.wait_layout().text_content()
                    self.debug.press_no(wait=True)
                self.debug.press_yes()
        else:
            if cancel:
                self.debug.press_left()
            else:
                self.debug.press_right()
                assert "Maximum fee:" in self.debug.wait_layout().text_content()
                if info:
                    self.debug.press_right(wait=True)
                    assert "Gas limit:" in self.debug.wait_layout().text_content()
                    self.debug.press_right(wait=True)
                    assert "Gas price:" in self.debug.wait_layout().text_content()
                    self.debug.press_left(wait=True)
                    self.debug.press_left(wait=True)
                self.debug.press_middle()
