from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import ECDHSessionKey, GetECDHSessionKey

# This module implements the SLIP-0017 Elliptic Curve Diffie-Hellman algorithm, using a
# deterministic hierarchy, see https://github.com/satoshilabs/slips/blob/master/slip-0017.md.


async def get_ecdh_session_key(msg: GetECDHSessionKey) -> ECDHSessionKey:
    from trezor.messages import ECDHSessionKey
    from trezor.ui.layouts import confirm_address
    from trezor.wire import DataError

    from apps.common.keychain import get_keychain
    from apps.common.paths import AlwaysMatchingSchema

    from .sign_identity import (
        get_identity_path,
        serialize_identity,
        serialize_identity_without_proto,
    )

    msg_identity = msg.identity  # local_cache_attribute
    peer_public_key = msg.peer_public_key  # local_cache_attribute
    curve_name = msg.ecdsa_curve_name or "secp256k1"

    keychain = await get_keychain(curve_name, [AlwaysMatchingSchema])
    identity = serialize_identity(msg_identity)

    # require_confirm_ecdh_session_key
    proto = msg_identity.proto.upper() if msg_identity.proto else "identity"
    await confirm_address(
        f"Decrypt {proto}",
        serialize_identity_without_proto(msg_identity),
        "",
    )
    # END require_confirm_ecdh_session_key

    address_n = get_identity_path(identity, msg_identity.index or 0, 17)
    node = keychain.derive(address_n)

    # ecdh
    if curve_name == "secp256k1":
        from trezor.crypto.curve import secp256k1

        session_key = secp256k1.multiply(node.private_key(), peer_public_key)
    elif curve_name == "nist256p1":
        from trezor.crypto.curve import nist256p1

        session_key = nist256p1.multiply(node.private_key(), peer_public_key)
    elif curve_name == "curve25519":
        from trezor.crypto.curve import curve25519

        if peer_public_key[0] != 0x40:
            raise DataError("Curve25519 public key should start with 0x40")
        session_key = b"\x04" + curve25519.multiply(
            node.private_key(), peer_public_key[1:]
        )
    else:
        raise DataError("Unsupported curve for ECDH: " + curve_name)
    # END ecdh

    return ECDHSessionKey(session_key=session_key, public_key=node.public_key())
