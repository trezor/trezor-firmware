from micropython import const

from trezor import wire
from trezor.messages.SignTx import SignTx
from trezor.messages.TxInputType import TxInputType
from trezor.messages.TxOutputType import TxOutputType

from apps.common import coininfo

from .. import addresses
from . import helpers, tx_weight


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

        if fee < 0:
            # some coins require negative fees for reward TX
            if not self.coin.negative_fee:
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
