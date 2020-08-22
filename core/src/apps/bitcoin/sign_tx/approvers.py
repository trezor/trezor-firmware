from micropython import const

from storage import device
from trezor import wire
from trezor.messages.SignTx import SignTx
from trezor.messages.TxInputType import TxInputType
from trezor.messages.TxOutputType import TxOutputType

from apps.common import coininfo

from .. import addresses
from ..authorization import FEE_PER_ANONYMITY_DECIMALS
from . import helpers, tx_weight

if False:
    from ..authorization import CoinJoinAuthorization

# Setting nSequence to this value for every input in a transaction disables nLockTime.
_SEQUENCE_FINAL = const(0xFFFFFFFF)


# An Approver object computes the transaction totals and either prompts the user
# to confirm transaction parameters (output addresses, amounts and fees) or uses
# an Authorization object to verify that the user authorized a transaction with
# these parameters to be executed.
class Approver:
    def __init__(self, tx: SignTx, coin: coininfo.CoinInfo) -> None:
        self.tx = tx
        self.coin = coin
        self.weight = tx_weight.TxWeightCalculator(tx.inputs_count, tx.outputs_count)
        self.min_sequence = _SEQUENCE_FINAL  # the minimum nSequence of all inputs

        # amounts
        self.total_in = 0  # sum of input amounts
        self.external_in = 0  # sum of external input amounts
        self.total_out = 0  # sum of output amounts
        self.change_out = 0  # change output amount

    async def add_internal_input(self, txi: TxInputType) -> None:
        self.weight.add_input(txi)
        self.total_in += txi.amount
        self.min_sequence = min(self.min_sequence, txi.sequence)

    def add_external_input(self, txi: TxInputType) -> None:
        self.weight.add_input(txi)
        self.total_in += txi.amount
        self.external_in += txi.amount
        self.min_sequence = min(self.min_sequence, txi.sequence)

    def add_change_output(self, txo: TxOutputType, script_pubkey: bytes) -> None:
        self.weight.add_output(script_pubkey)
        self.total_out += txo.amount
        self.change_out += txo.amount

    async def add_external_output(
        self, txo: TxOutputType, script_pubkey: bytes
    ) -> None:
        self.weight.add_output(script_pubkey)
        self.total_out += txo.amount

    async def approve_tx(self) -> None:
        raise NotImplementedError


class BasicApprover(Approver):
    # the maximum number of change-outputs allowed without user confirmation
    MAX_SILENT_CHANGE_COUNT = const(2)

    def __init__(self, tx: SignTx, coin: coininfo.CoinInfo) -> None:
        super().__init__(tx, coin)
        self.change_count = 0  # the number of change-outputs

    async def add_internal_input(self, txi: TxInputType) -> None:
        if not addresses.validate_full_path(txi.address_n, self.coin, txi.script_type):
            await helpers.confirm_foreign_address(txi.address_n)

        await super().add_internal_input(txi)

    def add_change_output(self, txo: TxOutputType, script_pubkey: bytes) -> None:
        super().add_change_output(txo, script_pubkey)
        self.change_count += 1

    async def add_external_output(
        self, txo: TxOutputType, script_pubkey: bytes
    ) -> None:
        await super().add_external_output(txo, script_pubkey)
        await helpers.confirm_output(txo, self.coin)

    async def approve_tx(self) -> None:
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
            if fee > 10 * fee_threshold and not device.unsafe_prompts_allowed():
                raise wire.DataError("The fee is unexpectedly large")
            await helpers.confirm_feeoverthreshold(fee, self.coin)
        if self.change_count > self.MAX_SILENT_CHANGE_COUNT:
            await helpers.confirm_change_count_over_threshold(self.change_count)
        if self.tx.lock_time > 0:
            lock_time_disabled = self.min_sequence == _SEQUENCE_FINAL
            await helpers.confirm_nondefault_locktime(
                self.tx.lock_time, lock_time_disabled
            )
        if not self.external_in:
            await helpers.confirm_total(total, fee, self.coin)
        else:
            await helpers.confirm_joint_total(spending, total, self.coin)


class CoinJoinApprover(Approver):
    def __init__(
        self, tx: SignTx, coin: coininfo.CoinInfo, authorization: CoinJoinAuthorization
    ) -> None:
        super().__init__(tx, coin)
        self.authorization = authorization

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

    async def add_internal_input(self, txi: TxInputType) -> None:
        self.our_weight.add_input(txi)
        if not self.authorization.check_sign_tx_input(txi, self.coin):
            raise wire.ProcessError("Unauthorized path")

        await super().add_internal_input(txi)

    def add_change_output(self, txo: TxOutputType, script_pubkey: bytes) -> None:
        super().add_change_output(txo, script_pubkey)
        self._add_output(txo, script_pubkey)
        self.our_weight.add_output(script_pubkey)
        self.group_our_count += 1

    async def add_external_output(
        self, txo: TxOutputType, script_pubkey: bytes
    ) -> None:
        await super().add_external_output(txo, script_pubkey)
        self._add_output(txo, script_pubkey)

    async def approve_tx(self) -> None:
        # Ensure that at least one of the user's outputs is in a group with an external output.
        if not self.anonymity:
            raise wire.ProcessError("No anonymity gain")

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

        if self.tx.lock_time > 0:
            raise wire.ProcessError("nLockTime not allowed in CoinJoin")

        if not self.authorization.approve_sign_tx(self.tx, our_fees):
            raise wire.ProcessError("Fees exceed authorized limit")

    # Coordinator fee calculation.

    def _get_coordinator_fee(self) -> float:
        # Add the coordinator fee for the last group of outputs.
        self._new_group(0)

        return (
            self.coordinator_fee_base
            * self.authorization.fee_per_anonymity
            / pow(10, FEE_PER_ANONYMITY_DECIMALS + 2)
        )

    def _add_output(self, txo: TxOutputType, script_pubkey: bytes):
        # Assumption: CoinJoin outputs are grouped by amount. (If this assumption is
        # not satisfied, then we will compute a lower coordinator fee, which may lead
        # us to wrongfully decline the transaction.)
        if self.group_amount != txo.amount:
            self._new_group(txo.amount)

        self.group_size += 1

    def _new_group(self, amount: int):
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
