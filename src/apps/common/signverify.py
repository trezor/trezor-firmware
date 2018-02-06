from micropython import const
from trezor.crypto.hashlib import sha256
from trezor.utils import chunks
from apps.common.hash_writer import HashWriter
from apps.wallet.sign_tx.signing import write_varint


def message_digest(coin, message):
    h = HashWriter(sha256)
    write_varint(h, len(coin.signed_message_header))
    h.extend(coin.signed_message_header)
    write_varint(h, len(message))
    h.extend(message)
    return sha256(h.get_digest()).digest()


def split_message(message):
    chars_per_line = const(18)
    message = stringify_message(message)
    lines = chunks(message, chars_per_line)
    return lines


def stringify_message(message):
    # TODO: account for invalid UTF-8 sequences
    return str(message, 'utf-8')
