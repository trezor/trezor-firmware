from typing import TYPE_CHECKING

from apps.common.keychain import with_slip44_keychain

from . import CURVE, PATTERNS, SLIP44_ID

if TYPE_CHECKING:
    from trezor.messages import (
        SolanaSignOffChainMessage,
        SolanaOffChainMessageSignature,
    )
    from apps.common.keychain import Keychain


FORMAT_ASCII = 0
FORMAT_UTF8 = 1

MAX_MESSAGE_LENGTH = 1212


@with_slip44_keychain(*PATTERNS, slip44_id=SLIP44_ID, curve=CURVE)
async def sign_off_chain_message(
    msg: SolanaSignOffChainMessage,
    keychain: Keychain,
) -> SolanaOffChainMessageSignature:
    from trezor.crypto import base58
    from trezor.crypto.curve import ed25519
    from trezor.messages import SolanaOffChainMessageSignature
    from trezor.ui.layouts import confirm_signverify
    from apps.common import seed

    signer_path = msg.signer_path_n
    serialized_message = msg.serialized_message

    message, format = _parse_off_chain_message(serialized_message)

    node = keychain.derive(signer_path)

    address = base58.encode(seed.remove_ed25519_prefix(node.public_key()))

    await confirm_signverify(
        "SOL", message.decode("ascii" if format == 0 else "utf-8"), address, False
    )

    signature = ed25519.sign(node.private_key(), serialized_message)

    return SolanaOffChainMessageSignature(signature=signature)


def _parse_off_chain_message(serialized_message: bytes) -> tuple[bytes, int]:
    from trezor.utils import BufferReader

    SIGNING_DOMAIN_SPECIFIER = b"\xffsolana offchain"

    serialized_message_b = BufferReader(serialized_message)

    signing_domain_specifier = serialized_message_b.read(16)
    if signing_domain_specifier != SIGNING_DOMAIN_SPECIFIER:
        raise ValueError("Invalid message")

    version = serialized_message_b.get()
    if version != 0:
        raise ValueError("Invalid message")

    format = serialized_message_b.get()
    if format > FORMAT_UTF8:
        raise ValueError("Invalid message")

    length = int.from_bytes(serialized_message_b.read(2), "little")
    if serialized_message_b.remaining_count() != length:
        raise ValueError("Invalid message")

    message = serialized_message_b.read(length)

    if format == FORMAT_ASCII and not _is_ascii(message):
        raise ValueError("Invalid message")
    elif format == FORMAT_UTF8 and not _is_utf8(message):
        raise ValueError("Invalid message")

    return message, format


def _is_utf8(data: bytes) -> bool:
    """Adapted from: https://www.cl.cam.ac.uk/~mgk25/ucs/utf8_check.c"""
    length = len(data)
    i = 0
    while i < length:
        if data[i] < 0x80:
            # 0xxxxxxx
            i += 1
        elif (data[i] & 0xE0) == 0xC0:
            # 110XXXXx 10xxxxxx
            if (
                i + 1 >= length
                or (data[i + 1] & 0xC0) != 0x80
                or (data[i] & 0xFE) == 0xC0
            ):  # overlong?
                return False
            else:
                i += 2
        elif (data[i] & 0xF0) == 0xE0:
            # 1110XXXX 10Xxxxxx 10xxxxxx
            if (
                i + 2 >= length
                or (data[i + 1] & 0xC0) != 0x80
                or (data[i + 2] & 0xC0) != 0x80
                or (data[i] == 0xE0 and (data[i + 1] & 0xE0) == 0x80)
                or (data[i] == 0xED and (data[i + 1] & 0xE0) == 0xA0)
                or (
                    data[i] == 0xEF
                    and data[i + 1] == 0xBF
                    and (data[i + 2] & 0xFE) == 0xBE
                )
            ):  # U+FFFE or U+FFFF?
                return False
            else:
                i += 3
        elif (data[i] & 0xF8) == 0xF0:
            # 11110XXX 10XXxxxx 10xxxxxx 10xxxxxx
            if (
                i + 3 >= length
                or (data[i + 1] & 0xC0) != 0x80
                or (data[i + 2] & 0xC0) != 0x80
                or (data[i + 3] & 0xC0) != 0x80
                or (data[i] == 0xF0 and (data[i + 1] & 0xF0) == 0x80)
                or (data[i] == 0xF4 and data[i + 1] > 0x8F)
                or data[i] > 0xF4
            ):
                return False
            else:
                i += 4
        else:
            return False

    return True

def _is_ascii(data: bytes) -> bool:
    for byte in data:
        if byte < 0x20 or byte > 0x7e:
            return False;

    return True
