from trezor import wire
from trezor.crypto.curve import secp256k1
from trezor.messages.InputScriptType import SPENDADDRESS, SPENDP2SHWITNESS, SPENDWITNESS
from trezor.messages.MessageSignature import MessageSignature
from trezor.ui.text import Text

from apps.common import coins
from apps.common.paths import validate_path
from apps.common.signverify import split_message, tpos_digest
from apps.wallet.sign_tx.addresses import get_address, validate_full_path


async def sign_tpos_contract(ctx, msg, keychain):
    tpos = msg.tpos
    address_n = msg.address_n
    coin_name = msg.coin_name or "Bitcoin"
    script_type = msg.script_type or 0
    coin = coins.by_name(coin_name)

    await require_confirm_sign_tpos_contract(ctx, tpos)
    await validate_path(
        ctx,
        validate_full_path,
        keychain,
        msg.address_n,
        coin.curve_name,
        coin=coin,
        script_type=msg.script_type,
        validate_script_type=False,
    )

    node = keychain.derive(address_n, coin.curve_name)
    seckey = node.private_key()

    address = get_address(script_type, coin, node)
    serialized_tpos = serialize(tpos)
    digest = tpos_digest(coin, serialized_tpos)

    signature = secp256k1.sign(seckey, digest)

    if script_type == SPENDADDRESS:
        pass
    elif script_type == SPENDP2SHWITNESS:
        signature = bytes([signature[0] + 4]) + signature[1:]
    elif script_type == SPENDWITNESS:
        signature = bytes([signature[0] + 8]) + signature[1:]
    else:
        raise wire.ProcessError("Unsupported script type")

    return MessageSignature(address=address, signature=signature)


def serialize(tpos):
    tpos = list(tpos)
    separator = tpos.index(ord(":"))
    prev_hash = bytes(tpos[:separator])
    prev_hash = [int(prev_hash[i : i + 2], 16) for i in range(0, len(prev_hash), 2)]
    prev_hash.reverse()
    prev_hash = bytes(prev_hash)

    nout = map(lambda n: str(n - ord("0")), tpos[separator + 1 :])
    nout = int("".join(nout))

    nout = bytes(nout.to_bytes(4, "big"))

    return prev_hash + nout


async def require_confirm_sign_tpos_contract(ctx, tpos):
    tpos = split_message(tpos)
    text = Text("Sign tpos contract", new_lines=False)
    text.normal(*tpos)
