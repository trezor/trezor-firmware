from trezor.enums import CardanoCertificateType, CardanoPoolRelayType

from apps.common import cbor

from .address import (
    get_address_bytes_unsafe,
    get_public_key_hash,
    validate_reward_address,
)
from .helpers import ADDRESS_KEY_HASH_SIZE, INVALID_CERTIFICATE, LOVELACE_MAX_SUPPLY
from .helpers.paths import SCHEMA_STAKING_ANY_ACCOUNT

if False:
    from trezor.messages import (
        CardanoPoolMetadataType,
        CardanoPoolOwnerType,
        CardanoPoolParametersType,
        CardanoPoolRelayParametersType,
        CardanoTxCertificateType,
    )

    from apps.common.cbor import CborSequence

    from . import seed

POOL_HASH_SIZE = 28
VRF_KEY_HASH_SIZE = 32
POOL_METADATA_HASH_SIZE = 32
IPV4_ADDRESS_SIZE = 4
IPV6_ADDRESS_SIZE = 16

MAX_URL_LENGTH = 64
MAX_PORT_NUMBER = 65535


def validate_certificate(
    certificate: CardanoTxCertificateType, protocol_magic: int, network_id: int
) -> None:
    if certificate.type in (
        CardanoCertificateType.STAKE_DELEGATION,
        CardanoCertificateType.STAKE_REGISTRATION,
        CardanoCertificateType.STAKE_DEREGISTRATION,
    ):
        if not SCHEMA_STAKING_ANY_ACCOUNT.match(certificate.path):
            raise INVALID_CERTIFICATE

    if certificate.type == CardanoCertificateType.STAKE_DELEGATION:
        if not certificate.pool or len(certificate.pool) != POOL_HASH_SIZE:
            raise INVALID_CERTIFICATE

    if certificate.type == CardanoCertificateType.STAKE_POOL_REGISTRATION:
        if certificate.pool_parameters is None:
            raise INVALID_CERTIFICATE
        _validate_pool_parameters(
            certificate.pool_parameters, protocol_magic, network_id
        )


def cborize_certificate(
    keychain: seed.Keychain, certificate: CardanoTxCertificateType
) -> CborSequence:
    if certificate.type in (
        CardanoCertificateType.STAKE_REGISTRATION,
        CardanoCertificateType.STAKE_DEREGISTRATION,
    ):
        return (
            certificate.type,
            (0, get_public_key_hash(keychain, certificate.path)),
        )
    elif certificate.type == CardanoCertificateType.STAKE_DELEGATION:
        return (
            certificate.type,
            (0, get_public_key_hash(keychain, certificate.path)),
            certificate.pool,
        )
    elif certificate.type == CardanoCertificateType.STAKE_POOL_REGISTRATION:
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
            _cborize_pool_owners(keychain, pool_parameters.owners),
            _cborize_pool_relays(pool_parameters.relays),
            _cborize_pool_metadata(pool_parameters.metadata),
        )
    else:
        raise INVALID_CERTIFICATE


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
    assert_certificate_cond(len(pool_parameters.owners) > 0)

    validate_reward_address(pool_parameters.reward_account, protocol_magic, network_id)

    for pool_relay in pool_parameters.relays:
        _validate_pool_relay(pool_relay)

    _validate_pool_owners(pool_parameters.owners)

    if pool_parameters.metadata:
        _validate_pool_metadata(pool_parameters.metadata)


def _validate_pool_owners(owners: list[CardanoPoolOwnerType]) -> None:
    owners_as_path_count = 0
    for owner in owners:
        assert_certificate_cond(
            owner.staking_key_hash is not None or owner.staking_key_path is not None
        )
        if owner.staking_key_hash is not None:
            assert_certificate_cond(
                len(owner.staking_key_hash) == ADDRESS_KEY_HASH_SIZE
            )
        if owner.staking_key_path:
            assert_certificate_cond(
                SCHEMA_STAKING_ANY_ACCOUNT.match(owner.staking_key_path)
            )

        if owner.staking_key_path:
            owners_as_path_count += 1

    assert_certificate_cond(owners_as_path_count == 1)


def _validate_pool_relay(pool_relay: CardanoPoolRelayParametersType) -> None:
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


def _cborize_pool_owners(
    keychain: seed.Keychain, pool_owners: list[CardanoPoolOwnerType]
) -> list[bytes]:
    result = []

    for pool_owner in pool_owners:
        if pool_owner.staking_key_path:
            result.append(get_public_key_hash(keychain, pool_owner.staking_key_path))
        elif pool_owner.staking_key_hash:
            result.append(pool_owner.staking_key_hash)
        else:
            raise ValueError

    return result


def _cborize_ipv6_address(ipv6_address: bytes | None) -> bytes | None:
    if ipv6_address is None:
        return None

    # ipv6 addresses are serialized to CBOR as uint_32[4] little endian
    assert len(ipv6_address) == IPV6_ADDRESS_SIZE

    result = b""
    for i in range(0, 4):
        result += bytes(reversed(ipv6_address[i * 4 : i * 4 + 4]))

    return result


def _cborize_pool_relays(
    pool_relays: list[CardanoPoolRelayParametersType],
) -> list[CborSequence]:
    result: list[CborSequence] = []

    for pool_relay in pool_relays:
        if pool_relay.type == CardanoPoolRelayType.SINGLE_HOST_IP:
            result.append(
                (
                    pool_relay.type,
                    pool_relay.port,
                    pool_relay.ipv4_address,
                    _cborize_ipv6_address(pool_relay.ipv6_address),
                )
            )
        elif pool_relay.type == CardanoPoolRelayType.SINGLE_HOST_NAME:
            result.append(
                (
                    pool_relay.type,
                    pool_relay.port,
                    pool_relay.host_name,
                )
            )
        elif pool_relay.type == CardanoPoolRelayType.MULTIPLE_HOST_NAME:
            result.append(
                (
                    pool_relay.type,
                    pool_relay.host_name,
                )
            )

    return result


def _cborize_pool_metadata(
    pool_metadata: CardanoPoolMetadataType | None,
) -> CborSequence | None:
    if not pool_metadata:
        return None

    return (pool_metadata.url, pool_metadata.hash)
