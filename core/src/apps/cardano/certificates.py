from micropython import const
from typing import TYPE_CHECKING

from trezor.enums import CardanoCertificateType, CardanoPoolRelayType
from trezor.wire import ProcessError

from . import addresses
from .helpers.utils import get_public_key_hash

if TYPE_CHECKING:
    from typing import Any

    from trezor import messages

    from apps.common.cbor import CborSequence

    from . import seed
    from .helpers.account_path_check import AccountPathChecker

_POOL_HASH_SIZE = const(28)
_VRF_KEY_HASH_SIZE = const(32)
_POOL_METADATA_HASH_SIZE = const(32)
_IPV4_ADDRESS_SIZE = const(4)
_IPV6_ADDRESS_SIZE = const(16)

_MAX_URL_LENGTH = const(64)
_MAX_PORT_NUMBER = const(65535)


def validate(
    certificate: messages.CardanoTxCertificate,
    protocol_magic: int,
    network_id: int,
    account_path_checker: AccountPathChecker,
) -> None:
    from .helpers.utils import validate_stake_credential

    _validate_structure(certificate)

    CCT = CardanoCertificateType  # local_cache_global

    if certificate.type in (
        CCT.STAKE_DELEGATION,
        CCT.STAKE_REGISTRATION,
        CCT.STAKE_DEREGISTRATION,
    ):
        validate_stake_credential(
            certificate.path,
            certificate.script_hash,
            certificate.key_hash,
            ProcessError("Invalid certificate"),
        )

    if certificate.type == CCT.STAKE_DELEGATION:
        if not certificate.pool or len(certificate.pool) != _POOL_HASH_SIZE:
            raise ProcessError("Invalid certificate")

    if certificate.type == CCT.STAKE_POOL_REGISTRATION:
        if certificate.pool_parameters is None:
            raise ProcessError("Invalid certificate")
        _validate_pool_parameters(
            certificate.pool_parameters, protocol_magic, network_id
        )

    account_path_checker.add_certificate(certificate)


def _validate_structure(certificate: messages.CardanoTxCertificate) -> None:
    pool = certificate.pool  # local_cache_attribute
    pool_parameters = certificate.pool_parameters  # local_cache_attribute
    CCT = CardanoCertificateType  # local_cache_global

    fields_to_be_empty: dict[CCT, tuple[Any, ...]] = {
        CCT.STAKE_REGISTRATION: (pool, pool_parameters),
        CCT.STAKE_DELEGATION: (pool_parameters,),
        CCT.STAKE_DEREGISTRATION: (pool, pool_parameters),
        CCT.STAKE_POOL_REGISTRATION: (
            certificate.path,
            certificate.script_hash,
            certificate.key_hash,
            pool,
        ),
    }

    if certificate.type not in fields_to_be_empty or any(
        fields_to_be_empty[certificate.type]
    ):
        raise ProcessError("Invalid certificate")


def cborize(
    keychain: seed.Keychain, certificate: messages.CardanoTxCertificate
) -> CborSequence:
    cert_type = certificate.type  # local_cache_attribute

    if cert_type in (
        CardanoCertificateType.STAKE_REGISTRATION,
        CardanoCertificateType.STAKE_DEREGISTRATION,
    ):
        return (
            cert_type,
            cborize_stake_credential(
                keychain,
                certificate.path,
                certificate.script_hash,
                certificate.key_hash,
            ),
        )
    elif cert_type == CardanoCertificateType.STAKE_DELEGATION:
        return (
            cert_type,
            cborize_stake_credential(
                keychain,
                certificate.path,
                certificate.script_hash,
                certificate.key_hash,
            ),
            certificate.pool,
        )
    else:
        raise RuntimeError  # should be unreachable


def cborize_stake_credential(
    keychain: seed.Keychain,
    path: list[int],
    script_hash: bytes | None,
    key_hash: bytes | None,
) -> tuple[int, bytes]:
    if key_hash or path:
        return 0, key_hash or get_public_key_hash(keychain, path)

    if script_hash:
        return 1, script_hash

    # should be unreachable unless there's a bug in validation
    raise RuntimeError


def cborize_pool_registration_init(
    certificate: messages.CardanoTxCertificate,
) -> CborSequence:
    from apps.common import cbor

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
        addresses.get_bytes_unsafe(pool_parameters.reward_account),
    )


def assert_cond(condition: bool) -> None:
    if not condition:
        raise ProcessError("Invalid certificate")


def _validate_pool_parameters(
    pool_parameters: messages.CardanoPoolParametersType,
    protocol_magic: int,
    network_id: int,
) -> None:
    from .helpers import LOVELACE_MAX_SUPPLY

    assert_cond(len(pool_parameters.pool_id) == _POOL_HASH_SIZE)
    assert_cond(len(pool_parameters.vrf_key_hash) == _VRF_KEY_HASH_SIZE)
    assert_cond(0 <= pool_parameters.pledge <= LOVELACE_MAX_SUPPLY)
    assert_cond(0 <= pool_parameters.cost <= LOVELACE_MAX_SUPPLY)
    assert_cond(pool_parameters.margin_numerator >= 0)
    assert_cond(pool_parameters.margin_denominator > 0)
    assert_cond(pool_parameters.margin_numerator <= pool_parameters.margin_denominator)
    assert_cond(pool_parameters.owners_count > 0)

    addresses.validate_reward_address(
        pool_parameters.reward_account, protocol_magic, network_id
    )
    pool_metadata = pool_parameters.metadata  # local_cache_attribute
    if pool_metadata:
        # _validate_pool_metadata
        assert_cond(len(pool_metadata.url) <= _MAX_URL_LENGTH)
        assert_cond(len(pool_metadata.hash) == _POOL_METADATA_HASH_SIZE)
        assert_cond(all((32 <= ord(c) < 127) for c in pool_metadata.url))


def validate_pool_owner(
    owner: messages.CardanoPoolOwner, account_path_checker: AccountPathChecker
) -> None:
    from .helpers import ADDRESS_KEY_HASH_SIZE
    from .helpers.paths import SCHEMA_STAKING_ANY_ACCOUNT

    assert_cond(
        owner.staking_key_hash is not None or owner.staking_key_path is not None
    )
    if owner.staking_key_hash is not None:
        assert_cond(len(owner.staking_key_hash) == ADDRESS_KEY_HASH_SIZE)
    if owner.staking_key_path:
        assert_cond(SCHEMA_STAKING_ANY_ACCOUNT.match(owner.staking_key_path))

    account_path_checker.add_pool_owner(owner)


def validate_pool_relay(pool_relay: messages.CardanoPoolRelayParameters) -> None:
    port = pool_relay.port  # local_cache_attribute
    host_name = pool_relay.host_name  # local_cache_attribute

    if pool_relay.type == CardanoPoolRelayType.SINGLE_HOST_IP:
        assert_cond(
            pool_relay.ipv4_address is not None or pool_relay.ipv6_address is not None
        )
        if pool_relay.ipv4_address is not None:
            assert_cond(len(pool_relay.ipv4_address) == _IPV4_ADDRESS_SIZE)
        if pool_relay.ipv6_address is not None:
            assert_cond(len(pool_relay.ipv6_address) == _IPV6_ADDRESS_SIZE)
        assert_cond(port is not None and 0 <= port <= _MAX_PORT_NUMBER)
    elif pool_relay.type == CardanoPoolRelayType.SINGLE_HOST_NAME:
        assert_cond(host_name is not None and len(host_name) <= _MAX_URL_LENGTH)
        assert_cond(port is not None and 0 <= port <= _MAX_PORT_NUMBER)
    elif pool_relay.type == CardanoPoolRelayType.MULTIPLE_HOST_NAME:
        assert_cond(host_name is not None and len(host_name) <= _MAX_URL_LENGTH)
    else:
        raise RuntimeError  # should be unreachable


def cborize_pool_owner(
    keychain: seed.Keychain, pool_owner: messages.CardanoPoolOwner
) -> bytes:
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
    assert len(ipv6_address) == _IPV6_ADDRESS_SIZE

    result = b""
    for i in range(0, 4):
        result += bytes(reversed(ipv6_address[i * 4 : i * 4 + 4]))

    return result


def cborize_pool_relay(
    pool_relay: messages.CardanoPoolRelayParameters,
) -> CborSequence:
    relay_type = pool_relay.type  # local_cache_attribute

    if relay_type == CardanoPoolRelayType.SINGLE_HOST_IP:
        return (
            relay_type,
            pool_relay.port,
            pool_relay.ipv4_address,
            _cborize_ipv6_address(pool_relay.ipv6_address),
        )
    elif relay_type == CardanoPoolRelayType.SINGLE_HOST_NAME:
        return (
            relay_type,
            pool_relay.port,
            pool_relay.host_name,
        )
    elif relay_type == CardanoPoolRelayType.MULTIPLE_HOST_NAME:
        return (
            relay_type,
            pool_relay.host_name,
        )
    else:
        raise RuntimeError  # should be unreachable


def cborize_pool_metadata(
    pool_metadata: messages.CardanoPoolMetadataType | None,
) -> CborSequence | None:
    if not pool_metadata:
        return None

    return (pool_metadata.url, pool_metadata.hash)
