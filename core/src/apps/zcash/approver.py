from typing import TYPE_CHECKING

from apps.bitcoin.sign_tx import approvers

from .layout import UiConfirmOrchardOutput, UiConfirmTransparentOutput

if TYPE_CHECKING:
    from typing import Awaitable
    from trezor.messages import ZcashOrchardInput, ZcashOrchardOutput, TxOutput


class ZcashApprover(approvers.BasicApprover):
    def __init__(self, *args, **kwargs):
        self.orchard_balance = 0
        super().__init__(*args, **kwargs)

    def confirm_output(self, txo: TxOutput) -> Awaitable[None]:  # type: ignore [awaitable-is-generator]
        return (yield UiConfirmTransparentOutput(txo, self.coin))

    def add_orchard_input(self, txi: ZcashOrchardInput) -> None:
        self.total_in += txi.value
        self.orchard_balance += txi.value

    def add_orchard_change_output(self, txo: ZcashOrchardOutput) -> None:
        self.change_count += 1
        self.total_out += txo.amount
        self.change_out += txo.amount
        self.orchard_balance -= txo.amount

    def add_orchard_external_output(
        self, txo: ZcashOrchardOutput
    ) -> Awaitable[None]:  # type: ignore [awaitable-is-generator]
        self.total_out += txo.amount
        self.orchard_balance -= txo.amount
        return (yield UiConfirmOrchardOutput(txo, self.coin))
