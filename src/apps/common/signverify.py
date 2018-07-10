from ubinascii import hexlify

from trezor import ui
from trezor.crypto.hashlib import sha256
from trezor.ui.text import TEXT_MARGIN_LEFT
from trezor.utils import HashWriter, chunks, split_words

from apps.wallet.sign_tx.signing import write_varint


def message_digest(coin, message):
    h = HashWriter(sha256)
    write_varint(h, len(coin.signed_message_header))
    h.extend(coin.signed_message_header)
    write_varint(h, len(message))
    h.extend(message)
    ret = h.get_digest()
    if coin.sign_hash_double:
        ret = sha256(ret).digest()
    return ret


def split_message(message):
    def measure(s):
        return ui.display.text_width(s, ui.NORMAL)

    try:
        m = bytes(message).decode()
        lines = split_words(m, ui.WIDTH - 2 * TEXT_MARGIN_LEFT, metric=measure)
    except UnicodeError:
        m = hexlify(message)
        lines = chunks(m, 16)
    return lines
