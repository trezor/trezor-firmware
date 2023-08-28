from typing import TYPE_CHECKING

from trezor.wire import ProcessError

from .signer import Signer

if TYPE_CHECKING:
    from trezor import messages


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
        msg = self.msg  # local_cache_attribute

        super()._validate_tx_init()
        for condition in (
            msg.certificates_count == 1,
            msg.withdrawals_count == 0,
            msg.minting_asset_groups_count == 0,
            msg.script_data_hash is None,
            msg.collateral_inputs_count == 0,
            msg.required_signers_count == 0,
            not msg.has_collateral_return,
            msg.total_collateral is None,
            msg.reference_inputs_count == 0,
        ):
            self._assert_tx_init_cond(condition)

    async def _confirm_tx(self, tx_hash: bytes) -> None:
        from .. import layout

        # super() omitted intentionally
        await layout.confirm_stake_pool_registration_final(
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
            raise ProcessError("Invalid output")

    def _should_show_output(self, output: messages.CardanoTxOutput) -> bool:
        # super() omitted intentionally
        # There are no spending witnesses, it is thus safe to hide outputs.
        return False

    def _validate_certificate(self, certificate: messages.CardanoTxCertificate) -> None:
        from trezor.enums import CardanoCertificateType

        super()._validate_certificate(certificate)
        if certificate.type != CardanoCertificateType.STAKE_POOL_REGISTRATION:
            raise ProcessError("Invalid certificate")

    def _validate_witness_request(
        self, witness_request: messages.CardanoTxWitnessRequest
    ) -> None:
        from ..helpers.paths import SCHEMA_STAKING_ANY_ACCOUNT

        super()._validate_witness_request(witness_request)
        if not (
            SCHEMA_STAKING_ANY_ACCOUNT.match(witness_request.path)
            and witness_request.path == self.pool_owner_path
        ):
            raise ProcessError(
                "Stakepool registration transaction can only contain the pool owner witness request"
            )

    def _is_network_id_verifiable(self) -> bool:
        # super() omitted intentionally
        return True
