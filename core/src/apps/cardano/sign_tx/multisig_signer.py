from typing import TYPE_CHECKING

from trezor import TR
from trezor.wire import ProcessError

from .signer import Signer

if TYPE_CHECKING:
    from trezor import messages


class MultisigSigner(Signer):
    """
    The multisig signing mode only allows signing with multisig (and minting) keys.
    """

    SIGNING_MODE_TITLE = TR.cardano__confirming_a_multisig_transaction

    def _validate_tx_init(self) -> None:
        msg = self.msg  # local_cache_attribute
        _assert_tx_init_cond = self._assert_tx_init_cond  # local_cache_attribute

        super()._validate_tx_init()
        _assert_tx_init_cond(msg.collateral_inputs_count == 0)
        _assert_tx_init_cond(not msg.has_collateral_return)
        _assert_tx_init_cond(msg.total_collateral is None)
        _assert_tx_init_cond(msg.reference_inputs_count == 0)

    async def _confirm_tx(self, tx_hash: bytes) -> None:
        from .. import layout

        msg = self.msg  # local_cache_attribute

        # super() omitted intentionally
        is_network_id_verifiable = self._is_network_id_verifiable()
        await layout.confirm_tx_details(
            msg.network_id,
            msg.protocol_magic,
            msg.ttl,
            msg.fee,
            msg.validity_interval_start,
            msg.total_collateral,
            is_network_id_verifiable,
            tx_hash=None,
        )

    def _validate_output(self, output: messages.CardanoTxOutput) -> None:
        super()._validate_output(output)
        if output.address_parameters is not None:
            raise ProcessError("Invalid output")

    def _validate_certificate(self, certificate: messages.CardanoTxCertificate) -> None:
        from trezor.enums import CardanoCertificateType

        super()._validate_certificate(certificate)
        if certificate.type == CardanoCertificateType.STAKE_POOL_REGISTRATION:
            raise ProcessError("Invalid certificate")
        if certificate.path or certificate.key_hash:
            raise ProcessError("Invalid certificate")

    def _validate_withdrawal(self, withdrawal: messages.CardanoTxWithdrawal) -> None:
        super()._validate_withdrawal(withdrawal)
        if withdrawal.path or withdrawal.key_hash:
            raise ProcessError("Invalid withdrawal")

    def _validate_witness_request(
        self, witness_request: messages.CardanoTxWitnessRequest
    ) -> None:
        from .. import seed
        from ..helpers.paths import SCHEMA_MINT

        super()._validate_witness_request(witness_request)
        is_minting = SCHEMA_MINT.match(witness_request.path)
        tx_has_token_minting = self.msg.minting_asset_groups_count > 0

        if not (
            seed.is_multisig_path(witness_request.path)
            or (is_minting and tx_has_token_minting)
        ):
            raise ProcessError("Invalid witness request")
