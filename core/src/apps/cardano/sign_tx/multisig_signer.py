from trezor import messages, wire
from trezor.enums import CardanoCertificateType

from .. import layout, seed
from ..helpers.paths import SCHEMA_MINT
from .signer import Signer


class MultisigSigner(Signer):
    """
    The multisig signing mode only allows signing with multisig (and minting) keys.
    """

    SIGNING_MODE_TITLE = "Confirming a multisig transaction."

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

    def _validate_output(self, output: messages.CardanoTxOutput) -> None:
        super()._validate_output(output)
        if output.address_parameters is not None:
            raise wire.ProcessError("Invalid output")

    def _validate_certificate(self, certificate: messages.CardanoTxCertificate) -> None:
        super()._validate_certificate(certificate)
        if certificate.type == CardanoCertificateType.STAKE_POOL_REGISTRATION:
            raise wire.ProcessError("Invalid certificate")
        if certificate.path or certificate.key_hash:
            raise wire.ProcessError("Invalid certificate")

    def _validate_withdrawal(self, withdrawal: messages.CardanoTxWithdrawal) -> None:
        super()._validate_withdrawal(withdrawal)
        if withdrawal.path or withdrawal.key_hash:
            raise wire.ProcessError("Invalid withdrawal")

    def _validate_witness_request(
        self, witness_request: messages.CardanoTxWitnessRequest
    ) -> None:
        super()._validate_witness_request(witness_request)
        is_minting = SCHEMA_MINT.match(witness_request.path)
        tx_has_token_minting = self.msg.minting_asset_groups_count > 0

        if not (
            seed.is_multisig_path(witness_request.path)
            or (is_minting and tx_has_token_minting)
        ):
            raise wire.ProcessError("Invalid witness request")
