from typing import TYPE_CHECKING

from trezor import wire
from trezortranslate import TR

from .. import layout
from .signer import Signer

if TYPE_CHECKING:
    from trezor import messages


class PlutusSigner(Signer):
    """
    The Plutus siging mode is meant for txs that involve Plutus script evaluation. The
    validation rules are less strict, but more tx items/warnings are shown to the user.
    """

    SIGNING_MODE_TITLE = TR.cardano__confirming_a_plutus_transaction

    async def _show_tx_init(self) -> None:
        await super()._show_tx_init()

        # These items should be present if a Plutus script is to be executed.
        if self.msg.script_data_hash is None:
            await layout.warn_no_script_data_hash()
        if self.msg.collateral_inputs_count == 0:
            await layout.warn_no_collateral_inputs()

        if self.msg.total_collateral is None:
            await layout.warn_unknown_total_collateral()

    async def _confirm_tx(self, tx_hash: bytes) -> None:
        msg = self.msg  # local_cache_attribute

        # super() omitted intentionally
        # We display tx hash so that experienced users can compare it to the tx hash
        # computed by a trusted device (in case the tx contains many items which are
        # tedious to check one by one on the Trezor screen).
        is_network_id_verifiable = self._is_network_id_verifiable()
        await layout.confirm_tx_details(
            msg.network_id,
            msg.protocol_magic,
            msg.ttl,
            msg.fee,
            msg.validity_interval_start,
            msg.total_collateral,
            is_network_id_verifiable,
            tx_hash,
        )

    async def _show_input(self, input: messages.CardanoTxInput) -> None:
        # super() omitted intentionally
        # The inputs are not interchangeable (because of datums), so we must show them.
        await self._show_if_showing_details(layout.confirm_input(input))

    async def _show_output_credentials(
        self, address_parameters: messages.CardanoAddressParametersType
    ) -> None:
        from ..helpers.credential import Credential, should_show_credentials

        # In ordinary txs, change outputs with matching payment and staking paths can be
        # hidden, but we need to show them in Plutus txs because of the script
        # evaluation. We at least hide the staking path if it matches the payment path.
        show_both_credentials = should_show_credentials(address_parameters)
        await layout.show_device_owned_output_credentials(
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
        from trezor.enums import CardanoCertificateType

        super()._validate_certificate(certificate)
        if certificate.type == CardanoCertificateType.STAKE_POOL_REGISTRATION:
            raise wire.ProcessError("Invalid certificate")

    def _validate_witness_request(
        self, witness_request: messages.CardanoTxWitnessRequest
    ) -> None:
        from .. import seed
        from ..helpers.paths import SCHEMA_MINT

        super()._validate_witness_request(witness_request)
        is_minting = SCHEMA_MINT.match(witness_request.path)

        # In Plutus txs, we allow minting witnesses even when the tx doesn't have token minting.
        if not (
            seed.is_shelley_path(witness_request.path)
            or seed.is_multisig_path(witness_request.path)
            or is_minting
        ):
            raise wire.ProcessError("Invalid witness request")
