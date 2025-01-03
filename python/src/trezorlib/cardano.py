# This file is part of the Trezor project.
#
# Copyright (C) 2012-2022 SatoshiLabs and contributors
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3
# as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the License along with this library.
# If not, see <https://www.gnu.org/licenses/lgpl-3.0.html>.

from ipaddress import ip_address
from itertools import chain
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Iterable,
    Iterator,
    List,
    Optional,
    Sequence,
    Tuple,
    Type,
    TypeVar,
    Union,
)

from . import messages as m
from . import tools

if TYPE_CHECKING:
    from .client import TrezorClient

PROTOCOL_MAGICS = {
    "mainnet": 764824073,
    "testnet_preprod": 1,
    "testnet_preview": 2,
    "testnet_legacy": 1097911063,
}
NETWORK_IDS = {"mainnet": 1, "testnet": 0}

MAX_CHUNK_SIZE = 1024

REQUIRED_FIELDS_TRANSACTION = ("inputs", "outputs")
REQUIRED_FIELDS_INPUT = ("prev_hash", "prev_index")
REQUIRED_FIELDS_CERTIFICATE = ("type",)
REQUIRED_FIELDS_POOL_PARAMETERS = (
    "pool_id",
    "vrf_key_hash",
    "pledge",
    "cost",
    "margin",
    "reward_account",
    "owners",
)
REQUIRED_FIELDS_TOKEN_GROUP = ("policy_id", "tokens")
REQUIRED_FIELDS_CVOTE_REGISTRATION = (
    "staking_path",
    "nonce",
)
REQUIRED_FIELDS_CVOTE_DELEGATION = ("vote_public_key", "weight")

INCOMPLETE_OUTPUT_ERROR_MESSAGE = "The output is missing some fields"

INVALID_OUTPUT_TOKEN_BUNDLE_ENTRY = "The output's token_bundle entry is invalid"
INVALID_MINT_TOKEN_BUNDLE_ENTRY = "The mint token_bundle entry is invalid"

InputWithPath = Tuple[m.CardanoTxInput, List[int]]
CollateralInputWithPath = Tuple[m.CardanoTxCollateralInput, List[int]]
AssetGroupWithTokens = Tuple[m.CardanoAssetGroup, List[m.CardanoToken]]
OutputWithData = Tuple[
    m.CardanoTxOutput,
    List[AssetGroupWithTokens],
    List[m.CardanoTxInlineDatumChunk],
    List[m.CardanoTxReferenceScriptChunk],
]
OutputItem = Union[
    m.CardanoTxOutput,
    m.CardanoAssetGroup,
    m.CardanoToken,
    m.CardanoTxInlineDatumChunk,
    m.CardanoTxReferenceScriptChunk,
]
CertificateItem = Union[
    m.CardanoTxCertificate,
    m.CardanoPoolOwner,
    m.CardanoPoolRelayParameters,
]
MintItem = Union[m.CardanoTxMint, m.CardanoAssetGroup, m.CardanoToken]
PoolOwnersAndRelays = Tuple[
    List[m.CardanoPoolOwner], List[m.CardanoPoolRelayParameters]
]
CertificateWithPoolOwnersAndRelays = Tuple[
    m.CardanoTxCertificate, Optional[PoolOwnersAndRelays]
]
Path = List[int]
Witness = Tuple[Path, bytes]
AuxiliaryDataSupplement = Dict[str, Union[int, bytes]]
SignTxResponse = Dict[str, Union[bytes, List[Witness], AuxiliaryDataSupplement]]
Chunk = TypeVar(
    "Chunk",
    bound=Union[m.CardanoTxInlineDatumChunk, m.CardanoTxReferenceScriptChunk],
)


def parse_optional_bytes(value: Optional[str]) -> Optional[bytes]:
    return bytes.fromhex(value) if value is not None else None


def parse_optional_int(value: Optional[str]) -> Optional[int]:
    return int(value) if value is not None else None


def create_address_parameters(
    address_type: m.CardanoAddressType,
    address_n: List[int],
    address_n_staking: Optional[List[int]] = None,
    staking_key_hash: Optional[bytes] = None,
    block_index: Optional[int] = None,
    tx_index: Optional[int] = None,
    certificate_index: Optional[int] = None,
    script_payment_hash: Optional[bytes] = None,
    script_staking_hash: Optional[bytes] = None,
) -> m.CardanoAddressParametersType:
    certificate_pointer = None

    if address_type in (
        m.CardanoAddressType.POINTER,
        m.CardanoAddressType.POINTER_SCRIPT,
    ):
        certificate_pointer = _create_certificate_pointer(
            block_index, tx_index, certificate_index
        )

    return m.CardanoAddressParametersType(
        address_type=address_type,
        address_n=address_n,
        address_n_staking=address_n_staking,
        staking_key_hash=staking_key_hash,
        certificate_pointer=certificate_pointer,
        script_payment_hash=script_payment_hash,
        script_staking_hash=script_staking_hash,
    )


def _create_certificate_pointer(
    block_index: Optional[int],
    tx_index: Optional[int],
    certificate_index: Optional[int],
) -> m.CardanoBlockchainPointerType:
    if block_index is None or tx_index is None or certificate_index is None:
        raise ValueError("Invalid pointer parameters")

    return m.CardanoBlockchainPointerType(
        block_index=block_index, tx_index=tx_index, certificate_index=certificate_index
    )


def parse_input(tx_input: dict) -> InputWithPath:
    if not all(k in tx_input for k in REQUIRED_FIELDS_INPUT):
        raise ValueError("The input is missing some fields")

    path = tools.parse_path(tx_input.get("path", ""))
    return (
        m.CardanoTxInput(
            prev_hash=bytes.fromhex(tx_input["prev_hash"]),
            prev_index=tx_input["prev_index"],
        ),
        path,
    )


def parse_output(output: dict) -> OutputWithData:
    contains_address = "address" in output
    contains_address_type = "addressType" in output

    if "amount" not in output:
        raise ValueError(INCOMPLETE_OUTPUT_ERROR_MESSAGE)
    if not (contains_address or contains_address_type):
        raise ValueError(INCOMPLETE_OUTPUT_ERROR_MESSAGE)

    address = output.get("address")

    address_parameters = None
    if contains_address_type:
        address_parameters = _parse_address_parameters(
            output, INCOMPLETE_OUTPUT_ERROR_MESSAGE
        )

    token_bundle = []
    if "token_bundle" in output:
        token_bundle = _parse_token_bundle(output["token_bundle"], is_mint=False)

    datum_hash = parse_optional_bytes(output.get("datum_hash"))

    serialization_format = m.CardanoTxOutputSerializationFormat.ARRAY_LEGACY
    if "format" in output:
        serialization_format = output["format"]

    inline_datum_size, inline_datum_chunks = _parse_chunkable_data(
        parse_optional_bytes(output.get("inline_datum")),
        m.CardanoTxInlineDatumChunk,
    )

    reference_script_size, reference_script_chunks = _parse_chunkable_data(
        parse_optional_bytes(output.get("reference_script")),
        m.CardanoTxReferenceScriptChunk,
    )

    return (
        m.CardanoTxOutput(
            address=address,
            address_parameters=address_parameters,
            amount=int(output["amount"]),
            asset_groups_count=len(token_bundle),
            datum_hash=datum_hash,
            format=serialization_format,
            inline_datum_size=inline_datum_size,
            reference_script_size=reference_script_size,
        ),
        token_bundle,
        inline_datum_chunks,
        reference_script_chunks,
    )


def _parse_token_bundle(
    token_bundle: Iterable[dict], is_mint: bool
) -> List[AssetGroupWithTokens]:
    error_message: str
    if is_mint:
        error_message = INVALID_MINT_TOKEN_BUNDLE_ENTRY
    else:
        error_message = INVALID_OUTPUT_TOKEN_BUNDLE_ENTRY

    result = []
    for token_group in token_bundle:
        if not all(k in token_group for k in REQUIRED_FIELDS_TOKEN_GROUP):
            raise ValueError(error_message)

        tokens = _parse_tokens(token_group["tokens"], is_mint)

        result.append(
            (
                m.CardanoAssetGroup(
                    policy_id=bytes.fromhex(token_group["policy_id"]),
                    tokens_count=len(tokens),
                ),
                tokens,
            )
        )

    return result


def _parse_tokens(tokens: Iterable[dict], is_mint: bool) -> List[m.CardanoToken]:
    error_message: str
    if is_mint:
        error_message = INVALID_MINT_TOKEN_BUNDLE_ENTRY
    else:
        error_message = INVALID_OUTPUT_TOKEN_BUNDLE_ENTRY

    result = []
    for token in tokens:
        if "asset_name_bytes" not in token:
            raise ValueError(error_message)

        mint_amount = None
        amount = None
        if is_mint:
            if "mint_amount" not in token:
                raise ValueError(error_message)
            mint_amount = int(token["mint_amount"])
        else:
            if "amount" not in token:
                raise ValueError(error_message)
            amount = int(token["amount"])

        result.append(
            m.CardanoToken(
                asset_name_bytes=bytes.fromhex(token["asset_name_bytes"]),
                amount=amount,
                mint_amount=mint_amount,
            )
        )

    return result


def _parse_address_parameters(
    address_parameters: dict, error_message: str
) -> m.CardanoAddressParametersType:
    if "addressType" not in address_parameters:
        raise ValueError(error_message)

    payment_path = tools.parse_path(address_parameters.get("path", ""))
    staking_path = tools.parse_path(address_parameters.get("stakingPath", ""))
    staking_key_hash_bytes = parse_optional_bytes(
        address_parameters.get("stakingKeyHash")
    )
    script_payment_hash = parse_optional_bytes(
        address_parameters.get("scriptPaymentHash")
    )
    script_staking_hash = parse_optional_bytes(
        address_parameters.get("scriptStakingHash")
    )

    return create_address_parameters(
        m.CardanoAddressType(address_parameters["addressType"]),
        payment_path,
        staking_path,
        staking_key_hash_bytes,
        address_parameters.get("blockIndex"),
        address_parameters.get("txIndex"),
        address_parameters.get("certificateIndex"),
        script_payment_hash,
        script_staking_hash,
    )


def _parse_chunkable_data(
    data: Optional[bytes], chunk_type: Type[Chunk]
) -> Tuple[int, List[Chunk]]:
    if data is None:
        return 0, []
    data_size = len(data)
    data_chunks = [chunk_type(data=chunk) for chunk in _create_data_chunks(data)]
    return data_size, data_chunks


def _create_data_chunks(data: bytes) -> Iterator[bytes]:
    processed_size = 0
    while processed_size < len(data):
        yield data[processed_size : (processed_size + MAX_CHUNK_SIZE)]
        processed_size += MAX_CHUNK_SIZE


def parse_native_script(native_script: dict) -> m.CardanoNativeScript:
    if "type" not in native_script:
        raise ValueError("Script is missing some fields")

    type = native_script["type"]
    scripts = [
        parse_native_script(sub_script)
        for sub_script in native_script.get("scripts", ())
    ]

    key_hash = parse_optional_bytes(native_script.get("key_hash"))
    key_path = tools.parse_path(native_script.get("key_path", ""))
    required_signatures_count = parse_optional_int(
        native_script.get("required_signatures_count")
    )
    invalid_before = parse_optional_int(native_script.get("invalid_before"))
    invalid_hereafter = parse_optional_int(native_script.get("invalid_hereafter"))

    return m.CardanoNativeScript(
        type=type,
        scripts=scripts,
        key_hash=key_hash,
        key_path=key_path,
        required_signatures_count=required_signatures_count,
        invalid_before=invalid_before,
        invalid_hereafter=invalid_hereafter,
    )


def parse_certificate(certificate: dict) -> CertificateWithPoolOwnersAndRelays:
    CERTIFICATE_MISSING_FIELDS_ERROR = ValueError(
        "The certificate is missing some fields"
    )

    if not all(k in certificate for k in REQUIRED_FIELDS_CERTIFICATE):
        raise CERTIFICATE_MISSING_FIELDS_ERROR

    certificate_type = certificate["type"]

    if certificate_type == m.CardanoCertificateType.STAKE_DELEGATION:
        if "pool" not in certificate:
            raise CERTIFICATE_MISSING_FIELDS_ERROR

        path, script_hash, key_hash = _parse_credential(
            certificate, CERTIFICATE_MISSING_FIELDS_ERROR
        )

        return (
            m.CardanoTxCertificate(
                type=certificate_type,
                path=path,
                pool=bytes.fromhex(certificate["pool"]),
                script_hash=script_hash,
                key_hash=key_hash,
            ),
            None,
        )
    elif certificate_type in (
        m.CardanoCertificateType.STAKE_REGISTRATION,
        m.CardanoCertificateType.STAKE_DEREGISTRATION,
    ):
        path, script_hash, key_hash = _parse_credential(
            certificate, CERTIFICATE_MISSING_FIELDS_ERROR
        )

        return (
            m.CardanoTxCertificate(
                type=certificate_type,
                path=path,
                script_hash=script_hash,
                key_hash=key_hash,
            ),
            None,
        )
    elif certificate_type in (
        m.CardanoCertificateType.STAKE_REGISTRATION_CONWAY,
        m.CardanoCertificateType.STAKE_DEREGISTRATION_CONWAY,
    ):
        if "deposit" not in certificate:
            raise CERTIFICATE_MISSING_FIELDS_ERROR

        path, script_hash, key_hash = _parse_credential(
            certificate, CERTIFICATE_MISSING_FIELDS_ERROR
        )

        return (
            m.CardanoTxCertificate(
                type=certificate_type,
                path=path,
                script_hash=script_hash,
                key_hash=key_hash,
                deposit=int(certificate["deposit"]),
            ),
            None,
        )
    elif certificate_type == m.CardanoCertificateType.STAKE_POOL_REGISTRATION:
        pool_parameters = certificate["pool_parameters"]

        if any(
            required_param not in pool_parameters
            for required_param in REQUIRED_FIELDS_POOL_PARAMETERS
        ):
            raise CERTIFICATE_MISSING_FIELDS_ERROR

        pool_metadata: Optional[m.CardanoPoolMetadataType]
        if pool_parameters.get("metadata") is not None:
            pool_metadata = m.CardanoPoolMetadataType(
                url=pool_parameters["metadata"]["url"],
                hash=bytes.fromhex(pool_parameters["metadata"]["hash"]),
            )
        else:
            pool_metadata = None

        owners = [
            _parse_pool_owner(pool_owner)
            for pool_owner in pool_parameters.get("owners", [])
        ]
        relays = [
            _parse_pool_relay(pool_relay)
            for pool_relay in pool_parameters.get("relays", [])
        ]

        return (
            m.CardanoTxCertificate(
                type=certificate_type,
                pool_parameters=m.CardanoPoolParametersType(
                    pool_id=bytes.fromhex(pool_parameters["pool_id"]),
                    vrf_key_hash=bytes.fromhex(pool_parameters["vrf_key_hash"]),
                    pledge=int(pool_parameters["pledge"]),
                    cost=int(pool_parameters["cost"]),
                    margin_numerator=int(pool_parameters["margin"]["numerator"]),
                    margin_denominator=int(pool_parameters["margin"]["denominator"]),
                    reward_account=pool_parameters["reward_account"],
                    metadata=pool_metadata,
                    owners_count=len(owners),
                    relays_count=len(relays),
                ),
            ),
            (owners, relays),
        )
    if certificate_type == m.CardanoCertificateType.VOTE_DELEGATION:
        if "drep" not in certificate:
            raise CERTIFICATE_MISSING_FIELDS_ERROR

        path, script_hash, key_hash = _parse_credential(
            certificate, CERTIFICATE_MISSING_FIELDS_ERROR
        )

        return (
            m.CardanoTxCertificate(
                type=certificate_type,
                path=path,
                script_hash=script_hash,
                key_hash=key_hash,
                drep=m.CardanoDRep(
                    type=m.CardanoDRepType(certificate["drep"]["type"]),
                    key_hash=parse_optional_bytes(certificate["drep"].get("key_hash")),
                    script_hash=parse_optional_bytes(
                        certificate["drep"].get("script_hash")
                    ),
                ),
            ),
            None,
        )
    else:
        raise ValueError("Unknown certificate type")


def _parse_credential(
    obj: dict, error: ValueError
) -> Tuple[List[int], Optional[bytes], Optional[bytes]]:
    if not any(k in obj for k in ("path", "script_hash", "key_hash")):
        raise error

    path = tools.parse_path(obj.get("path", ""))
    script_hash = parse_optional_bytes(obj.get("script_hash"))
    key_hash = parse_optional_bytes(obj.get("key_hash"))

    return path, script_hash, key_hash


def _parse_pool_owner(pool_owner: dict) -> m.CardanoPoolOwner:
    if "staking_key_path" in pool_owner:
        return m.CardanoPoolOwner(
            staking_key_path=tools.parse_path(pool_owner["staking_key_path"])
        )

    return m.CardanoPoolOwner(
        staking_key_hash=bytes.fromhex(pool_owner["staking_key_hash"])
    )


def _parse_pool_relay(pool_relay: dict) -> m.CardanoPoolRelayParameters:
    pool_relay_type = m.CardanoPoolRelayType(pool_relay["type"])

    if pool_relay_type == m.CardanoPoolRelayType.SINGLE_HOST_IP:
        ipv4_address_packed = (
            ip_address(pool_relay["ipv4_address"]).packed
            if "ipv4_address" in pool_relay
            else None
        )
        ipv6_address_packed = (
            ip_address(pool_relay["ipv6_address"]).packed
            if "ipv6_address" in pool_relay
            else None
        )

        return m.CardanoPoolRelayParameters(
            type=pool_relay_type,
            port=int(pool_relay["port"]),
            ipv4_address=ipv4_address_packed,
            ipv6_address=ipv6_address_packed,
        )
    elif pool_relay_type == m.CardanoPoolRelayType.SINGLE_HOST_NAME:
        return m.CardanoPoolRelayParameters(
            type=pool_relay_type,
            port=int(pool_relay["port"]),
            host_name=pool_relay["host_name"],
        )
    elif pool_relay_type == m.CardanoPoolRelayType.MULTIPLE_HOST_NAME:
        return m.CardanoPoolRelayParameters(
            type=pool_relay_type,
            host_name=pool_relay["host_name"],
        )

    raise ValueError("Unknown pool relay type")


def parse_withdrawal(withdrawal: dict) -> m.CardanoTxWithdrawal:
    WITHDRAWAL_MISSING_FIELDS_ERROR = ValueError(
        "The withdrawal is missing some fields"
    )

    if "amount" not in withdrawal:
        raise WITHDRAWAL_MISSING_FIELDS_ERROR

    path, script_hash, key_hash = _parse_credential(
        withdrawal, WITHDRAWAL_MISSING_FIELDS_ERROR
    )

    return m.CardanoTxWithdrawal(
        path=path,
        amount=int(withdrawal["amount"]),
        script_hash=script_hash,
        key_hash=key_hash,
    )


def parse_auxiliary_data(
    auxiliary_data: Optional[dict],
) -> Optional[m.CardanoTxAuxiliaryData]:
    if auxiliary_data is None:
        return None

    AUXILIARY_DATA_MISSING_FIELDS_ERROR = ValueError(
        "Auxiliary data is missing some fields"
    )

    # include all provided fields so we can test validation in FW
    hash = parse_optional_bytes(auxiliary_data.get("hash"))

    cvote_registration_parameters = None
    if "cvote_registration_parameters" in auxiliary_data:
        cvote_registration = auxiliary_data["cvote_registration_parameters"]
        if not all(k in cvote_registration for k in REQUIRED_FIELDS_CVOTE_REGISTRATION):
            raise AUXILIARY_DATA_MISSING_FIELDS_ERROR

        serialization_format = cvote_registration.get("format")

        delegations = []
        for delegation in cvote_registration.get("delegations", []):
            if not all(k in delegation for k in REQUIRED_FIELDS_CVOTE_DELEGATION):
                raise AUXILIARY_DATA_MISSING_FIELDS_ERROR
            delegations.append(
                m.CardanoCVoteRegistrationDelegation(
                    vote_public_key=bytes.fromhex(delegation["vote_public_key"]),
                    weight=int(delegation["weight"]),
                )
            )

        voting_purpose = None
        if serialization_format == m.CardanoCVoteRegistrationFormat.CIP36:
            voting_purpose = cvote_registration.get("voting_purpose")

        cvote_registration_parameters = m.CardanoCVoteRegistrationParametersType(
            vote_public_key=parse_optional_bytes(
                cvote_registration.get("vote_public_key")
            ),
            staking_path=tools.parse_path(cvote_registration["staking_path"]),
            nonce=cvote_registration["nonce"],
            payment_address=cvote_registration.get("payment_address"),
            payment_address_parameters=(
                _parse_address_parameters(
                    cvote_registration["payment_address_parameters"],
                    str(AUXILIARY_DATA_MISSING_FIELDS_ERROR),
                )
                if "payment_address_parameters" in cvote_registration
                else None
            ),
            format=serialization_format,
            delegations=delegations,
            voting_purpose=voting_purpose,
        )

    if hash is None and cvote_registration_parameters is None:
        raise AUXILIARY_DATA_MISSING_FIELDS_ERROR

    return m.CardanoTxAuxiliaryData(
        hash=hash,
        cvote_registration_parameters=cvote_registration_parameters,
    )


def parse_mint(mint: Iterable[dict]) -> List[AssetGroupWithTokens]:
    return _parse_token_bundle(mint, is_mint=True)


def parse_script_data_hash(script_data_hash: Optional[str]) -> Optional[bytes]:
    return parse_optional_bytes(script_data_hash)


def parse_collateral_input(collateral_input: dict) -> CollateralInputWithPath:
    if not all(k in collateral_input for k in REQUIRED_FIELDS_INPUT):
        raise ValueError("The collateral input is missing some fields")

    path = tools.parse_path(collateral_input.get("path", ""))
    return (
        m.CardanoTxCollateralInput(
            prev_hash=bytes.fromhex(collateral_input["prev_hash"]),
            prev_index=collateral_input["prev_index"],
        ),
        path,
    )


def parse_required_signer(required_signer: dict) -> m.CardanoTxRequiredSigner:
    key_hash = parse_optional_bytes(required_signer.get("key_hash"))
    key_path = tools.parse_path(required_signer.get("key_path", ""))
    return m.CardanoTxRequiredSigner(
        key_hash=key_hash,
        key_path=key_path,
    )


def parse_reference_input(reference_input: dict) -> m.CardanoTxReferenceInput:
    if not all(k in reference_input for k in REQUIRED_FIELDS_INPUT):
        raise ValueError("The reference input is missing some fields")

    return m.CardanoTxReferenceInput(
        prev_hash=bytes.fromhex(reference_input["prev_hash"]),
        prev_index=reference_input["prev_index"],
    )


def parse_additional_witness_request(
    additional_witness_request: dict,
) -> Path:
    if "path" not in additional_witness_request:
        raise ValueError("Invalid additional witness request")

    return tools.parse_path(additional_witness_request["path"])


def _get_witness_requests(
    inputs: Sequence[InputWithPath],
    certificates: Sequence[CertificateWithPoolOwnersAndRelays],
    withdrawals: Sequence[m.CardanoTxWithdrawal],
    collateral_inputs: Sequence[CollateralInputWithPath],
    required_signers: Sequence[m.CardanoTxRequiredSigner],
    additional_witness_requests: Sequence[Path],
    signing_mode: m.CardanoTxSigningMode,
) -> List[m.CardanoTxWitnessRequest]:
    paths = set()

    # don't gather paths from tx elements in MULTISIG_TRANSACTION signing mode
    if signing_mode != m.CardanoTxSigningMode.MULTISIG_TRANSACTION:
        for _, path in inputs:
            if path:
                paths.add(tuple(path))
        for certificate, pool_owners_and_relays in certificates:
            if (
                certificate.type
                in (
                    m.CardanoCertificateType.STAKE_DEREGISTRATION,
                    m.CardanoCertificateType.STAKE_DELEGATION,
                    m.CardanoCertificateType.STAKE_REGISTRATION_CONWAY,
                    m.CardanoCertificateType.STAKE_DEREGISTRATION_CONWAY,
                    m.CardanoCertificateType.VOTE_DELEGATION,
                )
                and certificate.path
            ):
                paths.add(tuple(certificate.path))
            elif (
                certificate.type == m.CardanoCertificateType.STAKE_POOL_REGISTRATION
                and pool_owners_and_relays is not None
            ):
                owners, _ = pool_owners_and_relays
                for pool_owner in owners:
                    if pool_owner.staking_key_path:
                        paths.add(tuple(pool_owner.staking_key_path))
        for withdrawal in withdrawals:
            if withdrawal.path:
                paths.add(tuple(withdrawal.path))

    # gather Plutus-related paths
    if signing_mode == m.CardanoTxSigningMode.PLUTUS_TRANSACTION:
        for _, path in collateral_inputs:
            if path:
                paths.add(tuple(path))

    # add required_signers and additional_witness_requests in all cases
    for required_signer in required_signers:
        if required_signer.key_path:
            paths.add(tuple(required_signer.key_path))
    for additional_witness_request in additional_witness_requests:
        paths.add(tuple(additional_witness_request))

    sorted_paths = sorted([list(path) for path in paths])
    return [m.CardanoTxWitnessRequest(path=path) for path in sorted_paths]


def _get_inputs_items(inputs: List[InputWithPath]) -> Iterator[m.CardanoTxInput]:
    for input, _ in inputs:
        yield input


def _get_outputs_items(outputs: List[OutputWithData]) -> Iterator[OutputItem]:
    for output_with_data in outputs:
        yield from _get_output_items(output_with_data)


def _get_output_items(output_with_data: OutputWithData) -> Iterator[OutputItem]:
    (
        output,
        asset_groups,
        inline_datum_chunks,
        reference_script_chunks,
    ) = output_with_data
    yield output
    for asset_group, tokens in asset_groups:
        yield asset_group
        yield from tokens
    yield from inline_datum_chunks
    yield from reference_script_chunks


def _get_certificates_items(
    certificates: Sequence[CertificateWithPoolOwnersAndRelays],
) -> Iterator[CertificateItem]:
    for certificate, pool_owners_and_relays in certificates:
        yield certificate
        if pool_owners_and_relays is not None:
            owners, relays = pool_owners_and_relays
            yield from owners
            yield from relays


def _get_mint_items(mint: Sequence[AssetGroupWithTokens]) -> Iterator[MintItem]:
    if not mint:
        return
    yield m.CardanoTxMint(asset_groups_count=len(mint))
    for asset_group, tokens in mint:
        yield asset_group
        yield from tokens


def _get_collateral_inputs_items(
    collateral_inputs: Sequence[CollateralInputWithPath],
) -> Iterator[m.CardanoTxCollateralInput]:
    for collateral_input, _ in collateral_inputs:
        yield collateral_input


# ====== Client functions ====== #


def get_address(
    client: "TrezorClient",
    address_parameters: m.CardanoAddressParametersType,
    protocol_magic: int = PROTOCOL_MAGICS["mainnet"],
    network_id: int = NETWORK_IDS["mainnet"],
    show_display: bool = False,
    derivation_type: m.CardanoDerivationType = m.CardanoDerivationType.ICARUS,
    chunkify: bool = False,
) -> str:
    return client.call(
        m.CardanoGetAddress(
            address_parameters=address_parameters,
            protocol_magic=protocol_magic,
            network_id=network_id,
            show_display=show_display,
            derivation_type=derivation_type,
            chunkify=chunkify,
        ),
        expect=m.CardanoAddress,
    ).address


def get_public_key(
    client: "TrezorClient",
    address_n: List[int],
    derivation_type: m.CardanoDerivationType = m.CardanoDerivationType.ICARUS,
    show_display: bool = False,
) -> m.CardanoPublicKey:
    return client.call(
        m.CardanoGetPublicKey(
            address_n=address_n,
            derivation_type=derivation_type,
            show_display=show_display,
        ),
        expect=m.CardanoPublicKey,
    )


def get_native_script_hash(
    client: "TrezorClient",
    native_script: m.CardanoNativeScript,
    display_format: m.CardanoNativeScriptHashDisplayFormat = m.CardanoNativeScriptHashDisplayFormat.HIDE,
    derivation_type: m.CardanoDerivationType = m.CardanoDerivationType.ICARUS,
) -> m.CardanoNativeScriptHash:
    return client.call(
        m.CardanoGetNativeScriptHash(
            script=native_script,
            display_format=display_format,
            derivation_type=derivation_type,
        ),
        expect=m.CardanoNativeScriptHash,
    )


def sign_tx(
    client: "TrezorClient",
    signing_mode: m.CardanoTxSigningMode,
    inputs: List[InputWithPath],
    outputs: List[OutputWithData],
    fee: int,
    ttl: Optional[int],
    validity_interval_start: Optional[int],
    certificates: Sequence[CertificateWithPoolOwnersAndRelays] = (),
    withdrawals: Sequence[m.CardanoTxWithdrawal] = (),
    protocol_magic: int = PROTOCOL_MAGICS["mainnet"],
    network_id: int = NETWORK_IDS["mainnet"],
    auxiliary_data: Optional[m.CardanoTxAuxiliaryData] = None,
    mint: Sequence[AssetGroupWithTokens] = (),
    script_data_hash: Optional[bytes] = None,
    collateral_inputs: Sequence[CollateralInputWithPath] = (),
    required_signers: Sequence[m.CardanoTxRequiredSigner] = (),
    collateral_return: Optional[OutputWithData] = None,
    total_collateral: Optional[int] = None,
    reference_inputs: Sequence[m.CardanoTxReferenceInput] = (),
    additional_witness_requests: Sequence[Path] = (),
    derivation_type: m.CardanoDerivationType = m.CardanoDerivationType.ICARUS,
    include_network_id: bool = False,
    chunkify: bool = False,
    tag_cbor_sets: bool = False,
) -> Dict[str, Any]:
    witness_requests = _get_witness_requests(
        inputs,
        certificates,
        withdrawals,
        collateral_inputs,
        required_signers,
        additional_witness_requests,
        signing_mode,
    )

    response = client.call(
        m.CardanoSignTxInit(
            signing_mode=signing_mode,
            inputs_count=len(inputs),
            outputs_count=len(outputs),
            fee=fee,
            ttl=ttl,
            validity_interval_start=validity_interval_start,
            certificates_count=len(certificates),
            withdrawals_count=len(withdrawals),
            protocol_magic=protocol_magic,
            network_id=network_id,
            has_auxiliary_data=auxiliary_data is not None,
            minting_asset_groups_count=len(mint),
            script_data_hash=script_data_hash,
            collateral_inputs_count=len(collateral_inputs),
            required_signers_count=len(required_signers),
            has_collateral_return=collateral_return is not None,
            total_collateral=total_collateral,
            reference_inputs_count=len(reference_inputs),
            witness_requests_count=len(witness_requests),
            derivation_type=derivation_type,
            include_network_id=include_network_id,
            chunkify=chunkify,
            tag_cbor_sets=tag_cbor_sets,
        ),
        expect=m.CardanoTxItemAck,
    )

    for tx_item in chain(
        _get_inputs_items(inputs),
        _get_outputs_items(outputs),
        _get_certificates_items(certificates),
        withdrawals,
    ):
        response = client.call(tx_item, expect=m.CardanoTxItemAck)

    sign_tx_response: Dict[str, Any] = {}

    if auxiliary_data is not None:
        auxiliary_data_supplement = client.call(
            auxiliary_data, expect=m.CardanoTxAuxiliaryDataSupplement
        )
        if (
            auxiliary_data_supplement.type
            != m.CardanoTxAuxiliaryDataSupplementType.NONE
        ):
            sign_tx_response["auxiliary_data_supplement"] = (
                auxiliary_data_supplement.__dict__
            )

        response = client.call(m.CardanoTxHostAck(), expect=m.CardanoTxItemAck)

    for tx_item in chain(
        _get_mint_items(mint),
        _get_collateral_inputs_items(collateral_inputs),
        required_signers,
    ):
        response = client.call(tx_item, expect=m.CardanoTxItemAck)

    if collateral_return is not None:
        for tx_item in _get_output_items(collateral_return):
            response = client.call(tx_item, expect=m.CardanoTxItemAck)

    for reference_input in reference_inputs:
        response = client.call(reference_input, expect=m.CardanoTxItemAck)

    sign_tx_response["witnesses"] = []
    for witness_request in witness_requests:
        response = client.call(witness_request, expect=m.CardanoTxWitnessResponse)
        sign_tx_response["witnesses"].append(
            {
                "type": response.type,
                "pub_key": response.pub_key,
                "signature": response.signature,
                "chain_code": response.chain_code,
            }
        )

    response = client.call(m.CardanoTxHostAck(), expect=m.CardanoTxBodyHash)
    sign_tx_response["tx_hash"] = response.tx_hash

    response = client.call(m.CardanoTxHostAck(), expect=m.CardanoSignTxFinished)

    return sign_tx_response
