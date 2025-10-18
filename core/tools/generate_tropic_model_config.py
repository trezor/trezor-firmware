#!/usr/bin/env python3

import hashlib
import os
from pathlib import Path

import click
import yaml
from cryptography import x509
from cryptography.hazmat.primitives import serialization

HERE = Path(__file__).parent
ROOT = HERE.parent.parent.resolve()
CONFIG_DIR = ROOT / "tests" / "tropic_model"
DEST_PATH = CONFIG_DIR / "config.yml"

# private key used by the Tropic model to sign
TROPIC_KEY = CONFIG_DIR / "tropic_key.pem"

# certificate of the Tropic model - signed by the root authority
TROPIC_CERT = CONFIG_DIR / "tropic_cert.pem"

# certificate of the root authority
ROOT_CERT = CONFIG_DIR / "root_cert.pem"

VENDOR_CONFIG_DIR = ROOT / "vendor" / "ts-tvl" / "model_configs" / "example_config"
EXTRA_FILES = [
    VENDOR_CONFIG_DIR / "tropic01_ese_certificate_1.pem",
    VENDOR_CONFIG_DIR / "tropic01_ese_private_key_1.pem",
    VENDOR_CONFIG_DIR / "tropic01_ese_public_key_1.pem",
]


@click.command()
@click.option("--check", is_flag=True)
def generate_config(check: bool) -> None:
    tropic_key = serialization.load_pem_private_key(
        TROPIC_KEY.read_bytes(), password=None
    )

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

    tropic_cert = x509.load_pem_x509_certificate(TROPIC_CERT.read_bytes())
    tropic_cert_der_bytes = tropic_cert.public_bytes(serialization.Encoding.DER)

    root_cert = x509.load_pem_x509_certificate(ROOT_CERT.read_bytes())
    root_cert_der_bytes = root_cert.public_bytes(serialization.Encoding.DER)

    # certificate chain with the length prefix
    all_cert_bytes = (
        (len(tropic_cert_der_bytes) + len(root_cert_der_bytes)).to_bytes(2, "big")
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
        "debug_random_value": b"\x00\xc0\xff\xee",
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

    config = yaml.dump(config_dict)

    if check:
        if not DEST_PATH.exists():
            print(f"{DEST_PATH} missing")
            raise click.ClickException("Config file is missing")
        elif config != DEST_PATH.read_text():
            print(f"{DEST_PATH} is out of date")
            raise click.ClickException("Config file is out of date")
        for extra_file in EXTRA_FILES:
            extra_file_dest = CONFIG_DIR / extra_file.name
            if not extra_file_dest.exists():
                print(f"{extra_file_dest} missing")
                raise click.ClickException("Extra config file missing")
            elif extra_file.read_bytes() != extra_file_dest.read_bytes():
                print(f"{extra_file_dest} is out of date")
                raise click.ClickException("Extra config file is out of date")
    else:
        tropic_key_stat = TROPIC_KEY.stat()
        tropic_cert_stat = TROPIC_CERT.stat()
        root_cert_stat = ROOT_CERT.stat()
        DEST_PATH.write_text(config)
        os.utime(
            DEST_PATH,
            ns=(
                max(
                    tropic_key_stat.st_atime_ns,
                    tropic_cert_stat.st_atime_ns,
                    root_cert_stat.st_atime_ns,
                ),
                max(
                    tropic_key_stat.st_mtime_ns,
                    tropic_cert_stat.st_mtime_ns,
                    root_cert_stat.st_mtime_ns,
                ),
            ),
        )

        for extra_file in EXTRA_FILES:
            extra_file_dest = CONFIG_DIR / extra_file.name
            extra_file_dest.write_bytes(extra_file.read_bytes())
            extra_file_stat = extra_file.stat()
            os.utime(
                extra_file_dest,
                ns=(extra_file_stat.st_atime_ns, extra_file_stat.st_mtime_ns),
            )


if __name__ == "__main__":
    generate_config()
