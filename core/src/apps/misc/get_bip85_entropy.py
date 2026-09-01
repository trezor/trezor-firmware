from micropython import const
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import Bip85Entropy, GetBip85Entropy

    from apps.common.paths import Bip32Path

# This module implements BIP-85 deterministic entropy derivation from a BIP-32
# keychain, see https://github.com/bitcoin/bips/blob/master/bip-0085.mediawiki.
#
# The derivation path has the form m/83696968'/{app}'/{params...}'/{index}'. The
# private key of the derived node is fed into HMAC-SHA512 with the key
# "bip-entropy-from-k", which yields 64 bytes of entropy. Each application defines
# how the entropy is truncated and formatted.

_BIP85_PURPOSE = const(83696968 | 0x8000_0000)
_MAX_PATH_LENGTH = const(8)
_HMAC_KEY = b"bip-entropy-from-k"

# BIP-85 application numbers
_APP_WIF = const(2)
_APP_XPRV = const(32)
_APP_BIP39 = const(39)
_APP_HEX = const(128169)
_APP_PWD_BASE64 = const(707764)
_APP_PWD_BASE85 = const(707785)

_BIP39_ENGLISH = const(0)
_BIP39_WORD_COUNTS = (12, 15, 18, 21, 24)

# BIP-32 serialization prefix of a mainnet extended private key (xprv)
_XPRV_VERSION = b"\x04\x88\xad\xe4"
# WIF prefix of a mainnet private key and the compressed-public-key suffix
_WIF_PREFIX = b"\x80"
_WIF_COMPRESSED_SUFFIX = b"\x01"

_BASE64_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
# RFC 1924 alphabet, as used by Python's base64.b85encode
_BASE85_ALPHABET = (
    "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "abcdefghijklmnopqrstuvwxyz!#$%&()*+-;<=>?@^_`{|}~"
)


async def get_bip85_entropy(msg: GetBip85Entropy) -> Bip85Entropy:
    from trezor import TR
    from trezor.enums import ButtonRequestType
    from trezor.messages import Bip85Entropy
    from trezor.ui.layouts import confirm_action, confirm_properties

    from apps.common.keychain import get_keychain
    from apps.common.paths import AlwaysMatchingSchema, address_n_to_str

    address_n = msg.address_n  # local_cache_attribute
    on_device_only = bool(msg.on_device_only)
    show_display = bool(msg.show_display) or on_device_only

    app_name = _validate_path(address_n)

    keychain = await get_keychain("secp256k1", [AlwaysMatchingSchema])
    with keychain:
        await confirm_properties(
            "get_bip85_entropy",
            TR.bip85__title,
            (
                (TR.bip85__application, app_name, False),
                (
                    TR.address_details__derivation_path,
                    address_n_to_str(address_n),
                    True,
                ),
            ),
            br_code=ButtonRequestType.ProtectCall,
        )

        if not on_device_only:
            await confirm_action(
                "get_bip85_entropy_export",
                TR.bip85__title,
                TR.bip85__send_to_host,
                TR.words__know_what_your_doing,
                br_code=ButtonRequestType.ProtectCall,
                prompt_screen=True,
            )

        node = keychain.derive(address_n)
        entropy = _entropy_from_key(node.private_key())
        node.__del__()

    entropy, secret = _apply_application(address_n, entropy)

    if show_display:
        await _show_secret(address_n, app_name, entropy, secret)

    if on_device_only:
        return Bip85Entropy()

    return Bip85Entropy(entropy=entropy, secret=secret)


def _entropy_from_key(private_key: bytes) -> bytes:
    """Derive the 64 bytes of BIP-85 entropy from the private key of a derived node."""
    from trezor.crypto import hmac

    return hmac(hmac.SHA512, _HMAC_KEY, private_key).digest()


def _validate_path(address_n: Bip32Path) -> str:
    """Check that the path is a valid BIP-85 path and return a human-readable
    description of the application it selects."""
    from trezor import TR
    from trezor.wire import DataError

    from apps.common.paths import path_is_hardened, unharden

    if (
        len(address_n) < 2
        or len(address_n) > _MAX_PATH_LENGTH
        or address_n[0] != _BIP85_PURPOSE
    ):
        raise DataError("Invalid BIP-85 derivation path")

    if not path_is_hardened(address_n):
        raise DataError("BIP-85 path components must be hardened")

    app = unharden(address_n[1])

    if app == _APP_BIP39:
        if len(address_n) != 5:
            raise DataError("Invalid BIP-85 derivation path")
        if unharden(address_n[2]) != _BIP39_ENGLISH:
            raise DataError("Only the English BIP-39 wordlist is supported")
        words = unharden(address_n[3])
        if words not in _BIP39_WORD_COUNTS:
            raise DataError("Invalid number of BIP-39 words")
        return TR.bip85__app_bip39_template.format(words)

    if app == _APP_WIF:
        if len(address_n) != 3:
            raise DataError("Invalid BIP-85 derivation path")
        return TR.bip85__app_wif

    if app == _APP_XPRV:
        if len(address_n) != 3:
            raise DataError("Invalid BIP-85 derivation path")
        return TR.bip85__app_xprv

    if app == _APP_HEX:
        if len(address_n) != 4:
            raise DataError("Invalid BIP-85 derivation path")
        num_bytes = unharden(address_n[2])
        if not 16 <= num_bytes <= 64:
            raise DataError("Invalid number of bytes")
        return TR.bip85__app_hex_template.format(num_bytes)

    if app == _APP_PWD_BASE64:
        if len(address_n) != 4:
            raise DataError("Invalid BIP-85 derivation path")
        pwd_len = unharden(address_n[2])
        if not 20 <= pwd_len <= 86:
            raise DataError("Invalid password length")
        return TR.bip85__app_pwd_base64_template.format(pwd_len)

    if app == _APP_PWD_BASE85:
        if len(address_n) != 4:
            raise DataError("Invalid BIP-85 derivation path")
        pwd_len = unharden(address_n[2])
        if not 10 <= pwd_len <= 80:
            raise DataError("Invalid password length")
        return TR.bip85__app_pwd_base85_template.format(pwd_len)

    # Unknown application: the raw 64 bytes of entropy are returned.
    return TR.bip85__app_unknown_template.format(app)


def _apply_application(
    address_n: Bip32Path, entropy: bytes
) -> tuple[bytes, str | None]:
    """Truncate and format the entropy according to the BIP-85 application.

    Returns the (possibly truncated) entropy and its human-readable form, if the
    application defines one.
    """
    from apps.common.paths import unharden

    app = unharden(address_n[1])

    if app == _APP_BIP39:
        from trezor.crypto import bip39

        words = unharden(address_n[3])
        entropy = entropy[: words * 4 // 3]
        return entropy, bip39.from_data(entropy)

    if app == _APP_WIF:
        from trezor.crypto import base58

        key = entropy[:32]
        return key, base58.encode_check(_WIF_PREFIX + key + _WIF_COMPRESSED_SUFFIX)

    if app == _APP_XPRV:
        from trezor.crypto import base58

        # BIP-85 uses the first 32 bytes as the chain code and the last 32 bytes as
        # the private key. Depth, parent fingerprint and child number are zero.
        data = _XPRV_VERSION + bytes(9) + entropy[:32] + b"\x00" + entropy[32:]
        return entropy, base58.encode_check(data)

    if app == _APP_HEX:
        return entropy[: unharden(address_n[2])], None

    if app == _APP_PWD_BASE64:
        return entropy, _base64_encode(entropy)[: unharden(address_n[2])]

    if app == _APP_PWD_BASE85:
        return entropy, _base85_encode(entropy)[: unharden(address_n[2])]

    return entropy, None


async def _show_secret(
    address_n: Bip32Path, app_name: str, entropy: bytes, secret: str | None
) -> None:
    from trezor import TR
    from trezor.enums import ButtonRequestType

    from apps.common.paths import unharden

    app = unharden(address_n[1])

    if app == _APP_BIP39:
        from trezor.ui.layouts.reset import show_share_words

        assert secret is not None
        await show_share_words(secret.split(" "))
    elif secret is not None:
        from trezor.ui.layouts import confirm_value

        await confirm_value(
            TR.bip85__derived_secret,
            secret,
            app_name,
            "get_bip85_entropy_secret",
            br_code=ButtonRequestType.ProtectCall,
            is_data=True,
            chunkify=app in (_APP_WIF, _APP_XPRV),
        )
    else:
        from trezor.ui.layouts import confirm_blob

        await confirm_blob(
            "get_bip85_entropy_secret",
            TR.bip85__derived_secret,
            entropy,
            app_name,
            br_code=ButtonRequestType.ProtectCall,
        )


def _base64_encode(data: bytes) -> str:
    """Standard base64 encoding with padding (RFC 4648)."""
    result = []
    for i in range(0, len(data), 3):
        chunk = data[i : i + 3]
        pad = 3 - len(chunk)
        n = int.from_bytes(chunk + bytes(pad), "big")
        for j in range(4 - pad):
            result.append(_BASE64_ALPHABET[(n >> (18 - 6 * j)) & 0x3F])
        result.append("=" * pad)
    return "".join(result)


def _base85_encode(data: bytes) -> str:
    """Base85 encoding with the RFC 1924 alphabet, compatible with Python's
    base64.b85encode. The input length must be a multiple of 4."""
    assert len(data) % 4 == 0
    result = []
    for i in range(0, len(data), 4):
        n = int.from_bytes(data[i : i + 4], "big")
        chars = [""] * 5
        for j in range(4, -1, -1):
            n, r = divmod(n, 85)
            chars[j] = _BASE85_ALPHABET[r]
        result.extend(chars)
    return "".join(result)
