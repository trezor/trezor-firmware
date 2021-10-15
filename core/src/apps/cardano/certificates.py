from trezor.enums import (
    CardanoCertificateType,
    CardanoPoolRelayType,
    CardanoTxSigningMode,
)

from apps.common import cbor

from .address import (
    get_address_bytes_unsafe,
    get_public_key_hash,
    validate_reward_address,
)
from .helpers import ADDRESS_KEY_HASH_SIZE, INVALID_CERTIFICATE, LOVELACE_MAX_SUPPLY
from .helpers.paths import SCHEMA_STAKING_ANY_ACCOUNT
from .helpers.utils import validate_stake_credential

if False:
    from typing import Any

    from trezor.messages import (
        CardanoPoolMetadataType,
        CardanoPoolOwner,
        CardanoPoolParametersType,
        CardanoPoolRelayParameters,
        CardanoTxCertificate,
    )

    from apps.common.cbor import CborSequence

    from . import seed
    from .helpers.account_path_check import AccountPathChecker

POOL_HASH_SIZE = 28
VRF_KEY_HASH_SIZE = 32
POOL_METADATA_HASH_SIZE = 32
IPV4_ADDRESS_SIZE = 4
IPV6_ADDRESS_SIZE = 16

MAX_URL_LENGTH = 64
MAX_PORT_NUMBER = 65535


def validate_certificate(
    certificate: CardanoTxCertificate,
    signing_mode: CardanoTxSigningMode,
    protocol_magic: int,
    network_id: int,
    account_path_checker: AccountPathChecker,
) -> None:
    if (
        signing_mode != CardanoTxSigningMode.POOL_REGISTRATION_AS_OWNER
        and certificate.type == CardanoCertificateType.STAKE_POOL_REGISTRATION
    ):
        raise INVALID_CERTIFICATE
    elif (
        signing_mode == CardanoTxSigningMode.POOL_REGISTRATION_AS_OWNER
        and certificate.type != CardanoCertificateType.STAKE_POOL_REGISTRATION
    ):
        raise INVALID_CERTIFICATE

    _validate_certificate_structure(certificate)

    if certificate.type in (
        CardanoCertificateType.STAKE_DELEGATION,
        CardanoCertificateType.STAKE_REGISTRATION,
        CardanoCertificateType.STAKE_DEREGISTRATION,
    ):
        validate_stake_credential(
            certificate.path, certificate.script_hash, signing_mode, INVALID_CERTIFICATE
        )

    if certificate.type == CardanoCertificateType.STAKE_DELEGATION:
        if not certificate.pool or len(certificate.pool) != POOL_HASH_SIZE:
            raise INVALID_CERTIFICATE

    if certificate.type == CardanoCertificateType.STAKE_POOL_REGISTRATION:
        if certificate.pool_parameters is None:
            raise INVALID_CERTIFICATE
        _validate_pool_parameters(
            certificate.pool_parameters, protocol_magic, network_id
        )

    account_path_checker.add_certificate(certificate)


def _validate_certificate_structure(certificate: CardanoTxCertificate) -> None:
    path = certificate.path
    script_hash = certificate.script_hash
    pool = certificate.pool
    pool_parameters = certificate.pool_parameters

    fields_to_be_empty: dict[CardanoCertificateType, tuple[Any, ...]] = {
        CardanoCertificateType.STAKE_REGISTRATION: (pool, pool_parameters),
        CardanoCertificateType.STAKE_DELEGATION: (pool_parameters,),
        CardanoCertificateType.STAKE_DEREGISTRATION: (pool, pool_parameters),
        CardanoCertificateType.STAKE_POOL_REGISTRATION: (path, script_hash, pool),
    }

    if certificate.type not in fields_to_be_empty or any(
        fields_to_be_empty[certificate.type]
    ):
        raise INVALID_CERTIFICATE


def cborize_certificate(
    keychain: seed.Keychain, certificate: CardanoTxCertificate
) -> CborSequence:
    if certificate.type in (
        CardanoCertificateType.STAKE_REGISTRATION,
        CardanoCertificateType.STAKE_DEREGISTRATION,
    ):
        return (
            certificate.type,
            cborize_certificate_stake_credential(
                keychain, certificate.path, certificate.script_hash
            ),
        )
    elif certificate.type == CardanoCertificateType.STAKE_DELEGATION:
        return (
            certificate.type,
            cborize_certificate_stake_credential(
                keychain, certificate.path, certificate.script_hash
            ),
            certificate.pool,
        )
    else:
        raise INVALID_CERTIFICATE


def cborize_certificate_stake_credential(
    keychain: seed.Keychain, path: list[int], script_hash: bytes | None
) -> tuple[int, bytes]:
    if path:
        return 0, get_public_key_hash(keychain, path)

    if script_hash:
        return 1, script_hash

    # should be unreachable unless there's a bug in validation
    raise INVALID_CERTIFICATE


def cborize_initial_pool_registration_certificate_fields(
    certificate: CardanoTxCertificate,
) -> CborSequence:
    assert certificate.type == CardanoCertificateType.STAKE_POOL_REGISTRATION

    pool_parameters = certificate.pool_parameters
    assert pool_parameters is not None

    return (
        certificate.type,
        pool_parameters.pool_id,
        pool_parameters.vrf_key_hash,
        pool_parameters.pledge,
        pool_parameters.cost,
        cbor.Tagged(
            30,
            (
                pool_parameters.margin_numerator,
                pool_parameters.margin_denominator,
            ),
        ),
        # this relies on pool_parameters.reward_account being validated beforehand
        # in _validate_pool_parameters
        get_address_bytes_unsafe(pool_parameters.reward_account),
    )


def assert_certificate_cond(condition: bool) -> None:
    if not condition:
        raise INVALID_CERTIFICATE


def _validate_pool_parameters(
    pool_parameters: CardanoPoolParametersType, protocol_magic: int, network_id: int
) -> None:
    assert_certificate_cond(len(pool_parameters.pool_id) == POOL_HASH_SIZE)
    assert_certificate_cond(len(pool_parameters.vrf_key_hash) == VRF_KEY_HASH_SIZE)
    assert_certificate_cond(0 <= pool_parameters.pledge <= LOVELACE_MAX_SUPPLY)
    assert_certificate_cond(0 <= pool_parameters.cost <= LOVELACE_MAX_SUPPLY)
    assert_certificate_cond(pool_parameters.margin_numerator >= 0)
    assert_certificate_cond(pool_parameters.margin_denominator > 0)
    assert_certificate_cond(
        pool_parameters.margin_numerator <= pool_parameters.margin_denominator
    )
    assert_certificate_cond(pool_parameters.owners_count > 0)

    validate_reward_address(pool_parameters.reward_account, protocol_magic, network_id)

    if pool_parameters.metadata:
        _validate_pool_metadata(pool_parameters.metadata)


def validate_pool_owner(
    owner: CardanoPoolOwner, account_path_checker: AccountPathChecker
) -> None:
    assert_certificate_cond(
        owner.staking_key_hash is not None or owner.staking_key_path is not None
    )
    if owner.staking_key_hash is not None:
        assert_certificate_cond(len(owner.staking_key_hash) == ADDRESS_KEY_HASH_SIZE)
    if owner.staking_key_path:
        assert_certificate_cond(
            SCHEMA_STAKING_ANY_ACCOUNT.match(owner.staking_key_path)
        )

    account_path_checker.add_pool_owner(owner)


def validate_pool_relay(pool_relay: CardanoPoolRelayParameters) -> None:
    if pool_relay.type == CardanoPoolRelayType.SINGLE_HOST_IP:
        assert_certificate_cond(
            pool_relay.ipv4_address is not None or pool_relay.ipv6_address is not None
        )
        if pool_relay.ipv4_address is not None:
            assert_certificate_cond(len(pool_relay.ipv4_address) == IPV4_ADDRESS_SIZE)
        if pool_relay.ipv6_address is not None:
            assert_certificate_cond(len(pool_relay.ipv6_address) == IPV6_ADDRESS_SIZE)
        assert_certificate_cond(
            pool_relay.port is not None and 0 <= pool_relay.port <= MAX_PORT_NUMBER
        )
    elif pool_relay.type == CardanoPoolRelayType.SINGLE_HOST_NAME:
        assert_certificate_cond(
            pool_relay.host_name is not None
            and len(pool_relay.host_name) <= MAX_URL_LENGTH
        )
        assert_certificate_cond(
            pool_relay.port is not None and 0 <= pool_relay.port <= MAX_PORT_NUMBER
        )
    elif pool_relay.type == CardanoPoolRelayType.MULTIPLE_HOST_NAME:
        assert_certificate_cond(
            pool_relay.host_name is not None
            and len(pool_relay.host_name) <= MAX_URL_LENGTH
        )
    else:
        raise INVALID_CERTIFICATE


def _validate_pool_metadata(pool_metadata: CardanoPoolMetadataType) -> None:
    assert_certificate_cond(len(pool_metadata.url) <= MAX_URL_LENGTH)
    assert_certificate_cond(len(pool_metadata.hash) == POOL_METADATA_HASH_SIZE)
    assert_certificate_cond(all((32 <= ord(c) < 127) for c in pool_metadata.url))


def cborize_pool_owner(keychain: seed.Keychain, pool_owner: CardanoPoolOwner) -> bytes:
    if pool_owner.staking_key_path:
        return get_public_key_hash(keychain, pool_owner.staking_key_path)
    elif pool_owner.staking_key_hash:
        return pool_owner.staking_key_hash
    else:
        raise ValueError


def _cborize_ipv6_address(ipv6_address: bytes | None) -> bytes | None:
    if ipv6_address is None:
        return None

    # ipv6 addresses are serialized to CBOR as uint_32[4] little endian
    assert len(ipv6_address) == IPV6_ADDRESS_SIZE

    result = b""
    for i in range(0, 4):
        result += bytes(reversed(ipv6_address[i * 4 : i * 4 + 4]))

    return result


def cborize_pool_relay(
    pool_relay: CardanoPoolRelayParameters,
) -> CborSequence:
    if pool_relay.type == CardanoPoolRelayType.SINGLE_HOST_IP:
        return (
            pool_relay.type,
            pool_relay.port,
            pool_relay.ipv4_address,
            _cborize_ipv6_address(pool_relay.ipv6_address),
        )
    elif pool_relay.type == CardanoPoolRelayType.SINGLE_HOST_NAME:
        return (
            pool_relay.type,
            pool_relay.port,
            pool_relay.host_name,
        )
    elif pool_relay.type == CardanoPoolRelayType.MULTIPLE_HOST_NAME:
        return (
            pool_relay.type,
            pool_relay.host_name,
        )
    else:
        raise INVALID_CERTIFICATE


def cborize_pool_metadata(
    pool_metadata: CardanoPoolMetadataType | None,
) -> CborSequence | None:
    if not pool_metadata:
        return None

    return (pool_metadata.url, pool_metadata.hash)
