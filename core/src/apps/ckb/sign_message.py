"""Sign a message with CKB private key."""

from typing import TYPE_CHECKING

from apps.common.keychain import with_slip44_keychain

from . import CURVE, PATTERN, SLIP44_ID

if TYPE_CHECKING:
    from trezor.messages import CKBMessageSignature, CKBSignMessage

    from apps.common.keychain import Keychain


@with_slip44_keychain(PATTERN, slip44_id=SLIP44_ID, curve=CURVE)
async def sign_message(msg: CKBSignMessage, keychain: Keychain) -> CKBMessageSignature:
    from trezor.crypto.curve import secp256k1
    from trezor.messages import CKBMessageSignature
    from trezor.ui.layouts import confirm_signverify
    from trezor.wire import DataError

    from apps.common.paths import address_n_to_str, validate_path
    from apps.common.signverify import decode_message

    from .helpers import encode_address, get_lock_script_arg, message_digest

    address_n = msg.address_n
    message = msg.message
    network = msg.network

    await validate_path(keychain, address_n)

    if network not in ("Mainnet", "Testnet"):
        raise DataError("Invalid CKB network")

    node = keychain.derive(address_n)
    public_key = node.public_key()
    arg = get_lock_script_arg(public_key)
    address = encode_address(arg, network)

    await confirm_signverify(
        decode_message(message),
        address,
        verify=False,
        account="CKB",
        path=address_n_to_str(address_n),
        chunkify=bool(msg.chunkify),
    )

    seckey = node.private_key()
    digest = message_digest(message)
    raw_sig = secp256k1.sign(seckey, digest)

    # CKB native format: [R(32) | S(32) | recovery_id(1)]
    # secp256k1.sign() default returns recovery byte = 31 + recid (compressed)
    recid = raw_sig[0] - 31
    signature = raw_sig[1:65] + bytes([recid])

    return CKBMessageSignature(address=address, signature=signature)
