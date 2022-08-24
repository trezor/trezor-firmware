from trezor import messages, wire
from trezor.enums import CardanoCertificateType

from .. import layout, seed
from ..helpers.credential import Credential, should_show_credentials
from ..helpers.paths import SCHEMA_MINT
from .signer import Signer


class PlutusSigner(Signer):
    """
    The Plutus siging mode is meant for txs that involve Plutus script evaluation. The
    validation rules are less strict, but more tx items/warnings are shown to the user.
    """

    SIGNING_MODE_TITLE = "Confirming a Plutus transaction."

    async def _show_tx_init(self) -> None:
        await super()._show_tx_init()

        # These items should be present if a Plutus script is to be executed.
        if self.msg.script_data_hash is None:
            await layout.warn_no_script_data_hash(self.ctx)
        if self.msg.collateral_inputs_count == 0:
            await layout.warn_no_collateral_inputs(self.ctx)

        if self.msg.total_collateral is None:
            await layout.warn_unknown_total_collateral(self.ctx)

    async def _confirm_tx(self, tx_hash: bytes) -> None:
        # super() omitted intentionally
        # We display tx hash so that experienced users can compare it to the tx hash
        # computed by a trusted device (in case the tx contains many items which are
        # tedious to check one by one on the Trezor screen).
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
            tx_hash,
        )

    def _should_show_tx_hash(self) -> bool:
        # super() omitted intentionally
        # Plutus txs tend to contain a lot of opaque data, some users might
        # want to verify only the tx hash.
        return True

    async def _show_input(self, input: messages.CardanoTxInput) -> None:
        # super() omitted intentionally
        # The inputs are not interchangeable (because of datums), so we must show them.
        await self._show_if_showing_details(layout.confirm_input(self.ctx, input))

    async def _show_output_credentials(
        self, address_parameters: messages.CardanoAddressParametersType
    ) -> None:
        # In ordinary txs, change outputs with matching payment and staking paths can be
        # hidden, but we need to show them in Plutus txs because of the script
        # evaluation. We at least hide the staking path if it matches the payment path.
        show_both_credentials = should_show_credentials(address_parameters)
        await layout.show_device_owned_output_credentials(
            self.ctx,
            Credential.payment_credential(address_parameters),
            Credential.stake_credential(address_parameters),
            show_both_credentials,
        )

    def _should_show_output(self, output: messages.CardanoTxOutput) -> bool:
        # super() omitted intentionally
        # All outputs need to be shown (even device-owned), because they might influence
        # the script evaluation.
        if self._is_simple_change_output(output):
            # only display simple change outputs if showing details
            return self.should_show_details

        return True

    def _is_change_output(self, output: messages.CardanoTxOutput) -> bool:
        # super() omitted intentionally
        # In Plutus txs, we don't call device-owned outputs "change" outputs.
        return False

    def _validate_certificate(self, certificate: messages.CardanoTxCertificate) -> None:
        super()._validate_certificate(certificate)
        if certificate.type == CardanoCertificateType.STAKE_POOL_REGISTRATION:
            raise wire.ProcessError("Invalid certificate")

    def _validate_witness_request(
        self, witness_request: messages.CardanoTxWitnessRequest
    ) -> None:
        super()._validate_witness_request(witness_request)
        is_minting = SCHEMA_MINT.match(witness_request.path)

        # In Plutus txs, we allow minting witnesses even when the tx doesn't have token minting.
        if not (
            seed.is_shelley_path(witness_request.path)
            or seed.is_multisig_path(witness_request.path)
            or is_minting
        ):
            raise wire.ProcessError("Invalid witness request")
