from trezor import messages, wire
from trezor.enums import CardanoCertificateType

from .. import layout, seed
from ..helpers.paths import (
    SCHEMA_MINT,
    SCHEMA_PAYMENT,
    SCHEMA_STAKING,
    WITNESS_PATH_NAME,
)
from .signer import Signer


class OrdinarySigner(Signer):
    """
    Ordinary txs are meant for usual actions, such as sending funds from addresses
    controlled by 1852' keys, dealing with staking and minting/burning tokens.
    """

    SIGNING_MODE_TITLE = "Confirming a transaction."

    def _validate_tx_init(self) -> None:
        super()._validate_tx_init()
        self._assert_tx_init_cond(self.msg.collateral_inputs_count == 0)
        self._assert_tx_init_cond(not self.msg.has_collateral_return)
        self._assert_tx_init_cond(self.msg.total_collateral is None)
        self._assert_tx_init_cond(self.msg.reference_inputs_count == 0)

    async def _confirm_tx(self, tx_hash: bytes) -> None:
        # super() omitted intentionally
        is_network_id_verifiable = self._is_network_id_verifiable()
        await layout.confirm_tx(
            self.ctx,
            self.msg.fee,
            self.msg.network_id,
            self.msg.protocol_magic,
            self.msg.ttl,
            self.msg.validity_interval_start,
            self.msg.total_collateral,
            is_network_id_verifiable,
            tx_hash=None,
        )

    def _validate_certificate(self, certificate: messages.CardanoTxCertificate) -> None:
        super()._validate_certificate(certificate)
        if certificate.type == CardanoCertificateType.STAKE_POOL_REGISTRATION:
            raise wire.ProcessError("Invalid certificate")
        if certificate.script_hash or certificate.key_hash:
            raise wire.ProcessError("Invalid certificate")

    def _validate_withdrawal(self, withdrawal: messages.CardanoTxWithdrawal) -> None:
        super()._validate_withdrawal(withdrawal)
        if withdrawal.script_hash or withdrawal.key_hash:
            raise wire.ProcessError("Invalid withdrawal")

    def _validate_witness_request(
        self, witness_request: messages.CardanoTxWitnessRequest
    ) -> None:
        super()._validate_witness_request(witness_request)
        is_minting = SCHEMA_MINT.match(witness_request.path)
        tx_has_token_minting = self.msg.minting_asset_groups_count > 0

        if not (
            seed.is_byron_path(witness_request.path)
            or seed.is_shelley_path(witness_request.path)
            or (is_minting and tx_has_token_minting)
        ):
            raise wire.ProcessError("Invalid witness request")

    async def _show_witness_request(self, witness_path: list[int]) -> None:
        # super() omitted intentionally
        # We only allow payment, staking or minting paths.
        # If the path is an unusual payment or staking path, we either fail or show the
        # path to the user depending on Trezor's configuration. If it's a minting path,
        # we always show it.
        is_payment = SCHEMA_PAYMENT.match(witness_path)
        is_staking = SCHEMA_STAKING.match(witness_path)
        is_minting = SCHEMA_MINT.match(witness_path)

        if is_minting:
            await layout.confirm_witness_request(self.ctx, witness_path)
        elif not is_payment and not is_staking:
            await self._fail_or_warn_path(witness_path, WITNESS_PATH_NAME)
        else:
            await self._show_if_showing_details(
                layout.confirm_witness_request(self.ctx, witness_path)
            )
