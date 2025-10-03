#!/usr/bin/env python3

from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from cryptography import x509
import hashlib

import click

@click.command()
@click.option("-k", "--tropic-key", type=click.File("rb"), required=True)
@click.option("-c", "--tropic-cert", type=click.File("rb"), required=True)
@click.option("-r", "--root-cert", type=click.File("rb"), required=True)
def generate_config(tropic_key, tropic_cert, root_cert):
    priv = serialization.load_pem_private_key(tropic_key.read(), password=None)

    tropic_s = priv.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption()
    )

    tropic_prefix = hashlib.sha512(tropic_s).digest()[:32]

    tropic_a = priv.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw
    )

    tropic_cert = x509.load_pem_x509_certificate(tropic_cert.read())
    tropic_cert_der_bytes = tropic_cert.public_bytes(serialization.Encoding.DER)

    root_cert = x509.load_pem_x509_certificate(root_cert.read())
    root_cert_der_bytes = root_cert.public_bytes(serialization.Encoding.DER)

    SLOT_LEN = 444

    # all the certificates together, with the length prefix
    all_cert_bytes = (len(tropic_cert_der_bytes) + len(root_cert_der_bytes)).to_bytes(2) + tropic_cert_der_bytes + root_cert_der_bytes

    # make sure they fit in 3 slots, which is what we have available
    assert len(all_cert_bytes) < SLOT_LEN * 3

    # split the data in 3 slots
    slot_1_bytes = all_cert_bytes[:SLOT_LEN]
    slot_2_bytes = all_cert_bytes[SLOT_LEN:SLOT_LEN * 2]
    slot_3_bytes = all_cert_bytes[SLOT_LEN * 2:SLOT_LEN * 3]

    user_data = {}
    for k, data in [(3, slot_1_bytes), (4, slot_2_bytes), (5, slot_3_bytes)]:
        if len(data) != 0:
            if len(data) < SLOT_LEN: # pad last slot
                data += b'\x00' * (SLOT_LEN - len(data))
            user_data[k] = {"value": data}

    config_dict = {
            "s_t_priv": "tropic01_ese_private_key_1.pem",
            "s_t_pub": "tropic01_ese_public_key_1.pem",
            "x509_certificate": "tropic01_ese_certificate_1.pem",
            "r_user_data": user_data, # certificates
            "r_ecc_keys": { # signing key at index 0
            0: {"a": tropic_a,
                "s": tropic_s,
                "origin": 2, # imported key
                "prefix": tropic_prefix}
            }
            }

    import yaml
    print(yaml.dump(config_dict))


if __name__ == "__main__":
    generate_config()

