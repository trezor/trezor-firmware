from micropython import const

from trezor import wire
from trezor.messages import OutputScriptType

from apps.common import safety_checks

from .. import keychain
from ..authorization import FEE_PER_ANONYMITY_DECIMALS
from . import helpers, tx_weight
from .tx_info import OriginalTxInfo, TxInfo

if False:
    from trezor.messages.SignTx import SignTx
    from trezor.messages.TxInput import TxInput
    from trezor.messages.TxOutput import TxOutput

    from apps.common.coininfo import CoinInfo

    from ..authorization import CoinJoinAuthorization


# An Approver object computes the transaction totals and either prompts the user
# to confirm transaction parameters (output addresses, amounts and fees) or uses
# an Authorization object to verify that the user authorized a transaction with
# these parameters to be executed.
class Approver:
    def __init__(self, tx: SignTx, coin: CoinInfo) -> None:
        self.coin = coin
        self.weight = tx_weight.TxWeightCalculator(tx.inputs_count, tx.outputs_count)

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

    def add_external_input(self, txi: TxInput) -> None:
        self.weight.add_input(txi)
        self.total_in += txi.amount
        self.external_in += txi.amount
        if txi.orig_hash:
            self.orig_total_in += txi.amount
            self.orig_external_in += txi.amount

    def add_change_output(self, txo: TxOutput, script_pubkey: bytes) -> None:
        self.weight.add_output(script_pubkey)
        self.total_out += txo.amount
        self.change_out += txo.amount

    def add_orig_change_output(self, txo: TxOutput) -> None:
        self.orig_total_out += txo.amount
        self.orig_change_out += txo.amount

    async def add_external_output(
        self,
        txo: TxOutput,
        script_pubkey: bytes,
        orig_txo: TxOutput | None = None,
    ) -> None:
        self.weight.add_output(script_pubkey)
        self.total_out += txo.amount

    def add_orig_external_output(self, txo: TxOutput) -> None:
        self.orig_total_out += txo.amount

    async def approve_orig_txids(
        self, tx_info: TxInfo, orig_txs: list[OriginalTxInfo]
    ) -> None:
        raise NotImplementedError

    async def approve_tx(self, tx_info: TxInfo, orig_txs: list[OriginalTxInfo]) -> None:
        raise NotImplementedError


class BasicApprover(Approver):
    # the maximum number of change-outputs allowed without user confirmation
    MAX_SILENT_CHANGE_COUNT = const(2)

    def __init__(self, tx: SignTx, coin: CoinInfo) -> None:
        super().__init__(tx, coin)
        self.change_count = 0  # the number of change-outputs

    async def add_internal_input(self, txi: TxInput) -> None:
        if not keychain.validate_path_against_script_type(self.coin, txi):
            await helpers.confirm_foreign_address(txi.address_n)

        await super().add_internal_input(txi)

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
        else:
            await helpers.confirm_output(txo, self.coin, self.amount_unit)

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
        self.our_weight = tx_weight.TxWeightCalculator(
            tx.inputs_count, tx.outputs_count
        )

        # base for coordinator fee to be multiplied by fee_per_anonymity
        self.coordinator_fee_base = 0

        # size of the current group of outputs
        self.group_size = 0

        # number of our change outputs in the current group
        self.group_our_count = 0

        # amount of each output in the current group
        self.group_amount = 0

        # flag indicating whether our outputs are gaining any anonymity
        self.anonymity = False

    async def add_internal_input(self, txi: TxInput) -> None:
        self.our_weight.add_input(txi)
        if not self.authorization.check_sign_tx_input(txi, self.coin):
            raise wire.ProcessError("Unauthorized path")

        await super().add_internal_input(txi)

    def add_change_output(self, txo: TxOutput, script_pubkey: bytes) -> None:
        super().add_change_output(txo, script_pubkey)
        self._add_output(txo, script_pubkey)
        self.our_weight.add_output(script_pubkey)
        self.group_our_count += 1

    async def add_external_output(
        self,
        txo: TxOutput,
        script_pubkey: bytes,
        orig_txo: TxOutput | None = None,
    ) -> None:
        await super().add_external_output(txo, script_pubkey, orig_txo)
        self._add_output(txo, script_pubkey)

    async def approve_orig_txids(
        self, tx_info: TxInfo, orig_txs: list[OriginalTxInfo]
    ) -> None:
        pass

    async def approve_tx(self, tx_info: TxInfo, orig_txs: list[OriginalTxInfo]) -> None:
        # The mining fee of the transaction as a whole.
        mining_fee = self.total_in - self.total_out

        # mining_fee > (coin.maxfee per byte * tx size)
        if mining_fee > (self.coin.maxfee_kb / 1000) * (self.weight.get_total() / 4):
            raise wire.ProcessError("Mining fee over threshold")

        # The maximum mining fee that the user should be paying.
        our_max_mining_fee = (
            mining_fee * self.our_weight.get_total() / self.weight.get_total()
        )

        # The coordinator fee for the user's outputs.
        our_coordinator_fee = self._get_coordinator_fee()

        # Total fees that the user is paying.
        our_fees = self.total_in - self.external_in - self.change_out

        if our_fees > our_coordinator_fee + our_max_mining_fee:
            raise wire.ProcessError("Total fee over threshold")

        # Ensure that at least one of the user's outputs is in a group with an external output.
        # Note: _get_coordinator_fee() needs to be called before checking this.
        if not self.anonymity:
            raise wire.ProcessError("No anonymity gain")

        if tx_info.tx.lock_time > 0:
            raise wire.ProcessError("nLockTime not allowed in CoinJoin")

        if not self.authorization.approve_sign_tx(tx_info.tx, our_fees):
            raise wire.ProcessError("Fees exceed authorized limit")

    # Coordinator fee calculation.

    def _get_coordinator_fee(self) -> float:
        # Add the coordinator fee for the last group of outputs.
        self._new_group(0)

        decimal_divisor: float = pow(10, FEE_PER_ANONYMITY_DECIMALS + 2)
        return (
            self.coordinator_fee_base
            * self.authorization.params.fee_per_anonymity
            / decimal_divisor
        )

    def _add_output(self, txo: TxOutput, script_pubkey: bytes) -> None:
        # Assumption: CoinJoin outputs are grouped by amount. (If this assumption is
        # not satisfied, then we will compute a lower coordinator fee, which may lead
        # us to wrongfully decline the transaction.)
        if self.group_amount != txo.amount:
            self._new_group(txo.amount)

        self.group_size += 1

    def _new_group(self, amount: int) -> None:
        # Add the base coordinator fee for the previous group of outputs.
        # Skip groups of size 1, because those must be change-outputs.
        if self.group_size > 1:
            self.coordinator_fee_base += (
                self.group_our_count * self.group_size * self.group_amount
            )

        # Check whether our outputs gained any anonymity.
        if self.group_our_count and self.group_size > self.group_our_count:
            self.anonymity = True

        self.group_size = 0
        self.group_our_count = 0
        self.group_amount = amount
