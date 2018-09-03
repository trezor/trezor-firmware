from . import messages as proto
from .tools import expect


@expect(proto.Entropy, field="entropy")
def get_entropy(client, size):
    return client.call(proto.GetEntropy(size=size))


@expect(proto.SignedIdentity)
def sign_identity(
    client, identity, challenge_hidden, challenge_visual, ecdsa_curve_name=None
):
    return client.call(
        proto.SignIdentity(
            identity=identity,
            challenge_hidden=challenge_hidden,
            challenge_visual=challenge_visual,
            ecdsa_curve_name=ecdsa_curve_name,
        )
    )


@expect(proto.ECDHSessionKey)
def get_ecdh_session_key(client, identity, peer_public_key, ecdsa_curve_name=None):
    return client.call(
        proto.GetECDHSessionKey(
            identity=identity,
            peer_public_key=peer_public_key,
            ecdsa_curve_name=ecdsa_curve_name,
        )
    )


@expect(proto.CipheredKeyValue, field="value")
def encrypt_keyvalue(
    client, n, key, value, ask_on_encrypt=True, ask_on_decrypt=True, iv=b""
):
    return client.call(
        proto.CipherKeyValue(
            address_n=n,
            key=key,
            value=value,
            encrypt=True,
            ask_on_encrypt=ask_on_encrypt,
            ask_on_decrypt=ask_on_decrypt,
            iv=iv,
        )
    )


@expect(proto.CipheredKeyValue, field="value")
def decrypt_keyvalue(
    client, n, key, value, ask_on_encrypt=True, ask_on_decrypt=True, iv=b""
):
    return client.call(
        proto.CipherKeyValue(
            address_n=n,
            key=key,
            value=value,
            encrypt=False,
            ask_on_encrypt=ask_on_encrypt,
            ask_on_decrypt=ask_on_decrypt,
            iv=iv,
        )
    )
