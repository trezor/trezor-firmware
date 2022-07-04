from micropython import const
from typing import TYPE_CHECKING

from trezor import messages, wire
from trezor.crypto import hashlib
from trezor.crypto.curve import ed25519
from trezor.enums import (
    CardanoAddressType,
    CardanoCertificateType,
    CardanoTxOutputSerializationFormat,
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
from ..helpers.hash_builder_collection import (
    HashBuilderDict,
    HashBuilderEmbeddedCBOR,
    HashBuilderList,
)
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
    from typing import Any, Awaitable, ClassVar
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
TX_BODY_KEY_COLLATERAL_RETURN = const(16)
TX_BODY_KEY_TOTAL_COLLATERAL = const(17)
TX_BODY_KEY_REFERENCE_INPUTS = const(18)

BABBAGE_OUTPUT_KEY_ADDRESS = const(0)
BABBAGE_OUTPUT_KEY_AMOUNT = const(1)
BABBAGE_OUTPUT_KEY_DATUM_OPTION = const(2)
BABBAGE_OUTPUT_KEY_REFERENCE_SCRIPT = const(3)

DATUM_OPTION_KEY_HASH = const(0)
DATUM_OPTION_KEY_INLINE = const(1)

POOL_REGISTRATION_CERTIFICATE_ITEMS_COUNT = 10

MAX_CHUNK_SIZE = 1024


class Signer:
    """
    This class encapsulates the entire tx signing process. By default, most tx items are
    allowed and shown to the user. For each signing mode, there is a subclass that
    overrides some methods, usually to add more validation rules and show/hide some
    items. Each tx item is processed in a _process_xyz() method which handles validation,
    user confirmation and serialization of the tx item.
    """

    SIGNING_MODE_TITLE: ClassVar[str]

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
                msg.has_collateral_return,
                msg.total_collateral is not None,
                msg.reference_inputs_count > 0,
            )
        )
        self.tx_dict: HashBuilderDict[int, Any] = HashBuilderDict(
            tx_dict_items_count, wire.ProcessError("Invalid tx signing request")
        )

        self.should_show_details = False

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

        if self.msg.has_collateral_return:
            await self._process_collateral_return()

        if self.msg.total_collateral is not None:
            self.tx_dict.add(TX_BODY_KEY_TOTAL_COLLATERAL, self.msg.total_collateral)

        if self.msg.reference_inputs_count > 0:
            reference_inputs_list: HashBuilderList[tuple[bytes, int]] = HashBuilderList(
                self.msg.reference_inputs_count
            )
            with self.tx_dict.add(TX_BODY_KEY_REFERENCE_INPUTS, reference_inputs_list):
                await self._process_reference_inputs(reference_inputs_list)

    def _validate_tx_init(self) -> None:
        if self.msg.fee > LOVELACE_MAX_SUPPLY:
            raise wire.ProcessError("Fee is out of range!")
        if (
            self.msg.total_collateral is not None
            and self.msg.total_collateral > LOVELACE_MAX_SUPPLY
        ):
            raise wire.ProcessError("Total collateral is out of range!")
        validate_network_info(self.msg.network_id, self.msg.protocol_magic)

    async def _show_tx_init(self) -> None:
        self.should_show_details = await layout.show_tx_init(
            self.ctx, self.SIGNING_MODE_TITLE
        )

        if not self._is_network_id_verifiable():
            await layout.warn_tx_network_unverifiable(self.ctx)

    async def _confirm_tx(self, tx_hash: bytes) -> None:
        # Final signing confirmation is handled separately in each signing mode.
        raise NotImplementedError

    def _should_show_tx_hash(self) -> bool:
        # By default we display tx hash only if showing details
        return self.should_show_details

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
            await self._process_output(outputs_list, output)

            total_amount += output.amount

        if total_amount > LOVELACE_MAX_SUPPLY:
            raise wire.ProcessError("Total transaction amount is out of range!")

    async def _process_output(
        self, outputs_list: HashBuilderList, output: messages.CardanoTxOutput
    ) -> None:
        self._validate_output(output)
        should_show = self._should_show_output(output)
        if should_show:
            await self._show_output_init(output)

        output_items_count = 2 + sum(
            (
                output.datum_hash is not None,
                output.inline_datum_size > 0,
                output.reference_script_size > 0,
            )
        )
        if output.format == CardanoTxOutputSerializationFormat.ARRAY_LEGACY:
            output_list: HashBuilderList = HashBuilderList(output_items_count)
            with outputs_list.append(output_list):
                await self._process_legacy_output(output_list, output, should_show)
        elif output.format == CardanoTxOutputSerializationFormat.MAP_BABBAGE:
            output_dict: HashBuilderDict[int, Any] = HashBuilderDict(
                output_items_count, wire.ProcessError("Invalid output")
            )
            with outputs_list.append(output_dict):
                await self._process_babbage_output(output_dict, output, should_show)
        else:
            raise RuntimeError  # should be unreachable

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

        # datum hash
        if output.datum_hash is not None:
            if len(output.datum_hash) != OUTPUT_DATUM_HASH_SIZE:
                raise wire.ProcessError("Invalid output datum hash")

        # inline datum
        if output.inline_datum_size > 0:
            if output.format != CardanoTxOutputSerializationFormat.MAP_BABBAGE:
                raise wire.ProcessError("Invalid output")

        # datum hash and inline datum are mutually exclusive
        if output.datum_hash is not None and output.inline_datum_size > 0:
            raise wire.ProcessError("Invalid output")

        # reference script
        if output.reference_script_size > 0:
            if output.format != CardanoTxOutputSerializationFormat.MAP_BABBAGE:
                raise wire.ProcessError("Invalid output")

        self.account_path_checker.add_output(output)

    async def _show_output_init(self, output: messages.CardanoTxOutput) -> None:
        address_type = self._get_output_address_type(output)
        if (
            output.datum_hash is None
            and output.inline_datum_size == 0
            and address_type in addresses.ADDRESS_TYPES_PAYMENT_SCRIPT
        ):
            await layout.warn_tx_output_no_datum(self.ctx)

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
            "change" if self._is_change_output(output) else "address",
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
        Determines whether the output should be shown. Extracted from _show_output
        because of readability.
        """

        address_type = self._get_output_address_type(output)
        if (
            output.datum_hash is None
            and output.inline_datum_size == 0
            and address_type in addresses.ADDRESS_TYPES_PAYMENT_SCRIPT
        ):
            # Plutus script address without a datum is unspendable, we must show a warning.
            return True

        if self._is_simple_change_output(output):
            # Show change output only if showing details and if it contains plutus data
            has_plutus_data = (
                output.datum_hash is not None
                or output.inline_datum_size > 0
                or output.reference_script_size > 0
            )
            return self.should_show_details and has_plutus_data

        return True

    def _is_change_output(self, output: messages.CardanoTxOutput) -> bool:
        """Used only to determine what message to show to the user when confirming sending."""
        return output.address_parameters is not None

    def _is_simple_change_output(self, output: messages.CardanoTxOutput) -> bool:
        """Used to determine whether an output is a change output with ordinary credentials."""
        return output.address_parameters is not None and not should_show_credentials(
            output.address_parameters
        )

    async def _process_legacy_output(
        self,
        output_list: HashBuilderList,
        output: messages.CardanoTxOutput,
        should_show: bool,
    ) -> None:
        address = self._get_output_address(output)
        output_list.append(address)

        if output.asset_groups_count == 0:
            # Output structure is: [address, amount, datum_hash?]
            output_list.append(output.amount)
        else:
            # Output structure is: [address, [amount, asset_groups], datum_hash?]
            output_value_list: HashBuilderList = HashBuilderList(2)
            with output_list.append(output_value_list):
                await self._process_output_value(output_value_list, output, should_show)

        if output.datum_hash is not None:
            if should_show:
                await self._show_if_showing_details(
                    layout.confirm_datum_hash(self.ctx, output.datum_hash)
                )
            output_list.append(output.datum_hash)

    async def _process_babbage_output(
        self,
        output_dict: HashBuilderDict[int, Any],
        output: messages.CardanoTxOutput,
        should_show: bool,
    ) -> None:
        """
        This output format corresponds to the post-Alonzo format in CDDL.
        Note that it is to be used also for outputs with no Plutus elements.
        """
        address = self._get_output_address(output)
        output_dict.add(BABBAGE_OUTPUT_KEY_ADDRESS, address)

        if output.asset_groups_count == 0:
            # Only amount is added to the dict.
            output_dict.add(BABBAGE_OUTPUT_KEY_AMOUNT, output.amount)
        else:
            # [amount, asset_groups] is added to the dict.
            output_value_list: HashBuilderList = HashBuilderList(2)
            with output_dict.add(BABBAGE_OUTPUT_KEY_AMOUNT, output_value_list):
                await self._process_output_value(output_value_list, output, should_show)

        if output.datum_hash is not None:
            if should_show:
                await self._show_if_showing_details(
                    layout.confirm_datum_hash(self.ctx, output.datum_hash)
                )
            output_dict.add(
                BABBAGE_OUTPUT_KEY_DATUM_OPTION,
                (DATUM_OPTION_KEY_HASH, output.datum_hash),
            )
        elif output.inline_datum_size > 0:
            inline_datum_list: HashBuilderList = HashBuilderList(2)
            with output_dict.add(BABBAGE_OUTPUT_KEY_DATUM_OPTION, inline_datum_list):
                inline_datum_list.append(DATUM_OPTION_KEY_INLINE)
                inline_datum_cbor: HashBuilderEmbeddedCBOR = HashBuilderEmbeddedCBOR(
                    output.inline_datum_size
                )
                with inline_datum_list.append(inline_datum_cbor):
                    await self._process_inline_datum(
                        inline_datum_cbor, output.inline_datum_size, should_show
                    )

        if output.reference_script_size > 0:
            reference_script_cbor: HashBuilderEmbeddedCBOR = HashBuilderEmbeddedCBOR(
                output.reference_script_size
            )
            with output_dict.add(
                BABBAGE_OUTPUT_KEY_REFERENCE_SCRIPT, reference_script_cbor
            ):
                await self._process_reference_script(
                    reference_script_cbor, output.reference_script_size, should_show
                )

    async def _process_output_value(
        self,
        output_value_list: HashBuilderList,
        output: messages.CardanoTxOutput,
        should_show_tokens: bool,
    ) -> None:
        """Should be used only when the output contains tokens."""
        assert output.asset_groups_count > 0

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
                should_show_tokens,
            )

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

    # inline datum

    async def _process_inline_datum(
        self,
        inline_datum_cbor: HashBuilderEmbeddedCBOR,
        inline_datum_size: int,
        should_show: bool,
    ) -> None:
        assert inline_datum_size > 0

        chunks_count = self._get_chunks_count(inline_datum_size)
        for chunk_number in range(chunks_count):
            chunk: messages.CardanoTxInlineDatumChunk = await self.ctx.call(
                messages.CardanoTxItemAck(), messages.CardanoTxInlineDatumChunk
            )
            self._validate_chunk(
                chunk.data,
                chunk_number,
                chunks_count,
                wire.ProcessError("Invalid inline datum chunk"),
            )
            if chunk_number == 0 and should_show:
                await self._show_if_showing_details(
                    layout.confirm_inline_datum(self.ctx, chunk.data, inline_datum_size)
                )
            inline_datum_cbor.add(chunk.data)

    # reference script

    async def _process_reference_script(
        self,
        reference_script_cbor: HashBuilderEmbeddedCBOR,
        reference_script_size: int,
        should_show: bool,
    ) -> None:
        assert reference_script_size > 0

        chunks_count = self._get_chunks_count(reference_script_size)
        for chunk_number in range(chunks_count):
            chunk: messages.CardanoTxReferenceScriptChunk = await self.ctx.call(
                messages.CardanoTxItemAck(), messages.CardanoTxReferenceScriptChunk
            )
            self._validate_chunk(
                chunk.data,
                chunk_number,
                chunks_count,
                wire.ProcessError("Invalid reference script chunk"),
            )
            if chunk_number == 0 and should_show:
                await self._show_if_showing_details(
                    layout.confirm_reference_script(
                        self.ctx, chunk.data, reference_script_size
                    )
                )
            reference_script_cbor.add(chunk.data)

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
            await self._show_if_showing_details(
                layout.confirm_withdrawal(
                    self.ctx, withdrawal, address_bytes, self.msg.network_id
                )
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
            self.should_show_details,
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
        await self._show_if_showing_details(
            layout.confirm_script_data_hash(self.ctx, self.msg.script_data_hash)
        )
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
            await self._show_collateral_input(collateral_input)
            collateral_inputs_list.append(
                (collateral_input.prev_hash, collateral_input.prev_index)
            )

    def _validate_collateral_input(
        self, collateral_input: messages.CardanoTxCollateralInput
    ) -> None:
        if len(collateral_input.prev_hash) != INPUT_PREV_HASH_SIZE:
            raise wire.ProcessError("Invalid collateral input")

    async def _show_collateral_input(
        self, collateral_input: messages.CardanoTxCollateralInput
    ) -> None:
        if self.msg.total_collateral is None:
            await self._show_if_showing_details(
                layout.confirm_collateral_input(self.ctx, collateral_input)
            )

    # required signers

    async def _process_required_signers(
        self, required_signers_list: HashBuilderList[bytes]
    ) -> None:
        for _ in range(self.msg.required_signers_count):
            required_signer: messages.CardanoTxRequiredSigner = await self.ctx.call(
                messages.CardanoTxItemAck(), messages.CardanoTxRequiredSigner
            )
            self._validate_required_signer(required_signer)
            await self._show_if_showing_details(
                layout.confirm_required_signer(self.ctx, required_signer)
            )

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

    # collateral return

    async def _process_collateral_return(self) -> None:
        output: messages.CardanoTxOutput = await self.ctx.call(
            messages.CardanoTxItemAck(), messages.CardanoTxOutput
        )
        self._validate_collateral_return(output)
        should_show_init = self._should_show_collateral_return_init(output)
        should_show_tokens = self._should_show_collateral_return_tokens(output)
        if should_show_init:
            await self._show_collateral_return_init(output)

        # Datums and reference scripts are forbidden, see _validate_collateral_return.
        output_items_count = 2
        if output.format == CardanoTxOutputSerializationFormat.ARRAY_LEGACY:
            output_list: HashBuilderList = HashBuilderList(output_items_count)
            with self.tx_dict.add(TX_BODY_KEY_COLLATERAL_RETURN, output_list):
                await self._process_legacy_output(
                    output_list, output, should_show_tokens
                )
        elif output.format == CardanoTxOutputSerializationFormat.MAP_BABBAGE:
            output_dict: HashBuilderDict[int, Any] = HashBuilderDict(
                output_items_count, wire.ProcessError("Invalid collateral return")
            )
            with self.tx_dict.add(TX_BODY_KEY_COLLATERAL_RETURN, output_dict):
                await self._process_babbage_output(
                    output_dict, output, should_show_tokens
                )
        else:
            raise RuntimeError  # should be unreachable

    def _validate_collateral_return(self, output: messages.CardanoTxOutput) -> None:
        self._validate_output(output)

        address_type = self._get_output_address_type(output)
        if address_type not in addresses.ADDRESS_TYPES_PAYMENT_KEY:
            raise wire.ProcessError("Invalid collateral return")

        if (
            output.datum_hash is not None
            or output.inline_datum_size > 0
            or output.reference_script_size > 0
        ):
            raise wire.ProcessError("Invalid collateral return")

    async def _show_collateral_return_init(
        self, output: messages.CardanoTxOutput
    ) -> None:
        # We don't display missing datum warning since datums are forbidden.

        if output.asset_groups_count > 0:
            await layout.warn_tx_output_contains_tokens(
                self.ctx, is_collateral_return=True
            )

        if output.address_parameters is not None:
            address = addresses.derive_human_readable(
                self.keychain,
                output.address_parameters,
                self.msg.protocol_magic,
                self.msg.network_id,
            )
            await self._show_output_credentials(
                output.address_parameters,
            )
        else:
            assert output.address is not None  # _validate_output
            address = output.address

        await layout.confirm_sending(
            self.ctx,
            output.amount,
            address,
            "collateral-return",
            self.msg.network_id,
        )

    def _should_show_collateral_return_init(
        self, output: messages.CardanoTxOutput
    ) -> bool:
        if self.msg.total_collateral is None:
            return True

        if self._is_simple_change_output(output):
            return False

        return True

    def _should_show_collateral_return_tokens(
        self, output: messages.CardanoTxOutput
    ) -> bool:
        if self._is_simple_change_output(output):
            return False

        return self.should_show_details

    # reference inputs

    async def _process_reference_inputs(
        self, reference_inputs_list: HashBuilderList[tuple[bytes, int]]
    ) -> None:
        for _ in range(self.msg.reference_inputs_count):
            reference_input: messages.CardanoTxReferenceInput = await self.ctx.call(
                messages.CardanoTxItemAck(), messages.CardanoTxReferenceInput
            )
            self._validate_reference_input(reference_input)
            await self._show_if_showing_details(
                layout.confirm_reference_input(self.ctx, reference_input)
            )
            reference_inputs_list.append(
                (reference_input.prev_hash, reference_input.prev_index)
            )

    def _validate_reference_input(
        self, reference_input: messages.CardanoTxReferenceInput
    ) -> None:
        if len(reference_input.prev_hash) != INPUT_PREV_HASH_SIZE:
            raise wire.ProcessError("Invalid reference input")

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

    def _assert_tx_init_cond(self, condition: bool) -> None:
        if not condition:
            raise wire.ProcessError("Invalid tx signing request")

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

    def _get_chunks_count(self, data_size: int) -> int:
        assert data_size > 0
        return (data_size - 1) // MAX_CHUNK_SIZE + 1

    def _validate_chunk(
        self,
        chunk_data: bytes,
        chunk_number: int,
        chunks_count: int,
        error: wire.ProcessError,
    ) -> None:
        if chunk_number < chunks_count - 1 and len(chunk_data) != MAX_CHUNK_SIZE:
            raise error
        if chunk_number == chunks_count - 1 and len(chunk_data) > MAX_CHUNK_SIZE:
            raise error

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

    async def _show_if_showing_details(self, layout_fn: Awaitable) -> None:
        if self.should_show_details:
            await layout_fn
