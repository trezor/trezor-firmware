from trezor import wire
from trezor.enums import CardanoCertificateType
from trezor.messages import (
    CardanoSignTxInit,
    CardanoTxCertificate,
    CardanoTxOutput,
    CardanoTxWithdrawal,
    CardanoTxWitnessRequest,
)

from .. import seed
from ..helpers import (
    INVALID_CERTIFICATE,
    INVALID_OUTPUT,
    INVALID_TX_SIGNING_REQUEST,
    INVALID_WITHDRAWAL,
    INVALID_WITNESS_REQUEST,
)
from ..helpers.paths import SCHEMA_MINT
from ..layout import show_multisig_transaction
from ..seed import is_multisig_path
from .signer import Signer


class MultisigSigner(Signer):
    """
    The multisig signing mode only allows signing with multisig (and minting) keys.
    """

    def __init__(
        self, ctx: wire.Context, msg: CardanoSignTxInit, keychain: seed.Keychain
    ) -> None:
        super().__init__(ctx, msg, keychain)

    def _validate_tx_signing_request(self) -> None:
        super()._validate_tx_signing_request()
        if (
            self.msg.collateral_inputs_count != 0
            or self.msg.required_signers_count != 0
        ):
            raise INVALID_TX_SIGNING_REQUEST

    async def _show_tx_signing_request(self) -> None:
        await show_multisig_transaction(self.ctx)
        await super()._show_tx_signing_request()

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
            is_network_id_verifiable,
            tx_hash=None,
        )

    def _validate_output(self, output: messages.CardanoTxOutput) -> None:
        super()._validate_output(output)
        if output.address_parameters is not None:
            raise INVALID_OUTPUT

    def _validate_certificate(self, certificate: CardanoTxCertificate) -> None:
        super()._validate_certificate(certificate)
        if certificate.type == CardanoCertificateType.STAKE_POOL_REGISTRATION:
            raise INVALID_CERTIFICATE
        if certificate.path or certificate.key_hash:
            raise INVALID_CERTIFICATE

    def _validate_withdrawal(self, withdrawal: CardanoTxWithdrawal) -> None:
        super()._validate_withdrawal(withdrawal)
        if withdrawal.path or withdrawal.key_hash:
            raise INVALID_WITHDRAWAL

    def _validate_witness_request(
        self, witness_request: CardanoTxWitnessRequest
    ) -> None:
        super()._validate_witness_request(witness_request)
        is_minting = SCHEMA_MINT.match(witness_request.path)
        transaction_has_token_minting = self.msg.minting_asset_groups_count > 0

        if not is_multisig_path(witness_request.path) and not is_minting:
            raise INVALID_WITNESS_REQUEST
        if is_minting and not transaction_has_token_minting:
            raise INVALID_WITNESS_REQUEST
