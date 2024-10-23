from micropython import const
from typing import TYPE_CHECKING

from .. import common

if TYPE_CHECKING:
    from trezor.messages import TxInput, TxOutput

# The chain id used for change.
_BIP32_CHANGE_CHAIN = const(1)

# The maximum allowed change address. This should be large enough for normal
# use and still allow to quickly brute-force the correct BIP32 path.
_BIP32_MAX_LAST_ELEMENT = const(1_000_000)


class ChangeDetector:
    def __init__(self) -> None:
        from .matchcheck import (
            MultisigFingerprintChecker,
            ScriptTypeChecker,
            WalletPathChecker,
        )

        # Checksum of multisig inputs, used to validate change-output.
        self.multisig_fingerprint = MultisigFingerprintChecker()

        # Common prefix of input paths, used to validate change-output.
        self.wallet_path = WalletPathChecker()

        # Common script type, used to validate change-output.
        self.script_type = ScriptTypeChecker()

    def add_input(self, txi: TxInput) -> None:
        if not common.input_is_external(txi):
            self.wallet_path.add_input(txi)
            self.script_type.add_input(txi)
            self.multisig_fingerprint.add_input(txi)

    def check_input(self, txi: TxInput) -> None:
        self.wallet_path.check_input(txi)
        self.script_type.check_input(txi)
        self.multisig_fingerprint.check_input(txi)

    def output_is_change(self, txo: TxOutput) -> bool:
        if txo.script_type not in common.CHANGE_OUTPUT_SCRIPT_TYPES:
            return False

        if txo.multisig and not common.multisig_uses_single_path(txo.multisig):
            # An address that uses different derivation paths for different xpubs
            # could be difficult to discover if the user did not note all the paths.
            # The reason is that each path ends with an address index, which can
            # have 1,000,000 possible values. If the address is a t-out-of-n
            # multisig, the total number of possible paths is 1,000,000^n. This can
            # be exploited by an attacker who has compromised the user's computer.
            # The attacker could randomize the address indices and then demand a
            # ransom from the user to reveal the paths. To prevent this, we require
            # that all xpubs use the same derivation path.
            return False

        return (
            self.multisig_fingerprint.output_matches(txo)
            and self.wallet_path.output_matches(txo)
            and self.script_type.output_matches(txo)
            and len(txo.address_n) >= common.BIP32_WALLET_DEPTH
            and txo.address_n[-2] <= _BIP32_CHANGE_CHAIN
            and txo.address_n[-1] <= _BIP32_MAX_LAST_ELEMENT
            and txo.amount > 0
        )
