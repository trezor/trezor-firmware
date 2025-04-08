from typing import TYPE_CHECKING

from apps.common.payment_request import PaymentRequestVerifier

if TYPE_CHECKING:
    from trezor.messages import TxOutput


class BitcoinPaymentRequestVerifier(PaymentRequestVerifier):
    def add_external_output(self, txo: TxOutput) -> None:
        # External outputs have txo.address filled by definition.
        assert txo.address is not None
        self.add_output(txo.amount, txo.address)
        self.amount += txo.amount

    def add_change_output(self, txo: TxOutput) -> None:
        # txo.address filled in by output_derive_script().
        assert txo.address is not None
        self.add_output(txo.amount, txo.address)
