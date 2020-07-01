from micropython import const

from trezor import log, wire
from trezor.crypto import base58, hashlib
from trezor.crypto.curve import ed25519
from trezor.messages.CardanoSignedTx import CardanoSignedTx

from apps.common import cbor
from apps.common.paths import validate_path
from apps.common.seed import remove_ed25519_prefix

from . import CURVE, seed
from .address import (
    derive_address_and_node,
    get_address_attributes,
    validate_full_path,
    validate_output_address,
)
from .layout import confirm_sending, confirm_transaction

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

        for i in msg.inputs:
            await validate_path(ctx, validate_full_path, keychain, i.address_n, CURVE)

        _validate_outputs(keychain, msg.outputs, msg.protocol_magic)

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


def _validate_outputs(
    keychain: seed.Keychain, outputs: List[CardanoTxOutputType], protocol_magic: int
) -> None:
    total_amount = 0
    for output in outputs:
        total_amount += output.amount
        if output.address_n:
            continue
        elif output.address is not None:
            validate_output_address(output.address, protocol_magic)
        else:
            raise wire.ProcessError("Each output must have address or address_n field!")

    if total_amount > LOVELACE_MAX_SUPPLY:
        raise wire.ProcessError("Total transaction amount is out of range!")


def _serialize_tx(keychain: seed.Keychain, msg: CardanoSignTx) -> Tuple[bytes, bytes]:
    tx_body = _build_tx_body(keychain, msg)
    tx_hash = _hash_tx_body(tx_body)

    witnesses_for_cbor = _build_witnesses(
        keychain, msg.inputs, tx_hash, msg.protocol_magic
    )
    # byron witnesses have the key 2 in Shelley
    witnesses = {2: witnesses_for_cbor}

    serialized_tx = cbor.encode([tx_body, witnesses, None])

    return serialized_tx, tx_hash


def _build_tx_body(keychain: seed.Keychain, msg: CardanoSignTx) -> Dict:
    inputs_for_cbor = _build_inputs(msg.inputs)
    outputs_for_cbor = _build_outputs(keychain, msg.outputs, msg.protocol_magic)

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
    keychain: seed.Keychain, outputs: List[CardanoTxOutputType], protocol_magic: int
) -> List[Tuple[bytes, int]]:
    result = []
    for output in outputs:
        amount = output.amount
        if output.address_n:
            address, _ = derive_address_and_node(
                keychain, output.address_n, protocol_magic
            )
        else:
            address = output.address

        result.append((base58.decode(address), amount))

    return result


def _hash_tx_body(tx_body: Dict) -> bytes:
    tx_body_cbor = cbor.encode(tx_body)
    return hashlib.blake2b(data=tx_body_cbor, outlen=32).digest()


def _build_witnesses(
    keychain: seed.Keychain,
    inputs: List[CardanoTxInputType],
    tx_body_hash: bytes,
    protocol_magic: int,
) -> List[Tuple[bytes, bytes, bytes, bytes]]:
    result = []
    for input in inputs:
        node = keychain.derive(input.address_n)

        public_key = remove_ed25519_prefix(node.public_key())
        signature = ed25519.sign_ext(
            node.private_key(), node.private_key_ext(), tx_body_hash
        )
        chain_code = node.chain_code()
        address_attributes = cbor.encode(get_address_attributes(protocol_magic))

        result.append((public_key, signature, chain_code, address_attributes))

    return result


async def _show_tx(
    ctx: wire.Context, keychain: seed.Keychain, msg: CardanoSignTx
) -> None:
    total_amount = 0
    for output in msg.outputs:
        if _should_hide_output(output.address_n, msg.inputs):
            continue

        total_amount += output.amount

        if not output.address:
            address, _ = derive_address_and_node(
                keychain, output.address_n, msg.protocol_magic
            )
        else:
            address = output.address

        await confirm_sending(ctx, output.amount, address)

    await confirm_transaction(ctx, total_amount, msg.fee, msg.protocol_magic)


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
