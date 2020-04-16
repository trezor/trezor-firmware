from micropython import const

from trezor.messages import FailureType
from trezor.messages.TxInputType import TxInputType
from trezor.messages.TxOutputType import TxOutputType
from trezor.utils import ensure

from apps.wallet.sign_tx import multisig
from apps.wallet.sign_tx.common import SigningError

if False:
    from typing import Union

# the number of bip32 levels used in a wallet (chain and address)
_BIP32_WALLET_DEPTH = const(2)


class MatchChecker:
    """
    MatchCheckers are used to identify the change-output in a transaction. An output is a change-output
    if it has certain matching attributes with all inputs.
    1. When inputs are first processed, add_input() is called on each one to determine if they all match.
    2. Outputs are tested using output_matches() to tell whether they are admissible as a change-output.
    3. Before signing each input, check_input() is used to ensure that the attribute has not changed.
    """

    MISMATCH = object()
    UNDEFINED = object()

    def __init__(self) -> None:
        self.attribute = self.UNDEFINED  # type: object
        self.read_only = False  # Failsafe to ensure that add_input() is not accidentally called after output_matches().

    def attribute_from_tx(self, txio: Union[TxInputType, TxOutputType]) -> object:
        # Return the attribute from the txio, which is to be used for matching.
        # If the txio is invalid for matching, then return an object which
        # evaluates as a boolean False.
        raise NotImplementedError

    def add_input(self, txi: TxInputType) -> None:
        ensure(not self.read_only)

        if self.attribute is self.MISMATCH:
            return  # There was a mismatch in previous inputs.

        added_attribute = self.attribute_from_tx(txi)
        if not added_attribute:
            self.attribute = self.MISMATCH  # The added input is invalid for matching.
        elif self.attribute is self.UNDEFINED:
            self.attribute = added_attribute  # This is the first input.
        elif self.attribute != added_attribute:
            self.attribute = self.MISMATCH

    def check_input(self, txi: TxInputType) -> None:
        if self.attribute is self.MISMATCH:
            return  # There was already a mismatch when adding inputs, ignore it now.

        # All added inputs had a matching attribute, allowing a change-output.
        # Ensure that this input still has the same attribute.
        if self.attribute != self.attribute_from_tx(txi):
            raise SigningError(
                FailureType.ProcessError, "Transaction has changed during signing"
            )

    def output_matches(self, txo: TxOutputType) -> bool:
        self.read_only = True

        if self.attribute is self.MISMATCH:
            return False

        return self.attribute_from_tx(txo) == self.attribute


class WalletPathChecker(MatchChecker):
    def attribute_from_tx(self, txio: Union[TxInputType, TxOutputType]) -> object:
        if not txio.address_n:
            return None
        return txio.address_n[:-_BIP32_WALLET_DEPTH]


class MultisigFingerprintChecker(MatchChecker):
    def attribute_from_tx(self, txio: Union[TxInputType, TxOutputType]) -> object:
        if not txio.multisig:
            return None
        return multisig.multisig_fingerprint(txio.multisig)
