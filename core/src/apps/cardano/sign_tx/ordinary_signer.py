from typing import TYPE_CHECKING

from trezor.wire import ProcessError

from .. import layout
from ..helpers.paths import SCHEMA_MINT
from .signer import Signer

if TYPE_CHECKING:
    from trezor import messages


class OrdinarySigner(Signer):
    """
    Ordinary txs are meant for usual actions, such as sending funds from addresses
    controlled by 1852' keys, dealing with staking and minting/burning tokens.
    """

    SIGNING_MODE_TITLE = "Confirming a transaction."

    def _validate_tx_init(self) -> None:
        msg = self.msg  # local_cache_attribute
        _assert_tx_init_cond = self._assert_tx_init_cond  # local_cache_attribute

        super()._validate_tx_init()
        _assert_tx_init_cond(msg.collateral_inputs_count == 0)
        _assert_tx_init_cond(not msg.has_collateral_return)
        _assert_tx_init_cond(msg.total_collateral is None)
        _assert_tx_init_cond(msg.reference_inputs_count == 0)

    async def _confirm_tx(self, tx_hash: bytes) -> None:
        msg = self.msg  # local_cache_attribute

        # super() omitted intentionally
        is_network_id_verifiable = self._is_network_id_verifiable()
        await layout.confirm_tx(
            msg.fee,
            msg.network_id,
            msg.protocol_magic,
            msg.ttl,
            msg.validity_interval_start,
            msg.total_collateral,
            is_network_id_verifiable,
            tx_hash=None,
        )

    def _validate_certificate(self, certificate: messages.CardanoTxCertificate) -> None:
        from trezor.enums import CardanoCertificateType

        super()._validate_certificate(certificate)
        if certificate.type == CardanoCertificateType.STAKE_POOL_REGISTRATION:
            raise ProcessError("Invalid certificate")
        if certificate.script_hash or certificate.key_hash:
            raise ProcessError("Invalid certificate")

    def _validate_withdrawal(self, withdrawal: messages.CardanoTxWithdrawal) -> None:
        super()._validate_withdrawal(withdrawal)
        if withdrawal.script_hash or withdrawal.key_hash:
            raise ProcessError("Invalid withdrawal")

    def _validate_witness_request(
        self, witness_request: messages.CardanoTxWitnessRequest
    ) -> None:
        from .. import seed

        super()._validate_witness_request(witness_request)
        is_minting = SCHEMA_MINT.match(witness_request.path)
        tx_has_token_minting = self.msg.minting_asset_groups_count > 0

        if not (
            seed.is_byron_path(witness_request.path)
            or seed.is_shelley_path(witness_request.path)
            or (is_minting and tx_has_token_minting)
        ):
            raise ProcessError("Invalid witness request")

    async def _show_witness_request(self, witness_path: list[int]) -> None:
        from ..helpers.paths import SCHEMA_PAYMENT, SCHEMA_STAKING, WITNESS_PATH_NAME

        # super() omitted intentionally
        # We only allow payment, staking or minting paths.
        # If the path is an unusual payment or staking path, we either fail or show the
        # path to the user depending on Trezor's configuration. If it's a minting path,
        # we always show it.
        is_payment = SCHEMA_PAYMENT.match(witness_path)
        is_staking = SCHEMA_STAKING.match(witness_path)
        is_minting = SCHEMA_MINT.match(witness_path)

        if is_minting:
            await layout.confirm_witness_request(witness_path)
        elif not is_payment and not is_staking:
            await self._fail_or_warn_path(witness_path, WITNESS_PATH_NAME)
        else:
            await self._show_if_showing_details(
                layout.confirm_witness_request(witness_path)
            )
