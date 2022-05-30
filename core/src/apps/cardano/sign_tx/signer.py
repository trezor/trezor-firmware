from micropython import const
from typing import TYPE_CHECKING

from trezor import messages, wire
from trezor.crypto import hashlib
from trezor.crypto.curve import ed25519
from trezor.enums import (
    CardanoAddressType,
    CardanoCertificateType,
    CardanoTxWitnessType,
)

from apps.common import cbor, safety_checks

from .. import addresses, auxiliary_data, certificates, layout, seed
from ..helpers import (
    ADDRESS_KEY_HASH_SIZE,
    INPUT_PREV_HASH_SIZE,
    LOVELACE_MAX_SUPPLY,
    OUTPUT_DATUM_HASH_SIZE,
    SCRIPT_DATA_HASH_SIZE,
)
from ..helpers.account_path_check import AccountPathChecker
from ..helpers.credential import Credential, should_show_credentials
from ..helpers.hash_builder_collection import HashBuilderDict, HashBuilderList
from ..helpers.paths import (
    CERTIFICATE_PATH_NAME,
    CHANGE_OUTPUT_PATH_NAME,
    CHANGE_OUTPUT_STAKING_PATH_NAME,
    POOL_OWNER_STAKING_PATH_NAME,
    SCHEMA_STAKING,
)
from ..helpers.utils import (
    derive_public_key,
    get_public_key_hash,
    validate_network_info,
    validate_stake_credential,
)

if TYPE_CHECKING:
    from typing import Any
    from apps.common.paths import PathSchema

    CardanoTxResponseType = (
        messages.CardanoTxItemAck | messages.CardanoTxWitnessResponse
    )

MINTING_POLICY_ID_LENGTH = 28
MAX_ASSET_NAME_LENGTH = 32

TX_BODY_KEY_INPUTS = const(0)
TX_BODY_KEY_OUTPUTS = const(1)
TX_BODY_KEY_FEE = const(2)
TX_BODY_KEY_TTL = const(3)
TX_BODY_KEY_CERTIFICATES = const(4)
TX_BODY_KEY_WITHDRAWALS = const(5)
TX_BODY_KEY_AUXILIARY_DATA = const(7)
TX_BODY_KEY_VALIDITY_INTERVAL_START = const(8)
TX_BODY_KEY_MINT = const(9)
TX_BODY_KEY_SCRIPT_DATA_HASH = const(11)
TX_BODY_KEY_COLLATERAL_INPUTS = const(13)
TX_BODY_KEY_REQUIRED_SIGNERS = const(14)
TX_BODY_KEY_NETWORK_ID = const(15)

POOL_REGISTRATION_CERTIFICATE_ITEMS_COUNT = 10


class Signer:
    """
    This class encapsulates the entire tx signing process. By default, most tx items are
    allowed and shown to the user. For each signing mode, there is a subclass that
    overrides some methods, usually to add more validation rules and show/hide some
    items. Each tx item is processed in a _process_xyz() method which handles validation,
    user confirmation and serialization of the tx item.
    """

    def __init__(
        self,
        ctx: wire.Context,
        msg: messages.CardanoSignTxInit,
        keychain: seed.Keychain,
    ) -> None:
        self.ctx = ctx
        self.msg = msg
        self.keychain = keychain

        self.account_path_checker = AccountPathChecker()

        # Inputs, outputs and fee are mandatory, count the number of optional fields present.
        tx_dict_items_count = 3 + sum(
            (
                msg.ttl is not None,
                msg.certificates_count > 0,
                msg.withdrawals_count > 0,
                msg.has_auxiliary_data,
                msg.validity_interval_start is not None,
                msg.minting_asset_groups_count > 0,
                msg.include_network_id,
                msg.script_data_hash is not None,
                msg.collateral_inputs_count > 0,
                msg.required_signers_count > 0,
            )
        )
        self.tx_dict: HashBuilderDict[int, Any] = HashBuilderDict(
            tx_dict_items_count, wire.ProcessError("Invalid tx signing request")
        )

    async def sign(self) -> None:
        hash_fn = hashlib.blake2b(outlen=32)
        self.tx_dict.start(hash_fn)
        with self.tx_dict:
            await self._processs_tx_init()

        tx_hash = hash_fn.digest()
        await self._confirm_tx(tx_hash)

        response_after_witness_requests = await self._process_witness_requests(tx_hash)
        await self.ctx.call(response_after_witness_requests, messages.CardanoTxHostAck)
        await self.ctx.call(
            messages.CardanoTxBodyHash(tx_hash=tx_hash), messages.CardanoTxHostAck
        )

    # signing request

    async def _processs_tx_init(self) -> None:
        self._validate_tx_init()
        await self._show_tx_init()

        inputs_list: HashBuilderList[tuple[bytes, int]] = HashBuilderList(
            self.msg.inputs_count
        )
        with self.tx_dict.add(TX_BODY_KEY_INPUTS, inputs_list):
            await self._process_inputs(inputs_list)

        outputs_list: HashBuilderList = HashBuilderList(self.msg.outputs_count)
        with self.tx_dict.add(TX_BODY_KEY_OUTPUTS, outputs_list):
            await self._process_outputs(outputs_list)

        self.tx_dict.add(TX_BODY_KEY_FEE, self.msg.fee)

        if self.msg.ttl is not None:
            self.tx_dict.add(TX_BODY_KEY_TTL, self.msg.ttl)

        if self.msg.certificates_count > 0:
            certificates_list: HashBuilderList = HashBuilderList(
                self.msg.certificates_count
            )
            with self.tx_dict.add(TX_BODY_KEY_CERTIFICATES, certificates_list):
                await self._process_certificates(certificates_list)

        if self.msg.withdrawals_count > 0:
            withdrawals_dict: HashBuilderDict[bytes, int] = HashBuilderDict(
                self.msg.withdrawals_count, wire.ProcessError("Invalid withdrawal")
            )
            with self.tx_dict.add(TX_BODY_KEY_WITHDRAWALS, withdrawals_dict):
                await self._process_withdrawals(withdrawals_dict)

        if self.msg.has_auxiliary_data:
            await self._process_auxiliary_data()

        if self.msg.validity_interval_start is not None:
            self.tx_dict.add(
                TX_BODY_KEY_VALIDITY_INTERVAL_START, self.msg.validity_interval_start
            )

        if self.msg.minting_asset_groups_count > 0:
            minting_dict: HashBuilderDict[bytes, HashBuilderDict] = HashBuilderDict(
                self.msg.minting_asset_groups_count,
                wire.ProcessError("Invalid mint token bundle"),
            )
            with self.tx_dict.add(TX_BODY_KEY_MINT, minting_dict):
                await self._process_minting(minting_dict)

        if self.msg.script_data_hash is not None:
            await self._process_script_data_hash()

        if self.msg.collateral_inputs_count > 0:
            collateral_inputs_list: HashBuilderList[
                tuple[bytes, int]
            ] = HashBuilderList(self.msg.collateral_inputs_count)
            with self.tx_dict.add(
                TX_BODY_KEY_COLLATERAL_INPUTS, collateral_inputs_list
            ):
                await self._process_collateral_inputs(collateral_inputs_list)

        if self.msg.required_signers_count > 0:
            required_signers_list: HashBuilderList[bytes] = HashBuilderList(
                self.msg.required_signers_count
            )
            with self.tx_dict.add(TX_BODY_KEY_REQUIRED_SIGNERS, required_signers_list):
                await self._process_required_signers(required_signers_list)

        if self.msg.include_network_id:
            self.tx_dict.add(TX_BODY_KEY_NETWORK_ID, self.msg.network_id)

    def _validate_tx_init(self) -> None:
        if self.msg.fee > LOVELACE_MAX_SUPPLY:
            raise wire.ProcessError("Fee is out of range!")
        validate_network_info(self.msg.network_id, self.msg.protocol_magic)

    async def _show_tx_init(self) -> None:
        if not self._is_network_id_verifiable():
            await layout.warn_tx_network_unverifiable(self.ctx)

    async def _confirm_tx(self, tx_hash: bytes) -> None:
        # Final signing confirmation is handled separately in each signing mode.
        raise NotImplementedError

    # inputs

    async def _process_inputs(
        self, inputs_list: HashBuilderList[tuple[bytes, int]]
    ) -> None:
        for _ in range(self.msg.inputs_count):
            input: messages.CardanoTxInput = await self.ctx.call(
                messages.CardanoTxItemAck(), messages.CardanoTxInput
            )
            self._validate_input(input)
            await self._show_input(input)
            inputs_list.append((input.prev_hash, input.prev_index))

    def _validate_input(self, input: messages.CardanoTxInput) -> None:
        if len(input.prev_hash) != INPUT_PREV_HASH_SIZE:
            raise wire.ProcessError("Invalid input")

    async def _show_input(self, input: messages.CardanoTxInput) -> None:
        # We never show the inputs, except for Plutus txs.
        pass

    # outputs

    async def _process_outputs(self, outputs_list: HashBuilderList) -> None:
        total_amount = 0
        for _ in range(self.msg.outputs_count):
            output: messages.CardanoTxOutput = await self.ctx.call(
                messages.CardanoTxItemAck(), messages.CardanoTxOutput
            )
            self._validate_output(output)
            await self._show_output(output)

            output_address = self._get_output_address(output)

            has_datum_hash = output.datum_hash is not None
            output_list: HashBuilderList = HashBuilderList(2 + int(has_datum_hash))
            with outputs_list.append(output_list):
                output_list.append(output_address)
                if output.asset_groups_count == 0:
                    # output structure is: [address, amount, datum_hash?]
                    output_list.append(output.amount)
                else:
                    # output structure is: [address, [amount, asset_groups], datum_hash?]
                    output_value_list: HashBuilderList = HashBuilderList(2)
                    with output_list.append(output_value_list):
                        output_value_list.append(output.amount)
                        asset_groups_dict: HashBuilderDict[
                            bytes, HashBuilderDict[bytes, int]
                        ] = HashBuilderDict(
                            output.asset_groups_count,
                            wire.ProcessError("Invalid token bundle in output"),
                        )
                        with output_value_list.append(asset_groups_dict):
                            await self._process_asset_groups(
                                asset_groups_dict,
                                output.asset_groups_count,
                                self._should_show_output(output),
                            )
                if has_datum_hash:
                    output_list.append(output.datum_hash)

            total_amount += output.amount

        if total_amount > LOVELACE_MAX_SUPPLY:
            raise wire.ProcessError("Total transaction amount is out of range!")

    def _validate_output(self, output: messages.CardanoTxOutput) -> None:
        if output.address_parameters is not None and output.address is not None:
            raise wire.ProcessError("Invalid output")

        if output.address_parameters is not None:
            addresses.validate_output_address_parameters(output.address_parameters)
            self._fail_if_strict_and_unusual(output.address_parameters)
        elif output.address is not None:
            addresses.validate_output_address(
                output.address, self.msg.protocol_magic, self.msg.network_id
            )
        else:
            raise wire.ProcessError("Invalid output")

        if output.datum_hash is not None:
            if len(output.datum_hash) != OUTPUT_DATUM_HASH_SIZE:
                raise wire.ProcessError("Invalid output datum hash")
            address_type = self._get_output_address_type(output)
            if address_type not in addresses.ADDRESS_TYPES_PAYMENT_SCRIPT:
                raise wire.ProcessError("Invalid output")

        self.account_path_checker.add_output(output)

    async def _show_output(self, output: messages.CardanoTxOutput) -> None:
        if not self._should_show_output(output):
            return

        if output.datum_hash is not None:
            await layout.warn_tx_output_contains_datum_hash(self.ctx, output.datum_hash)

        address_type = self._get_output_address_type(output)
        if (
            output.datum_hash is None
            and address_type in addresses.ADDRESS_TYPES_PAYMENT_SCRIPT
        ):
            await layout.warn_tx_output_no_datum_hash(self.ctx)

        if output.asset_groups_count > 0:
            await layout.warn_tx_output_contains_tokens(self.ctx)

        if output.address_parameters is not None:
            address = addresses.derive_human_readable(
                self.keychain,
                output.address_parameters,
                self.msg.protocol_magic,
                self.msg.network_id,
            )
            await self._show_output_credentials(output.address_parameters)
        else:
            assert output.address is not None  # _validate_output
            address = output.address

        await layout.confirm_sending(
            self.ctx,
            output.amount,
            address,
            self._is_change_output(output),
            self.msg.network_id,
        )

    async def _show_output_credentials(
        self, address_parameters: messages.CardanoAddressParametersType
    ) -> None:
        await layout.show_change_output_credentials(
            self.ctx,
            Credential.payment_credential(address_parameters),
            Credential.stake_credential(address_parameters),
        )

    def _should_show_output(self, output: messages.CardanoTxOutput) -> bool:
        """
        Determines whether the output should be shown. Extracted from _show_output because
        of readability and because the same decision is made when displaying output tokens.
        """
        if output.datum_hash is not None:
            # The `return False` case below should not be reachable when datum hash is
            # present, but let's make it explicit.
            return True

        address_type = self._get_output_address_type(output)
        if (
            output.datum_hash is None
            and address_type in addresses.ADDRESS_TYPES_PAYMENT_SCRIPT
        ):
            # Plutus script address without a datum hash is unspendable, we must show a warning.
            return True

        if output.address_parameters is not None:  # change output
            if not should_show_credentials(output.address_parameters):
                # We don't need to display simple address outputs.
                return False

        return True

    def _is_change_output(self, output: messages.CardanoTxOutput) -> bool:
        """Used only to determine what message to show to the user when confirming sending."""
        return output.address_parameters is not None

    # asset groups

    async def _process_asset_groups(
        self,
        asset_groups_dict: HashBuilderDict[bytes, HashBuilderDict[bytes, int]],
        asset_groups_count: int,
        should_show_tokens: bool,
    ) -> None:
        for _ in range(asset_groups_count):
            asset_group: messages.CardanoAssetGroup = await self.ctx.call(
                messages.CardanoTxItemAck(), messages.CardanoAssetGroup
            )
            self._validate_asset_group(asset_group)

            tokens: HashBuilderDict[bytes, int] = HashBuilderDict(
                asset_group.tokens_count,
                wire.ProcessError("Invalid token bundle in output"),
            )
            with asset_groups_dict.add(asset_group.policy_id, tokens):
                await self._process_tokens(
                    tokens,
                    asset_group.policy_id,
                    asset_group.tokens_count,
                    should_show_tokens,
                )

    def _validate_asset_group(
        self, asset_group: messages.CardanoAssetGroup, is_mint: bool = False
    ) -> None:
        INVALID_TOKEN_BUNDLE = (
            wire.ProcessError("Invalid mint token bundle")
            if is_mint
            else wire.ProcessError("Invalid token bundle in output")
        )

        if len(asset_group.policy_id) != MINTING_POLICY_ID_LENGTH:
            raise INVALID_TOKEN_BUNDLE
        if asset_group.tokens_count == 0:
            raise INVALID_TOKEN_BUNDLE

    # tokens

    async def _process_tokens(
        self,
        tokens_dict: HashBuilderDict[bytes, int],
        policy_id: bytes,
        tokens_count: int,
        should_show_tokens: bool,
    ) -> None:
        for _ in range(tokens_count):
            token: messages.CardanoToken = await self.ctx.call(
                messages.CardanoTxItemAck(), messages.CardanoToken
            )
            self._validate_token(token)
            if should_show_tokens:
                await layout.confirm_sending_token(self.ctx, policy_id, token)

            assert token.amount is not None  # _validate_token
            tokens_dict.add(token.asset_name_bytes, token.amount)

    def _validate_token(
        self, token: messages.CardanoToken, is_mint: bool = False
    ) -> None:
        INVALID_TOKEN_BUNDLE = (
            wire.ProcessError("Invalid mint token bundle")
            if is_mint
            else wire.ProcessError("Invalid token bundle in output")
        )

        if is_mint:
            if token.mint_amount is None or token.amount is not None:
                raise INVALID_TOKEN_BUNDLE
        else:
            if token.amount is None or token.mint_amount is not None:
                raise INVALID_TOKEN_BUNDLE

        if len(token.asset_name_bytes) > MAX_ASSET_NAME_LENGTH:
            raise INVALID_TOKEN_BUNDLE

    # certificates

    async def _process_certificates(self, certificates_list: HashBuilderList) -> None:
        for _ in range(self.msg.certificates_count):
            certificate: messages.CardanoTxCertificate = await self.ctx.call(
                messages.CardanoTxItemAck(), messages.CardanoTxCertificate
            )
            self._validate_certificate(certificate)
            await self._show_certificate(certificate)

            if certificate.type == CardanoCertificateType.STAKE_POOL_REGISTRATION:
                pool_parameters = certificate.pool_parameters
                assert pool_parameters is not None  # _validate_certificate

                pool_items_list: HashBuilderList = HashBuilderList(
                    POOL_REGISTRATION_CERTIFICATE_ITEMS_COUNT
                )
                with certificates_list.append(pool_items_list):
                    for item in certificates.cborize_pool_registration_init(
                        certificate
                    ):
                        pool_items_list.append(item)

                    pool_owners_list: HashBuilderList[bytes] = HashBuilderList(
                        pool_parameters.owners_count
                    )
                    with pool_items_list.append(pool_owners_list):
                        await self._process_pool_owners(
                            pool_owners_list, pool_parameters.owners_count
                        )

                    relays_list: HashBuilderList[cbor.CborSequence] = HashBuilderList(
                        pool_parameters.relays_count
                    )
                    with pool_items_list.append(relays_list):
                        await self._process_pool_relays(
                            relays_list, pool_parameters.relays_count
                        )

                    pool_items_list.append(
                        certificates.cborize_pool_metadata(pool_parameters.metadata)
                    )
            else:
                certificates_list.append(
                    certificates.cborize(self.keychain, certificate)
                )

    def _validate_certificate(self, certificate: messages.CardanoTxCertificate) -> None:
        certificates.validate(
            certificate,
            self.msg.protocol_magic,
            self.msg.network_id,
            self.account_path_checker,
        )

    async def _show_certificate(
        self, certificate: messages.CardanoTxCertificate
    ) -> None:
        if certificate.path:
            await self._fail_or_warn_if_invalid_path(
                SCHEMA_STAKING, certificate.path, CERTIFICATE_PATH_NAME
            )

        if certificate.type == CardanoCertificateType.STAKE_POOL_REGISTRATION:
            assert certificate.pool_parameters is not None
            await layout.confirm_stake_pool_parameters(
                self.ctx, certificate.pool_parameters, self.msg.network_id
            )
            await layout.confirm_stake_pool_metadata(
                self.ctx, certificate.pool_parameters.metadata
            )
        else:
            await layout.confirm_certificate(self.ctx, certificate)

    # pool owners

    async def _process_pool_owners(
        self, pool_owners_list: HashBuilderList[bytes], owners_count: int
    ) -> None:
        owners_as_path_count = 0
        for _ in range(owners_count):
            owner: messages.CardanoPoolOwner = await self.ctx.call(
                messages.CardanoTxItemAck(), messages.CardanoPoolOwner
            )
            certificates.validate_pool_owner(owner, self.account_path_checker)
            await self._show_pool_owner(owner)
            pool_owners_list.append(
                certificates.cborize_pool_owner(self.keychain, owner)
            )

            if owner.staking_key_path:
                owners_as_path_count += 1

        certificates.assert_cond(owners_as_path_count == 1)

    async def _show_pool_owner(self, owner: messages.CardanoPoolOwner) -> None:
        if owner.staking_key_path:
            await self._fail_or_warn_if_invalid_path(
                SCHEMA_STAKING, owner.staking_key_path, POOL_OWNER_STAKING_PATH_NAME
            )

        await layout.confirm_stake_pool_owner(
            self.ctx, self.keychain, owner, self.msg.protocol_magic, self.msg.network_id
        )

    # pool relays

    async def _process_pool_relays(
        self,
        relays_list: HashBuilderList[cbor.CborSequence],
        relays_count: int,
    ) -> None:
        for _ in range(relays_count):
            relay: messages.CardanoPoolRelayParameters = await self.ctx.call(
                messages.CardanoTxItemAck(), messages.CardanoPoolRelayParameters
            )
            certificates.validate_pool_relay(relay)
            relays_list.append(certificates.cborize_pool_relay(relay))

    # withdrawals

    async def _process_withdrawals(
        self, withdrawals_dict: HashBuilderDict[bytes, int]
    ) -> None:
        for _ in range(self.msg.withdrawals_count):
            withdrawal: messages.CardanoTxWithdrawal = await self.ctx.call(
                messages.CardanoTxItemAck(), messages.CardanoTxWithdrawal
            )
            self._validate_withdrawal(withdrawal)
            address_bytes = self._derive_withdrawal_address_bytes(withdrawal)
            await layout.confirm_withdrawal(
                self.ctx, withdrawal, address_bytes, self.msg.network_id
            )
            withdrawals_dict.add(address_bytes, withdrawal.amount)

    def _validate_withdrawal(self, withdrawal: messages.CardanoTxWithdrawal) -> None:
        validate_stake_credential(
            withdrawal.path,
            withdrawal.script_hash,
            withdrawal.key_hash,
            wire.ProcessError("Invalid withdrawal"),
        )

        if not 0 <= withdrawal.amount < LOVELACE_MAX_SUPPLY:
            raise wire.ProcessError("Invalid withdrawal")

        self.account_path_checker.add_withdrawal(withdrawal)

    # auxiliary data

    async def _process_auxiliary_data(self) -> None:
        data: messages.CardanoTxAuxiliaryData = await self.ctx.call(
            messages.CardanoTxItemAck(), messages.CardanoTxAuxiliaryData
        )
        auxiliary_data.validate(data)

        (
            auxiliary_data_hash,
            auxiliary_data_supplement,
        ) = auxiliary_data.get_hash_and_supplement(
            self.keychain, data, self.msg.protocol_magic, self.msg.network_id
        )
        await auxiliary_data.show(
            self.ctx,
            self.keychain,
            auxiliary_data_hash,
            data.catalyst_registration_parameters,
            self.msg.protocol_magic,
            self.msg.network_id,
        )
        self.tx_dict.add(TX_BODY_KEY_AUXILIARY_DATA, auxiliary_data_hash)

        await self.ctx.call(auxiliary_data_supplement, messages.CardanoTxHostAck)

    # minting

    async def _process_minting(
        self, minting_dict: HashBuilderDict[bytes, HashBuilderDict]
    ) -> None:
        token_minting: messages.CardanoTxMint = await self.ctx.call(
            messages.CardanoTxItemAck(), messages.CardanoTxMint
        )

        await layout.warn_tx_contains_mint(self.ctx)

        for _ in range(token_minting.asset_groups_count):
            asset_group: messages.CardanoAssetGroup = await self.ctx.call(
                messages.CardanoTxItemAck(), messages.CardanoAssetGroup
            )
            self._validate_asset_group(asset_group, is_mint=True)

            tokens: HashBuilderDict[bytes, int] = HashBuilderDict(
                asset_group.tokens_count, wire.ProcessError("Invalid mint token bundle")
            )
            with minting_dict.add(asset_group.policy_id, tokens):
                await self._process_minting_tokens(
                    tokens,
                    asset_group.policy_id,
                    asset_group.tokens_count,
                )

    # minting tokens

    async def _process_minting_tokens(
        self,
        tokens: HashBuilderDict[bytes, int],
        policy_id: bytes,
        tokens_count: int,
    ) -> None:
        for _ in range(tokens_count):
            token: messages.CardanoToken = await self.ctx.call(
                messages.CardanoTxItemAck(), messages.CardanoToken
            )
            self._validate_token(token, is_mint=True)
            await layout.confirm_token_minting(self.ctx, policy_id, token)

            assert token.mint_amount is not None  # _validate_token
            tokens.add(token.asset_name_bytes, token.mint_amount)

    # script data hash

    async def _process_script_data_hash(self) -> None:
        assert self.msg.script_data_hash is not None
        self._validate_script_data_hash()
        await layout.confirm_script_data_hash(self.ctx, self.msg.script_data_hash)
        self.tx_dict.add(TX_BODY_KEY_SCRIPT_DATA_HASH, self.msg.script_data_hash)

    def _validate_script_data_hash(self) -> None:
        assert self.msg.script_data_hash is not None
        if len(self.msg.script_data_hash) != SCRIPT_DATA_HASH_SIZE:
            raise wire.ProcessError("Invalid script data hash")

    # collateral inputs

    async def _process_collateral_inputs(
        self, collateral_inputs_list: HashBuilderList[tuple[bytes, int]]
    ) -> None:
        for _ in range(self.msg.collateral_inputs_count):
            collateral_input: messages.CardanoTxCollateralInput = await self.ctx.call(
                messages.CardanoTxItemAck(), messages.CardanoTxCollateralInput
            )
            self._validate_collateral_input(collateral_input)
            await layout.confirm_collateral_input(self.ctx, collateral_input)
            collateral_inputs_list.append(
                (collateral_input.prev_hash, collateral_input.prev_index)
            )

    def _validate_collateral_input(
        self, collateral_input: messages.CardanoTxCollateralInput
    ) -> None:
        if len(collateral_input.prev_hash) != INPUT_PREV_HASH_SIZE:
            raise wire.ProcessError("Invalid collateral input")

    # required signers

    async def _process_required_signers(
        self, required_signers_list: HashBuilderList[bytes]
    ) -> None:
        for _ in range(self.msg.required_signers_count):
            required_signer: messages.CardanoTxRequiredSigner = await self.ctx.call(
                messages.CardanoTxItemAck(), messages.CardanoTxRequiredSigner
            )
            self._validate_required_signer(required_signer)
            await layout.confirm_required_signer(self.ctx, required_signer)

            key_hash = required_signer.key_hash or get_public_key_hash(
                self.keychain, required_signer.key_path
            )
            required_signers_list.append(key_hash)

    def _validate_required_signer(
        self, required_signer: messages.CardanoTxRequiredSigner
    ) -> None:
        INVALID_REQUIRED_SIGNER = wire.ProcessError("Invalid required signer")

        if required_signer.key_hash and required_signer.key_path:
            raise INVALID_REQUIRED_SIGNER

        if required_signer.key_hash:
            if len(required_signer.key_hash) != ADDRESS_KEY_HASH_SIZE:
                raise INVALID_REQUIRED_SIGNER
        elif required_signer.key_path:
            if not (
                seed.is_shelley_path(required_signer.key_path)
                or seed.is_multisig_path(required_signer.key_path)
                or seed.is_minting_path(required_signer.key_path)
            ):
                raise INVALID_REQUIRED_SIGNER
        else:
            raise INVALID_REQUIRED_SIGNER

    # witness requests

    async def _process_witness_requests(self, tx_hash: bytes) -> CardanoTxResponseType:
        response: CardanoTxResponseType = messages.CardanoTxItemAck()

        for _ in range(self.msg.witness_requests_count):
            witness_request = await self.ctx.call(
                response, messages.CardanoTxWitnessRequest
            )
            self._validate_witness_request(witness_request)
            path = witness_request.path
            await self._show_witness_request(path)
            if seed.is_byron_path(path):
                response = self._get_byron_witness(path, tx_hash)
            else:
                response = self._get_shelley_witness(path, tx_hash)

        return response

    def _validate_witness_request(
        self, witness_request: messages.CardanoTxWitnessRequest
    ) -> None:
        self.account_path_checker.add_witness_request(witness_request)

    async def _show_witness_request(
        self,
        witness_path: list[int],
    ) -> None:
        await layout.confirm_witness_request(self.ctx, witness_path)

    # helpers

    def _is_network_id_verifiable(self) -> bool:
        """
        Checks whether there is at least one element that contains information about
        network ID, otherwise Trezor cannot guarantee that the tx is actually meant for
        the given network.

        Note: Shelley addresses contain network id. The intended network of Byron
        addresses can be determined based on whether they contain the protocol magic.
        These checks are performed during address validation.
        """
        return (
            self.msg.include_network_id
            or self.msg.outputs_count != 0
            or self.msg.withdrawals_count != 0
        )

    def _get_output_address(self, output: messages.CardanoTxOutput) -> bytes:
        if output.address_parameters:
            return addresses.derive_bytes(
                self.keychain,
                output.address_parameters,
                self.msg.protocol_magic,
                self.msg.network_id,
            )
        else:
            assert output.address is not None  # _validate_output
            return addresses.get_bytes_unsafe(output.address)

    def _get_output_address_type(
        self, output: messages.CardanoTxOutput
    ) -> CardanoAddressType:
        if output.address_parameters:
            return output.address_parameters.address_type
        assert output.address is not None  # _validate_output
        return addresses.get_type(addresses.get_bytes_unsafe(output.address))

    def _derive_withdrawal_address_bytes(
        self, withdrawal: messages.CardanoTxWithdrawal
    ) -> bytes:
        reward_address_type = (
            CardanoAddressType.REWARD
            if withdrawal.path or withdrawal.key_hash
            else CardanoAddressType.REWARD_SCRIPT
        )
        return addresses.derive_bytes(
            self.keychain,
            messages.CardanoAddressParametersType(
                address_type=reward_address_type,
                address_n_staking=withdrawal.path,
                staking_key_hash=withdrawal.key_hash,
                script_staking_hash=withdrawal.script_hash,
            ),
            self.msg.protocol_magic,
            self.msg.network_id,
        )

    def _get_byron_witness(
        self, path: list[int], tx_hash: bytes
    ) -> messages.CardanoTxWitnessResponse:
        node = self.keychain.derive(path)
        return messages.CardanoTxWitnessResponse(
            type=CardanoTxWitnessType.BYRON_WITNESS,
            pub_key=derive_public_key(self.keychain, path),
            signature=self._sign_tx_hash(tx_hash, path),
            chain_code=node.chain_code(),
        )

    def _get_shelley_witness(
        self, path: list[int], tx_hash: bytes
    ) -> messages.CardanoTxWitnessResponse:
        return messages.CardanoTxWitnessResponse(
            type=CardanoTxWitnessType.SHELLEY_WITNESS,
            pub_key=derive_public_key(self.keychain, path),
            signature=self._sign_tx_hash(tx_hash, path),
        )

    def _sign_tx_hash(self, tx_body_hash: bytes, path: list[int]) -> bytes:
        node = self.keychain.derive(path)
        return ed25519.sign_ext(
            node.private_key(), node.private_key_ext(), tx_body_hash
        )

    async def _fail_or_warn_if_invalid_path(
        self, schema: PathSchema, path: list[int], path_name: str
    ) -> None:
        if not schema.match(path):
            await self._fail_or_warn_path(path, path_name)

    async def _fail_or_warn_path(self, path: list[int], path_name: str) -> None:
        if safety_checks.is_strict():
            raise wire.DataError(f"Invalid {path_name.lower()}")
        else:
            await layout.warn_path(self.ctx, path, path_name)

    def _fail_if_strict_and_unusual(
        self, address_parameters: messages.CardanoAddressParametersType
    ) -> None:
        if not safety_checks.is_strict():
            return

        if Credential.payment_credential(address_parameters).is_unusual_path:
            raise wire.DataError(f"Invalid {CHANGE_OUTPUT_PATH_NAME.lower()}")

        if Credential.stake_credential(address_parameters).is_unusual_path:
            raise wire.DataError(f"Invalid {CHANGE_OUTPUT_STAKING_PATH_NAME.lower()}")
