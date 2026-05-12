#!/usr/bin/env python3

import datetime
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.x25519 import (
    X25519PrivateKey,
    X25519PublicKey,
)
from cryptography.x509.oid import NameOID

HERE = Path(__file__).parent
CERT_STORE_PATH = HERE / "cert_store.der"
CERT_STORE_VERSION = b"\x01"


def issue_cert(
    subject: x509.Name,
    public_key: ec.EllipticCurvePublicKey | X25519PublicKey,
    issuer_cert: x509.Certificate | None,
    issuer_key: ec.EllipticCurvePrivateKey,
    hash_algorithm: hashes.SHA384 | hashes.SHA512,
    serial: int,
    days: int,
    extensions: list[tuple[x509.ExtensionType, bool]],
) -> x509.Certificate:
    now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
    builder = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer_cert.subject if issuer_cert else subject)
        .public_key(public_key)
        .serial_number(serial)
        .not_valid_before(now)
        .not_valid_after(now + datetime.timedelta(days=days))
    )
    for ext, critical in extensions:
        builder = builder.add_extension(ext, critical=critical)
    return builder.sign(issuer_key, hash_algorithm)


def write_key(
    key: ec.EllipticCurvePrivateKey | X25519PrivateKey, filename: str
) -> None:
    (HERE / filename).write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )


def write_cert(cert: x509.Certificate, filename: str) -> None:
    (HERE / filename).write_bytes(cert.public_bytes(serialization.Encoding.PEM))


def build_cert_store(certs: list[bytes]) -> bytes:
    header = CERT_STORE_VERSION + len(certs).to_bytes(1, "big")
    body = b""
    for der in certs:
        header += len(der).to_bytes(2, "big")
        body += der
    return header + body


l0_key = ec.generate_private_key(ec.SECP521R1())
l1_key = ec.generate_private_key(ec.SECP384R1())
l2_key = ec.generate_private_key(ec.SECP384R1())
# This corresponds to `SECRET_TROPIC_PUBKEY_BYTES` from `core/embed/sec/secret_keys/unix/secret_keys.c`
l3_key = X25519PrivateKey.from_private_bytes(
    bytes.fromhex("b042807fe92ff875df45270f6d55aa2adf7cd783be565a17d466eed545bee367")
)

write_key(l0_key, "l0.key")
write_key(l1_key, "l1.key")
write_key(l2_key, "l2.key")
write_key(l3_key, "l3.key")

l0_cert = issue_cert(
    subject=x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, "CZ"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Tropic Square s.r.o."),
            x509.NameAttribute(NameOID.COMMON_NAME, "Tropic Square TEST Root CA v1"),
        ]
    ),
    public_key=l0_key.public_key(),
    issuer_cert=None,
    issuer_key=l0_key,
    hash_algorithm=hashes.SHA512(),
    serial=101,
    days=18262,
    extensions=[
        (x509.SubjectKeyIdentifier.from_public_key(l0_key.public_key()), False),
        (x509.BasicConstraints(ca=True, path_length=None), True),
        (
            x509.KeyUsage(
                key_cert_sign=True,
                crl_sign=True,
                digital_signature=False,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                encipher_only=False,
                decipher_only=False,
            ),
            True,
        ),
    ],
)

l1_cert = issue_cert(
    subject=x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, "CZ"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Tropic Square s.r.o."),
            x509.NameAttribute(NameOID.COMMON_NAME, "TROPIC01 TEST CA v1"),
        ]
    ),
    public_key=l1_key.public_key(),
    issuer_cert=l0_cert,
    issuer_key=l0_key,
    hash_algorithm=hashes.SHA512(),
    serial=1001,
    days=14610,
    extensions=[
        (x509.SubjectKeyIdentifier.from_public_key(l1_key.public_key()), False),
        (x509.BasicConstraints(ca=True, path_length=1), True),
        (
            x509.KeyUsage(
                key_cert_sign=True,
                crl_sign=True,
                digital_signature=False,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                encipher_only=False,
                decipher_only=False,
            ),
            True,
        ),
        (
            x509.AuthorityKeyIdentifier.from_issuer_public_key(l0_key.public_key()),
            False,
        ),
        (
            x509.CRLDistributionPoints(
                [
                    x509.DistributionPoint(
                        full_name=[
                            x509.UniformResourceIdentifier(
                                "http://pki.tropicsquare.com/l1/tsrv1.crl"
                            )
                        ],
                        relative_name=None,
                        reasons=None,
                        crl_issuer=None,
                    )
                ]
            ),
            False,
        ),
    ],
)

l2_cert = issue_cert(
    subject=x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, "CZ"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Tropic Square s.r.o."),
            x509.NameAttribute(NameOID.COMMON_NAME, "TROPIC01-X TEST CA v1"),
        ]
    ),
    public_key=l2_key.public_key(),
    issuer_cert=l1_cert,
    issuer_key=l1_key,
    hash_algorithm=hashes.SHA384(),
    serial=10001,
    days=12784,
    extensions=[
        (x509.SubjectKeyIdentifier.from_public_key(l2_key.public_key()), False),
        (x509.BasicConstraints(ca=True, path_length=0), True),
        (
            x509.KeyUsage(
                key_cert_sign=True,
                crl_sign=True,
                digital_signature=False,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                encipher_only=False,
                decipher_only=False,
            ),
            True,
        ),
        (
            x509.AuthorityKeyIdentifier.from_issuer_public_key(l1_key.public_key()),
            False,
        ),
        (
            x509.CRLDistributionPoints(
                [
                    x509.DistributionPoint(
                        full_name=[
                            x509.UniformResourceIdentifier(
                                "http://pki.tropicsquare.com/l2/t01v1.crl"
                            )
                        ],
                        relative_name=None,
                        reasons=None,
                        crl_issuer=None,
                    )
                ]
            ),
            False,
        ),
    ],
)

l3_cert = issue_cert(
    subject=x509.Name(
        [
            x509.NameAttribute(NameOID.COMMON_NAME, '"TROPIC01 eSE TEST CA v1"'),
        ]
    ),
    public_key=l3_key.public_key(),
    issuer_cert=l2_cert,
    issuer_key=l2_key,
    hash_algorithm=hashes.SHA384(),
    serial=0x02F0000508341904090C0700000305A5,
    days=7305,
    extensions=[
        (x509.BasicConstraints(ca=False, path_length=None), True),
        (
            x509.KeyUsage(
                key_agreement=True,
                digital_signature=False,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            True,
        ),
        (
            x509.AuthorityKeyIdentifier.from_issuer_public_key(l2_key.public_key()),
            False,
        ),
        (
            x509.CRLDistributionPoints(
                [
                    x509.DistributionPoint(
                        full_name=[
                            x509.UniformResourceIdentifier(
                                "http://pki.tropicsquare.com/l3/t01-Tv1.crl"
                            )
                        ],
                        relative_name=None,
                        reasons=None,
                        crl_issuer=None,
                    )
                ]
            ),
            True,
        ),
    ],
)

write_cert(l0_cert, "l0.pem")
write_cert(l1_cert, "l1.pem")
write_cert(l2_cert, "l2.pem")
write_cert(l3_cert, "l3.pem")

CERT_STORE_PATH.write_bytes(
    build_cert_store(
        [
            l3_cert.public_bytes(serialization.Encoding.DER),
            l2_cert.public_bytes(serialization.Encoding.DER),
            l1_cert.public_bytes(serialization.Encoding.DER),
            l0_cert.public_bytes(serialization.Encoding.DER),
        ]
    )
)
