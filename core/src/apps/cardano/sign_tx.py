from micropython import const

from trezor import log, wire
from trezor.crypto import hashlib
from trezor.crypto.curve import ed25519
from trezor.messages import CardanoAddressParametersType
from trezor.messages.CardanoSignedTx import CardanoSignedTx

from apps.common import cbor
from apps.common.paths import validate_path
from apps.common.seed import remove_ed25519_prefix

from . import CURVE, seed
from .address import (
    derive_address_bytes,
    derive_human_readable_address,
    get_address_bytes_unsafe,
    to_account_path,
    validate_full_path,
    validate_output_address,
)
from .byron_address import get_address_attributes
from .helpers import network_ids, protocol_magics, staking_use_cases
from .layout import (
    confirm_sending,
    confirm_transaction,
    show_warning_tx_different_staking_account,
    show_warning_tx_no_staking_info,
    show_warning_tx_pointer_address,
    show_warning_tx_staking_key_hash,
)
from .seed import is_byron_path, is_shelley_path

if False:
    from typing import Dict, List, Tuple
    from trezor.messages.CardanoSignTx import CardanoSignTx
    from trezor.messages.CardanoTxInputType import CardanoTxInputType
    from trezor.messages.CardanoTxOutputType import CardanoTxOutputType

# the maximum allowed change address.  this should be large enough for normal
# use and still allow to quickly brute-force the correct bip32 path
MAX_CHANGE_ADDRESS_INDEX = const(1000000)
ACCOUNT_PATH_INDEX = const(2)
BIP_PATH_LENGTH = const(5)

LOVELACE_MAX_SUPPLY = 45_000_000_000 * 1_000_000


@seed.with_keychain
async def sign_tx(
    ctx: wire.Context, msg: CardanoSignTx, keychain: seed.Keychain
) -> CardanoSignedTx:
    try:
        if msg.fee > LOVELACE_MAX_SUPPLY:
            raise wire.ProcessError("Fee is out of range!")

        _validate_network_info(msg.network_id, msg.protocol_magic)

        for i in msg.inputs:
            await validate_path(ctx, validate_full_path, keychain, i.address_n, CURVE)

        _validate_outputs(keychain, msg.outputs, msg.protocol_magic, msg.network_id)

        # display the transaction in UI
        await _show_tx(ctx, keychain, msg)

        # sign the transaction bundle and prepare the result
        serialized_tx, tx_hash = _serialize_tx(keychain, msg)
        tx = CardanoSignedTx(serialized_tx=serialized_tx, tx_hash=tx_hash)

    except ValueError as e:
        if __debug__:
            log.exception(__name__, e)
        raise wire.ProcessError("Signing failed")

    return tx


def _validate_network_info(network_id: int, protocol_magic: int) -> None:
    """
    We are only concerned about checking that both network_id and protocol_magic
    belong to the mainnet or that both belong to a testnet. We don't need to check for
    consistency between various testnets (at least for now).
    """
    is_mainnet_network_id = network_ids.is_mainnet(network_id)
    is_mainnet_protocol_magic = protocol_magics.is_mainnet(protocol_magic)

    if is_mainnet_network_id != is_mainnet_protocol_magic:
        raise wire.ProcessError("Invalid network id/protocol magic combination!")


def _validate_outputs(
    keychain: seed.Keychain,
    outputs: List[CardanoTxOutputType],
    protocol_magic: int,
    network_id: int,
) -> None:
    if not outputs:
        raise wire.ProcessError("Transaction has no outputs!")

    total_amount = 0
    for output in outputs:
        total_amount += output.amount
        if output.address_parameters:
            # try to derive the address to validate it
            derive_address_bytes(
                keychain, output.address_parameters, protocol_magic, network_id
            )
        elif output.address is not None:
            validate_output_address(output.address, protocol_magic, network_id)
        else:
            raise wire.ProcessError(
                "Each output must have an address field or address_parameters!"
            )

    if total_amount > LOVELACE_MAX_SUPPLY:
        raise wire.ProcessError("Total transaction amount is out of range!")


def _serialize_tx(keychain: seed.Keychain, msg: CardanoSignTx) -> Tuple[bytes, bytes]:
    tx_body = _build_tx_body(keychain, msg)
    tx_hash = _hash_tx_body(tx_body)

    witnesses = _build_witnesses(keychain, msg.inputs, tx_hash, msg.protocol_magic)

    serialized_tx = cbor.encode([tx_body, witnesses, None])

    return serialized_tx, tx_hash


def _build_tx_body(keychain: seed.Keychain, msg: CardanoSignTx) -> Dict:
    inputs_for_cbor = _build_inputs(msg.inputs)
    outputs_for_cbor = _build_outputs(
        keychain, msg.outputs, msg.protocol_magic, msg.network_id
    )

    tx_body = {
        0: inputs_for_cbor,
        1: outputs_for_cbor,
        2: msg.fee,
        3: msg.ttl,
    }

    return tx_body


def _build_inputs(inputs: List[CardanoTxInputType]) -> List[Tuple[bytes, int]]:
    return [(input.prev_hash, input.prev_index) for input in inputs]


def _build_outputs(
    keychain: seed.Keychain,
    outputs: List[CardanoTxOutputType],
    protocol_magic: int,
    network_id: int,
) -> List[Tuple[bytes, int]]:
    result = []
    for output in outputs:
        amount = output.amount
        if output.address_parameters:
            address = derive_address_bytes(
                keychain, output.address_parameters, protocol_magic, network_id
            )
        else:
            # output address is validated in _validate_outputs before this happens
            address = get_address_bytes_unsafe(output.address)

        result.append((address, amount))

    return result


def _hash_tx_body(tx_body: Dict) -> bytes:
    tx_body_cbor = cbor.encode(tx_body)
    return hashlib.blake2b(data=tx_body_cbor, outlen=32).digest()


def _build_witnesses(
    keychain: seed.Keychain,
    inputs: List[CardanoTxInputType],
    tx_body_hash: bytes,
    protocol_magic: int,
) -> Dict:
    shelley_witnesses = _build_shelley_witnesses(keychain, inputs, tx_body_hash)
    byron_witnesses = _build_byron_witnesses(
        keychain, inputs, tx_body_hash, protocol_magic
    )

    # use key 0 for shelley witnesses and key 2 for byron witnesses
    # according to the spec in shelley.cddl in cardano-ledger-specs
    witnesses = {}
    if len(shelley_witnesses) > 0:
        witnesses[0] = shelley_witnesses
    if len(byron_witnesses) > 0:
        witnesses[2] = byron_witnesses

    return witnesses


def _build_shelley_witnesses(
    keychain: seed.Keychain, inputs: List[CardanoTxInputType], tx_body_hash: bytes,
) -> List[Tuple[bytes, bytes]]:
    shelley_witnesses = []
    for input in inputs:
        if not is_shelley_path(input.address_n):
            continue

        node = keychain.derive(input.address_n)

        public_key = remove_ed25519_prefix(node.public_key())
        signature = ed25519.sign_ext(
            node.private_key(), node.private_key_ext(), tx_body_hash
        )
        shelley_witnesses.append((public_key, signature))

    return shelley_witnesses


def _build_byron_witnesses(
    keychain: seed.Keychain,
    inputs: List[CardanoTxInputType],
    tx_body_hash: bytes,
    protocol_magic: int,
) -> List[Tuple[bytes, bytes, bytes, bytes]]:
    byron_witnesses = []
    for input in inputs:
        if not is_byron_path(input.address_n):
            continue

        node = keychain.derive(input.address_n)

        public_key = remove_ed25519_prefix(node.public_key())
        signature = ed25519.sign_ext(
            node.private_key(), node.private_key_ext(), tx_body_hash
        )
        chain_code = node.chain_code()
        address_attributes = cbor.encode(get_address_attributes(protocol_magic))

        byron_witnesses.append((public_key, signature, chain_code, address_attributes))

    return byron_witnesses


async def _show_tx(
    ctx: wire.Context, keychain: seed.Keychain, msg: CardanoSignTx
) -> None:
    total_amount = await _show_outputs(ctx, keychain, msg)
    await confirm_transaction(ctx, total_amount, msg.fee, msg.protocol_magic)


async def _show_outputs(
    ctx: wire.Context, keychain: seed.Keychain, msg: CardanoSignTx
) -> int:
    total_amount = 0
    for output in msg.outputs:
        if output.address_parameters:
            address = derive_human_readable_address(
                keychain, output.address_parameters, msg.protocol_magic, msg.network_id
            )

            await _show_change_output_staking_warnings(
                ctx, keychain, output.address_parameters, address, output.amount
            )

            if _should_hide_output(output.address_parameters.address_n, msg.inputs):
                continue
        else:
            address = output.address

        total_amount += output.amount

        await confirm_sending(ctx, output.amount, address)

    return total_amount


async def _show_change_output_staking_warnings(
    ctx: wire.Context,
    keychain: seed.Keychain,
    address_parameters: CardanoAddressParametersType,
    address: str,
    amount: int,
):
    address_type = address_parameters.address_type

    staking_use_case = staking_use_cases.get(keychain, address_parameters)
    if staking_use_case == staking_use_cases.NO_STAKING:
        await show_warning_tx_no_staking_info(ctx, address_type, amount)
    elif staking_use_case == staking_use_cases.POINTER_ADDRESS:
        await show_warning_tx_pointer_address(
            ctx, address_parameters.certificate_pointer, amount,
        )
    elif staking_use_case == staking_use_cases.MISMATCH:
        if address_parameters.address_n_staking:
            await show_warning_tx_different_staking_account(
                ctx, to_account_path(address_parameters.address_n_staking), amount,
            )
        else:
            await show_warning_tx_staking_key_hash(
                ctx, address_parameters.staking_key_hash, amount,
            )


# addresses from the same account as inputs should be hidden
def _should_hide_output(output: List[int], inputs: List[CardanoTxInputType]) -> bool:
    for input in inputs:
        inp = input.address_n
        if (
            len(output) != BIP_PATH_LENGTH
            or output[: (ACCOUNT_PATH_INDEX + 1)] != inp[: (ACCOUNT_PATH_INDEX + 1)]
            or output[-2] >= 2
            or output[-1] >= MAX_CHANGE_ADDRESS_INDEX
        ):
            return False
    return True
