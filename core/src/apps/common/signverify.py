from ubinascii import hexlify

from trezor import ui, utils, wire
from trezor.crypto.hashlib import blake256, sha256
from trezor.ui.components.tt.text import Text

from apps.common.confirm import require_confirm
from apps.common.layout import paginate_text, split_address
from apps.common.writers import write_bitcoin_varint

if False:
    from apps.common.coininfo import CoinInfo


def message_digest(coin: CoinInfo, message: bytes) -> bytes:
    if not utils.BITCOIN_ONLY and coin.decred:
        h = utils.HashWriter(blake256())
    else:
        h = utils.HashWriter(sha256())
    if not coin.signed_message_header:
        raise wire.DataError("Empty message header not allowed.")
    write_bitcoin_varint(h, len(coin.signed_message_header))
    h.extend(coin.signed_message_header.encode())
    write_bitcoin_varint(h, len(message))
    h.extend(message)
    ret = h.get_digest()
    if coin.sign_hash_double:
        ret = sha256(ret).digest()
    return ret


def decode_message(message: bytes) -> str:
    try:
        return bytes(message).decode()
    except UnicodeError:
        return "hex(%s)" % hexlify(message).decode()


async def require_confirm_sign_message(
    ctx: wire.Context, coin: str, message: bytes
) -> None:
    header = "Sign {} message".format(coin)
    await require_confirm(ctx, paginate_text(decode_message(message), header))


async def require_confirm_verify_message(
    ctx: wire.Context, address: str, coin: str, message: bytes
) -> None:
    header = "Verify {} message".format(coin)
    text = Text(header, new_lines=False)
    text.bold("Confirm address:")
    text.br()
    text.mono(*split_address(address))
    await require_confirm(ctx, text)

    await require_confirm(
        ctx,
        paginate_text(decode_message(message), header, font=ui.MONO),
    )
