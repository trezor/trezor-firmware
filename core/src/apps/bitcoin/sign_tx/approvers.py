from micropython import const

from trezor import wire
from trezor.messages.SignTx import SignTx
from trezor.messages.TxInputType import TxInputType
from trezor.messages.TxOutputType import TxOutputType

from apps.common import coininfo

from .. import addresses
from . import helpers, tx_weight

if False:
    from ..authorization import CoinJoinAuthorization


class Approver:
    def __init__(self, tx: SignTx, coin: coininfo.CoinInfo) -> None:
        self.tx = tx
        self.coin = coin
        self.weight = tx_weight.TxWeightCalculator(tx.inputs_count, tx.outputs_count)

        # amounts
        self.total_in = 0  # sum of input amounts
        self.external_in = 0  # sum of external input amounts
        self.total_out = 0  # sum of output amounts
        self.change_out = 0  # change output amount

    async def add_internal_input(self, txi: TxInputType, amount: int) -> None:
        self.weight.add_input(txi)
        self.total_in += amount

    def add_external_input(self, txi: TxInputType) -> None:
        self.weight.add_input(txi)
        self.total_in += txi.amount
        self.external_in += txi.amount

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

    async def add_internal_input(self, txi: TxInputType, amount: int) -> None:
        if not addresses.validate_full_path(txi.address_n, self.coin, txi.script_type):
            await helpers.confirm_foreign_address(txi.address_n)

        await super().add_internal_input(txi, amount)

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

        # fee > (coin.maxfee per byte * tx size)
        if fee > (self.coin.maxfee_kb / 1000) * (self.weight.get_total() / 4):
            await helpers.confirm_feeoverthreshold(fee, self.coin)
        if self.change_count > self.MAX_SILENT_CHANGE_COUNT:
            await helpers.confirm_change_count_over_threshold(self.change_count)
        if self.tx.lock_time > 0:
            await helpers.confirm_nondefault_locktime(self.tx.lock_time)
        if not self.external_in:
            await helpers.confirm_total(total, fee, self.coin)
        else:
            await helpers.confirm_joint_total(spending, total, self.coin)


class CoinJoinApprover(Approver):
    MAX_COORDINATOR_FEE_PERCENT = 0.005

    def __init__(
        self, tx: SignTx, coin: coininfo.CoinInfo, authorization: CoinJoinAuthorization
    ) -> None:
        super().__init__(tx, coin)
        self.authorization = authorization

        # Upper bound on the user's contribution to the weight of the transaction.
        self.our_weight = tx_weight.TxWeightCalculator(
            tx.inputs_count, tx.outputs_count
        )

        self.max_fee = 0.0  # maximum coordinator fee for the user's outputs
        self.group_size = 0  # size of the current group of outputs
        self.group_our_count = 0  # number of our change outputs in the current group
        self.group_amount = 0  # amount of each output in the current group

    async def add_internal_input(self, txi: TxInputType, amount: int) -> None:
        self.our_weight.add_input(txi)
        if not self.authorization.check_sign_tx_input(txi, self.coin):
            raise wire.ProcessError("Unauthorized path")

        await super().add_internal_input(txi, amount)

    def add_change_output(self, txo: TxOutputType, script_pubkey: bytes) -> None:
        super().add_change_output(txo, script_pubkey)
        self._add_output(txo, script_pubkey)
        self.our_weight.add_output(script_pubkey)

    async def add_external_output(
        self, txo: TxOutputType, script_pubkey: bytes
    ) -> None:
        await super().add_external_output(txo, script_pubkey)
        self._add_output(txo, script_pubkey)
        self.group_our_count += 1

    async def approve_tx(self) -> None:
        # The maximum coordinator fee for the user's outputs.
        our_max_coordinator_fee = self._get_max_fee()

        # The mining fee of the transaction as a whole.
        mining_fee = self.total_in - self.total_out

        # The maximum mining fee that the user should be paying.
        our_max_mining_fee = (
            mining_fee * self.our_weight.get_total() / self.weight.get_total()
        )

        # Total fees that the user is paying.
        our_fees = self.total_in - self.external_in - self.change_out

        # mining_fee > (coin.maxfee per byte * tx size)
        if mining_fee > (self.coin.maxfee_kb / 1000) * (self.weight.get_total() / 4):
            raise wire.ProcessError("Mining fee over threshold")

        if our_fees > our_max_coordinator_fee + our_max_mining_fee:
            raise wire.ProcessError("Total fee over threshold")

        if self.tx.lock_time > 0:
            raise wire.ProcessError("nLockTime not allowed in CoinJoin")

        if not self.authorization.check_sign_tx(self.tx, our_fees):
            raise wire.ProcessError("Unauthorized CoinJoin fee or amount")

    # Coordinator fee calculation.

    def _get_max_fee(self) -> float:
        # Add the coordinator fee for the last group of outputs.
        self._new_group(0)

        return self.max_fee

    def _add_output(self, txo: TxOutputType, script_pubkey: bytes):
        # Assumption: CoinJoin outputs are sorted by amount.
        if self.group_amount != txo.amount:
            self._new_group(txo.amount)

        self.group_size += 1

    def _new_group(self, amount: int):
        # Add the coordinator fee for the previous group of outputs.
        if self.group_size > 1:
            self.max_fee += (
                self.group_our_count
                * self.group_size
                * self.group_amount
                * self.MAX_COORDINATOR_FEE_PERCENT
                / 100
            )

        self.group_size = 0
        self.group_our_count = 0
        self.group_amount = amount
