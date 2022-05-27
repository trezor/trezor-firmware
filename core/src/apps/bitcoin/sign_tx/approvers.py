from micropython import const
from typing import TYPE_CHECKING

from trezor import wire
from trezor.enums import OutputScriptType
from trezor.ui.components.common.confirm import INFO

from apps.common import safety_checks

from ..authorization import FEE_RATE_DECIMALS
from ..common import input_is_external_unverified
from ..keychain import validate_path_against_script_type
from . import helpers, tx_weight
from .payment_request import PaymentRequestVerifier
from .tx_info import OriginalTxInfo, TxInfo

if TYPE_CHECKING:
    from trezor.messages import SignTx
    from trezor.messages import TxInput
    from trezor.messages import TxOutput
    from trezor.messages import TxAckPaymentRequest

    from apps.common.coininfo import CoinInfo
    from apps.common.keychain import Keychain

    from ..authorization import CoinJoinAuthorization


# An Approver object computes the transaction totals and either prompts the user
# to confirm transaction parameters (output addresses, amounts and fees) or uses
# an Authorization object to verify that the user authorized a transaction with
# these parameters to be executed.
class Approver:
    def __init__(self, tx: SignTx, coin: CoinInfo) -> None:
        self.coin = coin
        self.weight = tx_weight.TxWeightCalculator()
        self.payment_req_verifier: PaymentRequestVerifier | None = None
        self.show_payment_req_details = False

        # amounts in the current transaction
        self.total_in = 0  # sum of input amounts
        self.external_in = 0  # sum of external input amounts
        self.total_out = 0  # sum of output amounts
        self.change_out = 0  # sum of change output amounts

        # amounts in original transactions when this is a replacement transaction
        self.orig_total_in = 0  # sum of original input amounts
        self.orig_external_in = 0  # sum of original external input amounts
        self.orig_total_out = 0  # sum of original output amounts
        self.orig_change_out = 0  # sum of original change output amounts

        self.amount_unit = tx.amount_unit
        self.has_unverified_external_input = False

    def is_payjoin(self) -> bool:
        # A PayJoin is a replacement transaction which manipulates the external inputs of the
        # original transaction. A replacement transaction is not allowed to remove any inputs from
        # the original, so the condition below is equivalent to external_in > orig_external_in.
        return self.external_in != self.orig_external_in

    async def add_internal_input(self, txi: TxInput) -> None:
        self.weight.add_input(txi)
        self.total_in += txi.amount
        if txi.orig_hash:
            self.orig_total_in += txi.amount

    def check_internal_input(self, txi: TxInput) -> None:
        pass

    def add_external_input(self, txi: TxInput) -> None:
        self.weight.add_input(txi)
        self.total_in += txi.amount
        if txi.orig_hash:
            self.orig_total_in += txi.amount

        if input_is_external_unverified(txi):
            self.has_unverified_external_input = True
            if safety_checks.is_strict():
                raise wire.ProcessError("Unverifiable external input.")
        else:
            self.external_in += txi.amount
            if txi.orig_hash:
                self.orig_external_in += txi.amount

    def _add_output(self, txo: TxOutput, script_pubkey: bytes) -> None:
        self.weight.add_output(script_pubkey)
        self.total_out += txo.amount

    async def add_payment_request(
        self, msg: TxAckPaymentRequest, keychain: Keychain
    ) -> None:
        self.finish_payment_request()
        self.payment_req_verifier = PaymentRequestVerifier(msg, self.coin, keychain)

    def finish_payment_request(self) -> None:
        if self.payment_req_verifier:
            self.payment_req_verifier.verify()
        self.payment_req_verifier = None
        self.show_payment_req_details = False

    def add_change_output(self, txo: TxOutput, script_pubkey: bytes) -> None:
        self._add_output(txo, script_pubkey)
        self.change_out += txo.amount
        if self.payment_req_verifier:
            self.payment_req_verifier.add_change_output(txo)

    def add_orig_change_output(self, txo: TxOutput) -> None:
        self.orig_total_out += txo.amount
        self.orig_change_out += txo.amount

    async def add_external_output(
        self,
        txo: TxOutput,
        script_pubkey: bytes,
        orig_txo: TxOutput | None = None,
    ) -> None:
        self._add_output(txo, script_pubkey)
        if self.payment_req_verifier:
            self.payment_req_verifier.add_external_output(txo)

    def add_orig_external_output(self, txo: TxOutput) -> None:
        self.orig_total_out += txo.amount

    async def approve_orig_txids(
        self, tx_info: TxInfo, orig_txs: list[OriginalTxInfo]
    ) -> None:
        raise NotImplementedError

    async def approve_tx(self, tx_info: TxInfo, orig_txs: list[OriginalTxInfo]) -> None:
        self.finish_payment_request()


class BasicApprover(Approver):
    # the maximum number of change-outputs allowed without user confirmation
    MAX_SILENT_CHANGE_COUNT = const(2)

    def __init__(self, tx: SignTx, coin: CoinInfo) -> None:
        super().__init__(tx, coin)
        self.change_count = 0  # the number of change-outputs
        self.foreign_address_confirmed = False

    async def add_internal_input(self, txi: TxInput) -> None:
        if not validate_path_against_script_type(self.coin, txi):
            await helpers.confirm_foreign_address(txi.address_n)
            self.foreign_address_confirmed = True

        await super().add_internal_input(txi)

    def check_internal_input(self, txi: TxInput) -> None:
        # Sanity check not critical for security.
        # The main reason for this is that we are not comfortable with using the same private key
        # in multiple signatures schemes (ECDSA and Schnorr) and we want to be sure that the user
        # went through a warning screen before we sign the input.
        if (
            not validate_path_against_script_type(self.coin, txi)
            and not self.foreign_address_confirmed
        ):
            raise wire.ProcessError("Transaction has changed during signing")

    def add_change_output(self, txo: TxOutput, script_pubkey: bytes) -> None:
        super().add_change_output(txo, script_pubkey)
        self.change_count += 1

    async def add_external_output(
        self,
        txo: TxOutput,
        script_pubkey: bytes,
        orig_txo: TxOutput | None = None,
    ) -> None:
        await super().add_external_output(txo, script_pubkey, orig_txo)

        if orig_txo:
            if txo.amount < orig_txo.amount:
                # Replacement transactions may need to decrease the value of external outputs to
                # bump the fee. This is needed if the original transaction transfers the entire
                # account balance ("Send Max").
                if self.is_payjoin():
                    # In case of PayJoin the above could be used to increase other external
                    # outputs, which would create too much UI complexity.
                    raise wire.ProcessError(
                        "Reducing original output amounts is not supported."
                    )
                await helpers.confirm_modify_output(
                    txo, orig_txo, self.coin, self.amount_unit
                )
            elif txo.amount > orig_txo.amount:
                # PayJoin transactions may increase the value of external outputs without
                # confirmation, because approve_tx() together with the branch above ensures that
                # the increase is paid by external inputs.
                if not self.is_payjoin():
                    raise wire.ProcessError(
                        "Increasing original output amounts is not supported."
                    )

        if self.orig_total_in:
            # Skip output confirmation for replacement transactions,
            # but don't allow adding new OP_RETURN outputs.
            if txo.script_type == OutputScriptType.PAYTOOPRETURN and not orig_txo:
                raise wire.ProcessError(
                    "Adding new OP_RETURN outputs in replacement transactions is not supported."
                )
        elif txo.payment_req_index is None or self.show_payment_req_details:
            # Ask user to confirm output, unless it is part of a payment
            # request, which gets confirmed separately.
            await helpers.confirm_output(txo, self.coin, self.amount_unit)

    async def add_payment_request(
        self, msg: TxAckPaymentRequest, keychain: Keychain
    ) -> None:
        await super().add_payment_request(msg, keychain)
        if msg.amount is None:
            raise wire.DataError("Missing payment request amount.")

        result = await helpers.confirm_payment_request(msg, self.coin, self.amount_unit)
        self.show_payment_req_details = result is INFO

    async def approve_orig_txids(
        self, tx_info: TxInfo, orig_txs: list[OriginalTxInfo]
    ) -> None:
        if not orig_txs:
            return

        if self.is_payjoin():
            description = "PayJoin"
        elif tx_info.rbf_disabled() and any(
            not orig.rbf_disabled() for orig in orig_txs
        ):
            description = "Finalize transaction"
        elif len(orig_txs) > 1:
            description = "Meld transactions"
        else:
            description = "Update transaction"

        for orig in orig_txs:
            await helpers.confirm_replacement(description, orig.orig_hash)

    async def approve_tx(self, tx_info: TxInfo, orig_txs: list[OriginalTxInfo]) -> None:
        await super().approve_tx(tx_info, orig_txs)

        if self.has_unverified_external_input:
            await helpers.confirm_unverified_external_input()

        fee = self.total_in - self.total_out

        # some coins require negative fees for reward TX
        if fee < 0 and not self.coin.negative_fee:
            raise wire.NotEnoughFunds("Not enough funds")

        total = self.total_in - self.change_out
        spending = total - self.external_in
        # fee_threshold = (coin.maxfee per byte * tx size)
        fee_threshold = (self.coin.maxfee_kb / 1000) * (self.weight.get_total() / 4)

        # fee > (coin.maxfee per byte * tx size)
        if fee > fee_threshold:
            if fee > 10 * fee_threshold and safety_checks.is_strict():
                raise wire.DataError("The fee is unexpectedly large")
            await helpers.confirm_feeoverthreshold(fee, self.coin, self.amount_unit)

        if self.change_count > self.MAX_SILENT_CHANGE_COUNT:
            await helpers.confirm_change_count_over_threshold(self.change_count)

        if orig_txs:
            # Replacement transaction.
            orig_spending = (
                self.orig_total_in - self.orig_change_out - self.orig_external_in
            )
            orig_fee = self.orig_total_in - self.orig_total_out

            if fee < 0 or orig_fee < 0:
                raise wire.ProcessError(
                    "Negative fees not supported in transaction replacement."
                )

            # Replacement transactions are only allowed to make amendments which
            # do not increase the amount that we are spending on external outputs.
            # In other words, the total amount being sent out of the wallet must
            # not increase by more than the fee difference (so additional funds
            # can only go towards the fee, which is confirmed by the user).
            if spending - orig_spending > fee - orig_fee:
                raise wire.ProcessError("Invalid replacement transaction.")

            # Replacement transactions must not change the effective nLockTime.
            lock_time = 0 if tx_info.lock_time_disabled() else tx_info.tx.lock_time
            for orig in orig_txs:
                orig_lock_time = 0 if orig.lock_time_disabled() else orig.tx.lock_time
                if lock_time != orig_lock_time:
                    raise wire.ProcessError(
                        "Original transactions must have same effective nLockTime as replacement transaction."
                    )

            if not self.is_payjoin():
                # Not a PayJoin: Show the actual fee difference, since any difference in the fee is
                # coming entirely from the user's own funds and from decreases of external outputs.
                # We consider the decreases as belonging to the user.
                await helpers.confirm_modify_fee(
                    fee - orig_fee, fee, self.coin, self.amount_unit
                )
            elif spending > orig_spending:
                # PayJoin and user is spending more: Show the increase in the user's contribution
                # to the fee, ignoring any contribution from external inputs. Decreasing of
                # external outputs is not allowed in PayJoin, so there is no need to handle those.
                await helpers.confirm_modify_fee(
                    spending - orig_spending, fee, self.coin, self.amount_unit
                )
            else:
                # PayJoin and user is not spending more: When new external inputs are involved and
                # the user is paying less, the scenario can be open to multiple interpretations and
                # the dialog would likely cause more confusion than what it's worth, see PR #1292.
                pass
        else:
            # Standard transaction.
            if tx_info.tx.lock_time > 0:
                await helpers.confirm_nondefault_locktime(
                    tx_info.tx.lock_time, tx_info.lock_time_disabled()
                )

            if not self.external_in:
                await helpers.confirm_total(total, fee, self.coin, self.amount_unit)
            else:
                await helpers.confirm_joint_total(
                    spending, total, self.coin, self.amount_unit
                )


class CoinJoinApprover(Approver):
    def __init__(
        self, tx: SignTx, coin: CoinInfo, authorization: CoinJoinAuthorization
    ) -> None:
        super().__init__(tx, coin)
        self.authorization = authorization

        if authorization.params.coin_name != tx.coin_name:
            raise wire.DataError("Coin name does not match authorization.")

        # Upper bound on the user's contribution to the weight of the transaction.
        self.our_weight = tx_weight.TxWeightCalculator()

    async def add_internal_input(self, txi: TxInput) -> None:
        self.our_weight.add_input(txi)
        if not self.authorization.check_sign_tx_input(txi, self.coin):
            raise wire.ProcessError("Unauthorized path")

        await super().add_internal_input(txi)

    def check_internal_input(self, txi: TxInput) -> None:
        # Sanity check not critical for security.
        # The main reason for this is that we are not comfortable with using the same private key
        # in multiple signatures schemes (ECDSA and Schnorr) and we want to be sure that the user
        # went through a warning screen before we sign the input.
        if not self.authorization.check_sign_tx_input(txi, self.coin):
            raise wire.ProcessError("Unauthorized path")

    def add_external_input(self, txi: TxInput) -> None:
        super().add_external_input(txi)

        # External inputs should always be verifiable in CoinJoin. This check
        # is not critical for security, we are just being cautious, because
        # CoinJoin is automated and this is not a very legitimate use-case.
        if input_is_external_unverified(txi):
            raise wire.ProcessError("Unverifiable external input.")

    def add_change_output(self, txo: TxOutput, script_pubkey: bytes) -> None:
        super().add_change_output(txo, script_pubkey)
        self.our_weight.add_output(script_pubkey)

    async def add_payment_request(
        self, msg: TxAckPaymentRequest, keychain: Keychain
    ) -> None:
        await super().add_payment_request(msg, keychain)

        if msg.recipient_name != self.authorization.params.coordinator:
            raise wire.DataError("CoinJoin coordinator mismatch in payment request.")

        if msg.memos:
            raise wire.DataError("Memos not allowed in CoinJoin payment request.")

    async def approve_orig_txids(
        self, tx_info: TxInfo, orig_txs: list[OriginalTxInfo]
    ) -> None:
        pass

    async def approve_tx(self, tx_info: TxInfo, orig_txs: list[OriginalTxInfo]) -> None:
        await super().approve_tx(tx_info, orig_txs)

        max_fee_per_vbyte = self.authorization.params.max_fee_per_kvbyte / 1000
        max_coordinator_fee_rate = (
            self.authorization.params.max_coordinator_fee_rate
            / pow(10, FEE_RATE_DECIMALS + 2)
        )

        # The mining fee of the transaction as a whole.
        mining_fee = self.total_in - self.total_out

        if mining_fee > max_fee_per_vbyte * self.weight.get_total() / 4:
            raise wire.ProcessError("Mining fee over threshold")

        # The maximum mining fee that the user should be paying.
        our_max_mining_fee = max_fee_per_vbyte * self.our_weight.get_total() / 4

        # The maximum coordination fee for the user's inputs.
        our_max_coordinator_fee = max_coordinator_fee_rate * (
            self.total_in - self.external_in
        )

        # Total fees that the user is paying.
        our_fees = self.total_in - self.external_in - self.change_out

        if our_fees > our_max_coordinator_fee + our_max_mining_fee:
            raise wire.ProcessError("Total fee over threshold.")

        if not self.authorization.approve_sign_tx(tx_info.tx):
            raise wire.ProcessError("Exceeded number of CoinJoin rounds.")

    def _add_output(self, txo: TxOutput, script_pubkey: bytes) -> None:
        super()._add_output(txo, script_pubkey)

        # All CoinJoin outputs must be accompanied by a signed payment request.
        if txo.payment_req_index is None:
            raise wire.DataError("Missing payment request.")
