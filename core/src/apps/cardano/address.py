from trezor import wire
from trezor.crypto import base58, hashlib
from trezor.messages import (
    CardanoAddressParametersType,
    CardanoAddressType,
    CardanoCertificatePointerType,
)

import apps.cardano.address_id as AddressId
from apps.cardano import BYRON_PURPOSE, CURVE, SHELLEY_PURPOSE
from apps.cardano.bech32 import bech32_encode
from apps.cardano.bootstrap_address import derive_address_and_node
from apps.cardano.utils import variable_length_encode
from apps.common import HARDENED, paths
from apps.common.seed import remove_ed25519_prefix

if False:
    from trezor.messages.CardanoGetAddress import CardanoGetAddress
    from apps.cardano import seed


def validate_full_path(path: list) -> bool:
    """
    Validates derivation path to fit {44', 1852'}/1815'/a'/{0,1}/i,
    where `a` is an account number and i an address index.
    The max value for `a` is 20, 1 000 000 for `i`.
    """
    if len(path) != 5:
        return False
    if path[0] != BYRON_PURPOSE and path[0] != SHELLEY_PURPOSE:
        return False
    if path[1] != 1815 | HARDENED:
        return False
    if (
        path[2] < HARDENED or path[2] > 20 | HARDENED
    ):  # TODO do we still limit it to 20 accounts?
        return False
    if path[3] != 0 and path[3] != 1:
        return False
    if path[4] > 1000000:  # TODO do we still impose this?
        return False
    return True


async def validate_address_path(
    ctx: wire.Context, msg: CardanoGetAddress, keychains: seed.Keychains
) -> None:
    # TODO what does this do? should we call it somewhere for validation of staking key paths, too?
    await paths.validate_path(ctx, validate_full_path, keychains, msg.address_n, CURVE)


def get_human_readable_address(address: bytes) -> str:
    return bech32_encode("addr", address)


def derive_address(
    keychains: seed.Keychains,
    parameters: CardanoAddressParametersType,
    network_id: int,
    human_readable: bool = True,
) -> str:
    if parameters.address_type == CardanoAddressType.BOOTSTRAP_ADDRESS:
        address = _derive_bootstrap_address(keychains, parameters.address_n)
        if human_readable:
            return address
        else:
            return base58.decode(address)

    if parameters.address_type == CardanoAddressType.BASE_ADDRESS:
        address = _derive_base_address(
            keychains, parameters.address_n, network_id, parameters.staking_key_hash
        )
    elif parameters.address_type == CardanoAddressType.ENTERPRISE_ADDRESS:
        address = _derive_enterprise_address(
            keychains, parameters.address_n, network_id
        )
    elif parameters.address_type == CardanoAddressType.POINTER_ADDRESS:
        address = _derive_pointer_address(
            keychains, parameters.address_n, network_id, parameters.certificate_pointer,
        )
    else:
        raise ValueError("Invalid address type '%s'" % parameters.address_type)

    if human_readable:
        return get_human_readable_address(address)
    else:
        return address


def _derive_base_address(
    keychains: seed.Keychains, path: list, network_id: int, staking_key_hash: bytes,
) -> str:
    if not _validate_shelley_address_path(path):
        raise wire.DataError("Invalid path for base address")

    spending_part = _get_spending_part(keychains, path)

    if staking_key_hash is None:
        staking_part = get_staking_key_hash(keychains, path)
    else:
        staking_part = staking_key_hash

    address_header = _get_address_header(CardanoAddressType.BASE_ADDRESS, network_id)
    address = address_header + spending_part + staking_part

    return address


def _derive_pointer_address(
    keychains: seed.Keychains,
    path: list,
    network_id: int,
    pointer: CardanoCertificatePointerType,
) -> str:
    if not _validate_shelley_address_path(path):
        raise wire.DataError("Invalid path for pointer address")

    spending_part = _get_spending_part(keychains, path)

    address_header = _get_address_header(CardanoAddressType.POINTER_ADDRESS, network_id)
    encoded_pointer = _encode_certificate_pointer(pointer)
    address = address_header + spending_part + encoded_pointer

    return address


def _derive_enterprise_address(
    keychains: seed.Keychains, path: list, network_id: int
) -> str:
    if not _validate_shelley_address_path(path):
        raise wire.DataError("Invalid path for enterprise address")

    spending_part = _get_spending_part(keychains, path)

    address_header = _get_address_header(
        CardanoAddressType.ENTERPRISE_ADDRESS, network_id
    )
    address = address_header + spending_part

    return address


def _derive_bootstrap_address(keychains: seed.Keychains, path: list) -> str:
    if not _validate_bootstrap_address_path(path):
        raise wire.DataError("Invalid path for bootstrap address")

    address, _ = derive_address_and_node(keychains, path)
    return address


def _validate_shelley_address_path(path: list) -> bool:
    return path[0] == SHELLEY_PURPOSE


def _validate_bootstrap_address_path(path: list) -> bool:
    return path[0] == BYRON_PURPOSE


def _get_spending_part(keychains: seed.Keychains, path: list) -> bytes:
    spending_node = keychains.derive(path)
    spending_key = remove_ed25519_prefix(spending_node.public_key())
    return hashlib.blake2b(data=spending_key, outlen=28).digest()


def get_staking_key_hash(keychains: seed.Keychains, path: list) -> bytes:
    staking_path = _path_to_staking_path(path)
    staking_node = keychains.derive(staking_path)
    staking_key = remove_ed25519_prefix(staking_node.public_key())
    return hashlib.blake2b(data=staking_key, outlen=28).digest()


def _path_to_staking_path(path: list) -> list:
    return path[:3] + [2, 0]


def _get_address_header(address_type: int, network_id: int) -> bytes:
    if address_type == CardanoAddressType.BOOTSTRAP_ADDRESS:
        """
        Bootstrap addresses don't have an explicit header in the Shelley
        spec. However, thanks to their CBOR structure they always start with
        0b1000 - the bootstrap address id. This is no coincidence.
        The Shelley address headers are purposefully built around these
        starting bits of the bootstrap address.
        """
        raise ValueError("Bootstrap address does not contain an explicit header")

    address_id = _get_address_id(address_type)
    header = address_id << 4 | network_id

    return bytes([header])


def _get_address_id(address_type: int) -> int:
    # todo: GK - script combinations
    if address_type == CardanoAddressType.BASE_ADDRESS:
        address_id = AddressId.BASE_ADDRESS_KEY_KEY
    elif address_type == CardanoAddressType.POINTER_ADDRESS:
        address_id = AddressId.POINTER_ADDRESS_KEY
    elif address_type == CardanoAddressType.ENTERPRISE_ADDRESS:
        address_id = AddressId.ENTERPRISE_ADDRESS_KEY
    elif address_type == CardanoAddressType.BOOTSTRAP_ADDRESS:
        address_id = AddressId.BOOTSTRAP_ADDRESS_ID
    else:
        raise wire.DataError("Invalid address type")

    return address_id


def _encode_certificate_pointer(pointer: CardanoCertificatePointerType) -> bytes:
    block_index_encoded = variable_length_encode(pointer.block_index)
    tx_index_encoded = variable_length_encode(pointer.tx_index)
    certificate_index_encoded = variable_length_encode(pointer.certificate_index)

    return bytes(block_index_encoded + tx_index_encoded + certificate_index_encoded)
