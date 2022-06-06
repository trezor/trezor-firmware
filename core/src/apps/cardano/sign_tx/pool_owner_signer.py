from trezor import messages, wire
from trezor.enums import CardanoCertificateType

from .. import layout
from ..helpers.paths import SCHEMA_STAKING_ANY_ACCOUNT
from .signer import Signer


class PoolOwnerSigner(Signer):
    """
    We have a separate tx signing flow for stake pool registration because it's a
    transaction where the witnessable entries (i.e. inputs, withdrawals, etc.) are not
    supposed to be controlled by the HW wallet, which means the user is vulnerable to
    unknowingly supplying a witness for an UTXO or other tx entry they think is external,
    resulting in the co-signers gaining control over their funds (Something SLIP-0019 is
    dealing with for BTC but no similar standard is currently available for Cardano).
    Hence we completely forbid witnessing inputs and other entries of the transaction
    except the stake pool certificate itself and we provide a witness only to the user's
    staking key in the list of pool owners.
    """

    SIGNING_MODE_TITLE = "Confirming pool registration as owner."

    def _validate_tx_init(self) -> None:
        super()._validate_tx_init()
        self._assert_tx_init_cond(self.msg.certificates_count == 1)
        self._assert_tx_init_cond(self.msg.withdrawals_count == 0)
        self._assert_tx_init_cond(self.msg.minting_asset_groups_count == 0)
        self._assert_tx_init_cond(self.msg.script_data_hash is None)
        self._assert_tx_init_cond(self.msg.collateral_inputs_count == 0)
        self._assert_tx_init_cond(self.msg.required_signers_count == 0)
        self._assert_tx_init_cond(not self.msg.has_collateral_return)
        self._assert_tx_init_cond(self.msg.total_collateral is None)
        self._assert_tx_init_cond(self.msg.reference_inputs_count == 0)

    async def _confirm_tx(self, tx_hash: bytes) -> None:
        # super() omitted intentionally
        await layout.confirm_stake_pool_registration_final(
            self.ctx,
            self.msg.protocol_magic,
            self.msg.ttl,
            self.msg.validity_interval_start,
        )

    def _validate_output(self, output: messages.CardanoTxOutput) -> None:
        super()._validate_output(output)
        if (
            output.address_parameters is not None
            or output.datum_hash is not None
            or output.inline_datum_size > 0
            or output.reference_script_size > 0
        ):
            raise wire.ProcessError("Invalid output")

    def _should_show_output(self, output: messages.CardanoTxOutput) -> bool:
        # super() omitted intentionally
        # There are no spending witnesses, it is thus safe to hide outputs.
        return False

    def _validate_certificate(self, certificate: messages.CardanoTxCertificate) -> None:
        super()._validate_certificate(certificate)
        if certificate.type != CardanoCertificateType.STAKE_POOL_REGISTRATION:
            raise wire.ProcessError("Invalid certificate")

    def _validate_witness_request(
        self, witness_request: messages.CardanoTxWitnessRequest
    ) -> None:
        super()._validate_witness_request(witness_request)
        if not SCHEMA_STAKING_ANY_ACCOUNT.match(witness_request.path):
            raise wire.ProcessError(
                "Stakepool registration transaction can only contain staking witnesses"
            )

    def _is_network_id_verifiable(self) -> bool:
        # super() omitted intentionally
        return True
