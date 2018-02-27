from ubinascii import hexlify
from trezor.crypto.hashlib import sha256
from trezor.utils import chunks, split_words
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
    try:
        m = bytes(message).decode()
        lines = split_words(m, 18)
    except UnicodeError:
        m = hexlify(message)
        lines = chunks(m, 16)
    return lines
