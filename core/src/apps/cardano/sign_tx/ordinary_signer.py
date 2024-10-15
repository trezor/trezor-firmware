from typing import TYPE_CHECKING

from trezor import TR
from trezor.wire import ProcessError

from .. import layout, seed
from ..helpers.paths import SCHEMA_MINT
from .signer import Signer

if TYPE_CHECKING:
    from trezor import messages


class OrdinarySigner(Signer):
    """
    Ordinary txs are meant for usual actions, such as sending funds from addresses
    controlled by 1852' keys, dealing with staking and minting/burning tokens.
    """

    SIGNING_MODE_TITLE = TR.cardano__confirming_transction

    def __init__(
        self,
        msg: messages.CardanoSignTxInit,
        keychain: seed.Keychain,
    ):
        super().__init__(msg, keychain)
        self.is_simple_send = self._is_simple_send()
        self.is_simple_stake = self._is_simple_stake()

    def _validate_tx_init(self) -> None:
        msg = self.msg  # local_cache_attribute
        _assert_tx_init_cond = self._assert_tx_init_cond  # local_cache_attribute

        super()._validate_tx_init()
        _assert_tx_init_cond(msg.collateral_inputs_count == 0)
        _assert_tx_init_cond(not msg.has_collateral_return)
        _assert_tx_init_cond(msg.total_collateral is None)
        _assert_tx_init_cond(msg.reference_inputs_count == 0)

    def _has_advanced_features(self) -> bool:
        msg = self.msg  # local_cache_attribute
        # NOTE: witness_request_count is 1 for ordinary send, should we even include it in this function?
        return (
            msg.minting_asset_groups_count > 0
            or msg.witness_requests_count > 1
            or msg.has_auxiliary_data
        )

    def _is_simple_send(self) -> bool:
        msg = self.msg  # local_cache_attribute
        return (
            not self._has_advanced_features()
            and msg.certificates_count == 0
            and msg.outputs_count > 0
        )

    def _is_simple_stake(self) -> bool:
        msg = self.msg  # local_cache_attribute
        return (
            not self._has_advanced_features()
            and msg.certificates_count > 0
            and msg.outputs_count == 0
        )

    async def _show_tx_init(self) -> None:
        # super() omitted intentionally
        # for OrdinarySigner, we do not show the prompt to choose level of details
        if self.is_simple_send or self.is_simple_stake:
            self.should_show_details = False
        else:
            self.should_show_details = await layout.show_tx_init(
                self.SIGNING_MODE_TITLE
            )
        if not self._is_network_id_verifiable():
            await layout.warn_tx_network_unverifiable()

    async def _confirm_tx(self, tx_hash: bytes) -> None:
        msg = self.msg  # local_cache_attribute

        # super() omitted intentionally
        is_network_id_verifiable = self._is_network_id_verifiable()
        if self.should_show_details:
            await layout.confirm_tx_details(
                msg.network_id,
                msg.protocol_magic,
                msg.ttl,
                None,  # do not show fee as it is in `confirm_total`
                msg.validity_interval_start,
                msg.total_collateral,
                is_network_id_verifiable,
                tx_hash=None,
            )
        if self.is_simple_send:
            await layout.confirm_total(self.total_amount, msg.fee, msg.network_id)

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
        from ..helpers.paths import SCHEMA_PAYMENT, SCHEMA_STAKING

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
            await self._fail_or_warn_path(witness_path, "Witness path")
        else:
            await self._show_if_showing_details(
                layout.confirm_witness_request(witness_path)
            )
