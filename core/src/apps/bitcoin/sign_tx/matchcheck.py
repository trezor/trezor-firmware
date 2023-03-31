from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any, Generic, TypeVar

    from trezor.messages import TxInput, TxOutput

    from apps.common.paths import Bip32Path

    T = TypeVar("T")
else:
    # typechecker cheat: Generic[T] will be `object` which is a valid parent type
    Generic = [object]
    T = 0


class MatchChecker(Generic[T]):
    """
    MatchCheckers are used to identify the change-output in a transaction. An output is
    a change-output if it has a certain matching attribute with all inputs.
    1. When inputs are first processed, add_input() is called on each one to determine
       if they all match.
    2. Outputs are tested using output_matches() to tell whether they are admissible as
       a change-output.
    3. Before signing each input, check_input() is used to ensure that the attribute has
       not changed.

    There are two possible paths:

    (a) If all inputs match on the attribute, the matching value is stored. Every output
        that matches the stored value is admissible as a change-output.

    (b) If some inputs do not match, a special value MISMATCH is stored. When the
        matcher is in this state, _no outputs_ are admissible as change-outputs.
        check_input() is a no-op in this case: if there is no matching attribute to
        check against, we cannot detect modifications.
    """

    MISMATCH = object()
    UNDEFINED = object()

    def __init__(self) -> None:
        self.attribute: object | T = self.UNDEFINED
        self.read_only = False  # Failsafe to ensure that add_input() is not accidentally called after output_matches().

    def attribute_from_tx(self, txio: TxInput | TxOutput) -> T:
        # Return the attribute from the txio, which is to be used for matching.
        # If the txio is invalid for matching, then return None.
        raise NotImplementedError

    def add_input(self, txi: TxInput) -> None:
        from trezor.utils import ensure

        ensure(not self.read_only)

        if self.attribute is self.MISMATCH:
            return  # There was a mismatch in previous inputs.

        added_attribute = self.attribute_from_tx(txi)
        if added_attribute is None:
            self.attribute = self.MISMATCH  # The added input is invalid for matching.
        elif self.attribute is self.UNDEFINED:
            self.attribute = added_attribute  # This is the first input.
        elif self.attribute != added_attribute:
            self.attribute = self.MISMATCH

    def check_input(self, txi: TxInput) -> None:
        from trezor import wire

        if self.attribute is self.MISMATCH:
            return  # There was already a mismatch when adding inputs, ignore it now.

        # All added inputs had a matching attribute, allowing a change-output.
        # Ensure that this input still has the same attribute.
        if self.attribute != self.attribute_from_tx(txi):
            raise wire.ProcessError("Transaction has changed during signing")

    def output_matches(self, txo: TxOutput) -> bool:
        self.read_only = True

        if self.attribute is self.MISMATCH:
            return False

        return self.attribute_from_tx(txo) == self.attribute


class WalletPathChecker(MatchChecker):
    def attribute_from_tx(self, txio: TxInput | TxOutput) -> Any:
        from ..common import BIP32_WALLET_DEPTH

        if len(txio.address_n) <= BIP32_WALLET_DEPTH:
            return None
        return txio.address_n[:-BIP32_WALLET_DEPTH]

    def get_path(self) -> Bip32Path | None:
        if isinstance(self.attribute, list):
            return self.attribute
        return None


class MultisigFingerprintChecker(MatchChecker):
    def attribute_from_tx(self, txio: TxInput | TxOutput) -> Any:
        from .. import multisig

        if not txio.multisig:
            return None
        return multisig.multisig_fingerprint(txio.multisig)


class ScriptTypeChecker(MatchChecker):
    def attribute_from_tx(self, txio: TxInput | TxOutput) -> Any:
        from trezor.enums import InputScriptType
        from trezor.messages import TxOutput

        from ..common import CHANGE_OUTPUT_TO_INPUT_SCRIPT_TYPES

        if TxOutput.is_type_of(txio):
            script_type = CHANGE_OUTPUT_TO_INPUT_SCRIPT_TYPES[txio.script_type]
        else:
            script_type = txio.script_type

        # SPENDMULTISIG is used only for non-SegWit and is effectively the same as SPENDADDRESS.
        # For SegWit inputs and outputs multisig is indicated by the presence of the multisig
        # structure. For both SegWit and non-SegWit we can rely on MultisigFingerprintChecker to
        # check the multisig structure.
        if script_type == InputScriptType.SPENDMULTISIG:
            script_type = InputScriptType.SPENDADDRESS

        return script_type
