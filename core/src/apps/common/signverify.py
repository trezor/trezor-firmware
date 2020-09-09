from ubinascii import hexlify

from trezor import utils, wire
from trezor.crypto.hashlib import blake256, sha256
from trezor.ui.text import Text

from apps.common.confirm import require_confirm
from apps.common.layout import split_address
from apps.common.writers import write_bitcoin_varint

if False:
    from typing import List
    from apps.common.coininfo import CoinType


def message_digest(coin: CoinType, message: bytes) -> bytes:
    if not utils.BITCOIN_ONLY and coin.decred:
        h = utils.HashWriter(blake256())
    else:
        h = utils.HashWriter(sha256())
    if not coin.signed_message_header:
        raise wire.DataError("Empty message header not allowed.")
    write_bitcoin_varint(h, len(coin.signed_message_header))
    h.extend(coin.signed_message_header)
    write_bitcoin_varint(h, len(message))
    h.extend(message)
    ret = h.get_digest()
    if coin.sign_hash_double:
        ret = sha256(ret).digest()
    return ret


def split_message(message: bytes) -> List[str]:
    try:
        m = bytes(message).decode()
        words = m.split(" ")
    except UnicodeError:
        m = "hex(%s)" % hexlify(message).decode()
        words = [m]
    return words


async def require_confirm_sign_message(
    ctx: wire.Context, coin: str, message: bytes
) -> None:
    header = "Sign {} message".format(coin)
    message = split_message(message)
    text = Text(header, new_lines=False)
    text.normal(*message)
    await require_confirm(ctx, text)


async def require_confirm_verify_message(
    ctx: wire.Context, address: str, coin: str, message: bytes
) -> None:
    header = "Verify {} message".format(coin)
    text = Text(header, new_lines=False)
    text.bold("Confirm address:")
    text.br()
    text.mono(*split_address(address))
    await require_confirm(ctx, text)

    text = Text(header, new_lines=False)
    text.mono(*split_message(message))
    await require_confirm(ctx, text)
