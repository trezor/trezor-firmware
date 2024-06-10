import sys
from pathlib import Path

from pyasn1.codec.der.encoder import encode
from pyasn1.codec.der.decoder import decode
from pyasn1.type.univ import BitString
from pyasn1_modules import rfc2459
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec


def load_certificate(data: bytes):
    return decode(data, asn1Spec=rfc2459.Certificate())[0]


def save_certificate(certificate) -> bytes:
    return encode(certificate)


def calculate_ecdsa_public_key():
    privkey_bytes = b"\x01" + b"\x00" * 31
    private_key = ec.derive_private_key(
        int.from_bytes(privkey_bytes, "big"), ec.SECP256R1()
    )

    return private_key.public_key()


def replace_public_key(certificate, public_key):
    public_key_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint,
    )
    certificate["tbsCertificate"]["subjectPublicKeyInfo"]["subjectPublicKey"] = (
        BitString(hexValue=public_key_bytes.hex())
    )


def main():
    in_cert = Path(sys.argv[1])
    certificate = load_certificate(in_cert.read_bytes())
    public_key = calculate_ecdsa_public_key()
    replace_public_key(certificate, public_key)
    updated_cert = save_certificate(certificate)
    out_cert = Path(sys.argv[2])
    out_cert.write_bytes(updated_cert)


if __name__ == "__main__":
    main()
