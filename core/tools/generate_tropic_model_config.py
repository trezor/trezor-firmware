#!/usr/bin/env python3

import hashlib

import click
from cryptography import x509
from cryptography.hazmat.primitives import serialization


@click.command()
@click.option("-k", "--tropic-key", type=click.File("rb"), required=True)
@click.option("-c", "--tropic-cert", type=click.File("rb"), required=True)
@click.option("-r", "--root-cert", type=click.File("rb"), required=True)
def generate_config(tropic_key, tropic_cert, root_cert):
    tropic_key = serialization.load_pem_private_key(tropic_key.read(), password=None)

    tropic_a = tropic_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
    )

    tropic_private_key_bytes = tropic_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )

    # perform clamping
    # https://www.jcraige.com/an-explainer-on-ed25519-clamping
    h = hashlib.sha512(tropic_private_key_bytes).digest()
    tropic_s = bytearray(h[:32])
    tropic_s[0] &= 248
    tropic_s[31] &= 63
    tropic_s[31] |= 64
    tropic_s = bytes(tropic_s)

    tropic_prefix = hashlib.sha512(tropic_s).digest()[:32]

    tropic_cert = x509.load_pem_x509_certificate(tropic_cert.read())
    tropic_cert_der_bytes = tropic_cert.public_bytes(serialization.Encoding.DER)

    root_cert = x509.load_pem_x509_certificate(root_cert.read())
    root_cert_der_bytes = root_cert.public_bytes(serialization.Encoding.DER)

    # certificate chain with the length prefix
    all_cert_bytes = (
        (len(tropic_cert_der_bytes) + len(root_cert_der_bytes)).to_bytes(2)
        + tropic_cert_der_bytes
        + root_cert_der_bytes
    )

    SLOT_LEN = 444

    # make sure they fit in 3 slots, which is what we have available
    assert len(all_cert_bytes) < SLOT_LEN * 3

    # split the data in 3 slots
    slot_1_bytes = all_cert_bytes[:SLOT_LEN]
    slot_2_bytes = all_cert_bytes[SLOT_LEN : SLOT_LEN * 2]
    slot_3_bytes = all_cert_bytes[SLOT_LEN * 2 : SLOT_LEN * 3]

    # save the data starting at slot 3
    # see https://github.com/trezor/trezor-firmware/blob/main/core/embed/sec/tropic/inc/sec/tropic.h#L31
    TROPIC_DEVICE_CERT_FIRST_SLOT = 3
    user_data = {}
    for i, data in enumerate([slot_1_bytes, slot_2_bytes, slot_3_bytes]):
        if len(data) != 0:
            if len(data) < SLOT_LEN:  # pad last slot
                data += b"\x00" * (SLOT_LEN - len(data))
            user_data[TROPIC_DEVICE_CERT_FIRST_SLOT + i] = {"value": data}

    config_dict = {
        "s_t_priv": "tropic01_ese_private_key_1.pem",
        "s_t_pub": "tropic01_ese_public_key_1.pem",
        "x509_certificate": "tropic01_ese_certificate_1.pem",
        "r_user_data": user_data,  # certificate chain
        "r_ecc_keys": {  # signing key at index 0
            0: {
                "a": tropic_a,
                "s": tropic_s,
                "prefix": tropic_prefix,
                "origin": 2,  # imported key
            }
        },
    }

    import yaml

    print(yaml.dump(config_dict))


if __name__ == "__main__":
    generate_config()
