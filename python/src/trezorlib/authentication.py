from __future__ import annotations

import io
import logging
import secrets
import typing as t

from cryptography import exceptions, x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, utils

from . import device
from .client import TrezorClient

LOG = logging.getLogger(__name__)


def _pk_p256(pubkey_hex: str) -> ec.EllipticCurvePublicKey:
    return ec.EllipticCurvePublicKey.from_encoded_point(
        ec.SECP256R1(), bytes.fromhex(pubkey_hex)
    )


CHALLENGE_HEADER = b"AuthenticateDevice:"


class RootCertificate(t.NamedTuple):
    name: str
    device: str
    devel: bool
    pubkey: ec.EllipticCurvePublicKey


ROOT_PUBLIC_KEYS = [
    RootCertificate(
        "Trezor Company",
        "Trezor Safe 3",
        False,
        _pk_p256(
            "04ca97480ac0d7b1e6efafe518cd433cec2bf8ab9822d76eafd34363b55d63e60"
            "380bff20acc75cde03cffcb50ab6f8ce70c878e37ebc58ff7cca0a83b16b15fa5"
        ),
    ),
    RootCertificate(
        "Trezor Company",
        "Trezor Safe 5",
        False,
        _pk_p256(
            "041854b27fb1d9f65abb66828e78c9dc0ca301e66081ab0c6a4d104f9df1cd0ad"
            "5a7c75f77a8c092f55cf825d2abaf734f934c9394d5e75f75a5a06a5ee9be93ae"
        ),
    ),
    RootCertificate(
        "TESTING ENVIRONMENT. DO NOT USE THIS DEVICE",
        "Trezor Safe 3",
        True,
        _pk_p256(
            "047f77368dea2d4d61e989f474a56723c3212dacf8a808d8795595ef38441427c"
            "4389bc454f02089d7f08b873005e4c28d432468997871c0bf286fd3861e21e96a"
        ),
    ),
    RootCertificate(
        "TESTING ENVIRONMENT. DO NOT USE THIS DEVICE",
        "Trezor Safe 5",
        True,
        _pk_p256(
            "04e48b69cd7962068d3cca3bcc6b1747ef496c1e28b5529e34ad7295215ea161d"
            "be8fb08ae0479568f9d2cb07630cb3e52f4af0692102da5873559e45e9fa72959"
        ),
    ),
    RootCertificate(
        "TESTING ENVIRONMENT. DO NOT USE THIS DEVICE",
        "Trezor T3W1",
        True,
        _pk_p256(
            "04521192e173a9da4e3023f747d836563725372681eba3079c56ff11b2fc137ab"
            "189eb4155f371127651b5594f8c332fc1e9c0f3b80d4212822668b63189706578"
        ),
    ),
]


class DeviceNotAuthentic(Exception):
    pass


class Certificate:
    def __init__(self, cert_bytes: bytes) -> None:
        self.cert_bytes = cert_bytes
        self.cert = x509.load_der_x509_certificate(cert_bytes)

    def __str__(self) -> str:
        return self.cert.subject.rfc4514_string()

    def public_key_bytes(self) -> bytes:
        return self.cert.public_key().public_bytes(
            serialization.Encoding.X962,
            serialization.PublicFormat.UncompressedPoint,
        )

    def verify(self, signature: bytes, message: bytes) -> None:
        cert_pubkey = self.cert.public_key()
        assert isinstance(cert_pubkey, ec.EllipticCurvePublicKey)
        cert_pubkey.verify(
            self.fix_signature(signature),
            message,
            ec.ECDSA(hashes.SHA256()),
        )

    def verify_by(self, pubkey: ec.EllipticCurvePublicKey) -> None:
        algo_params = self.cert.signature_algorithm_parameters
        assert isinstance(algo_params, ec.ECDSA)
        pubkey.verify(
            self.fix_signature(self.cert.signature),
            self.cert.tbs_certificate_bytes,
            algo_params,
        )

    def _check_ca_extensions(self) -> bool:
        """Check that this certificate is a valid Trezor CA.

        KeyUsage must be present and allow certificate signing.
        BasicConstraints must be present, have the cA flag and a pathLenConstraint.

        Any unrecognized non-critical extension is allowed. Any unrecognized critical
        extension is disallowed.
        """
        missing_extension_classes = {x509.KeyUsage, x509.BasicConstraints}
        passed = True

        for ext in self.cert.extensions:
            missing_extension_classes.discard(type(ext.value))

            if isinstance(ext.value, x509.KeyUsage):
                if not ext.value.key_cert_sign:
                    LOG.error(
                        "Not a valid CA certificate: %s (keyCertSign not set)", self
                    )
                    passed = False

            elif isinstance(ext.value, x509.BasicConstraints):
                if not ext.value.ca:
                    LOG.error("Not a valid CA certificate: %s (cA not set)", self)
                    passed = False
                if ext.value.path_length is None:
                    LOG.error(
                        "Not a valid CA certificate: %s (pathLenConstraint missing)",
                        self,
                    )
                    passed = False

            elif ext.critical:
                LOG.error(
                    "Unknown critical extension %s in CA certificate: %s",
                    self,
                    type(ext.value).__name__,
                )
                passed = False

        for ext in missing_extension_classes:
            LOG.error("Missing extension %s in CA certificate: %s", ext.__name__, self)
            passed = False

        return passed

    def is_issued_by(self, issuer: "Certificate", path_len: int) -> bool:
        """Check if this certificate was issued by an issuer.

        Returns True if:
         * our `issuer` is the same as issuer's `subject`,
         * the issuer is a valid CA, that is:
           - has the cA flag set
           - has a valid pathLenConstraint
           - pathLenConstraint does not exceed the current path length.
         * the issuer's public key signs this certificate.
        """
        if issuer.cert.subject != self.cert.issuer:
            LOG.error("Certificate %s is not issued by %s.", self, issuer)
            return False

        if not issuer._check_ca_extensions():
            return False

        basic_constraints = issuer.cert.extensions.get_extension_for_class(
            x509.BasicConstraints
        ).value
        assert basic_constraints.path_length is not None  # check_ca_extensions
        if basic_constraints.path_length < path_len:
            LOG.error(
                "Issuer %s was not permitted to issue certificate %s", issuer, self
            )
            return False

        try:
            pubkey = issuer.cert.public_key()
            assert isinstance(pubkey, ec.EllipticCurvePublicKey)
            self.verify_by(pubkey)
            return True
        except exceptions.InvalidSignature:
            LOG.error("Issuer %s did not sign certificate %s.", issuer, self)

        return False

    @staticmethod
    def _decode_signature_permissive(sig_bytes: bytes) -> tuple[int, int]:
        if len(sig_bytes) > 73:
            raise ValueError("Unsupported DER signature: too long.")

        reader = io.BytesIO(sig_bytes)
        tag = reader.read(1)
        if tag != b"\x30":
            raise ValueError("Invalid DER signature: not a sequence.")
        length = reader.read(1)[0]
        if length != len(sig_bytes) - 2:
            raise ValueError("Invalid DER signature: invalid length.")

        def read_int() -> int:
            tag = reader.read(1)
            if tag != b"\x02":
                raise ValueError("Invalid DER signature: not an integer.")
            length = reader.read(1)[0]
            if length > 33:
                raise ValueError("Invalid DER signature: integer too long.")
            return int.from_bytes(reader.read(length), "big")

        r = read_int()
        s = read_int()
        if reader.tell() != len(sig_bytes):
            raise ValueError("Invalid DER signature: trailing data.")
        return r, s

    @staticmethod
    def fix_signature(sig_bytes: bytes) -> bytes:
        r, s = Certificate._decode_signature_permissive(sig_bytes)
        reencoded = utils.encode_dss_signature(r, s)
        if reencoded != sig_bytes:
            LOG.info(
                "Re-encoding malformed signature: %s -> %s",
                sig_bytes.hex(),
                reencoded.hex(),
            )
        return reencoded


def verify_authentication_response(
    challenge: bytes,
    signature: bytes,
    cert_chain: t.Iterable[bytes],
    *,
    whitelist: t.Collection[bytes] | None,
    allow_development_devices: bool = False,
    root_pubkey: bytes | ec.EllipticCurvePublicKey | None = None,
) -> None:
    """Evaluate the response to an AuthenticateDevice call.

    Performs all steps and logs their results via the logging facility. (The log can be
    accessed via the `LOG` object in this module.)

    When done, raises DeviceNotAuthentic if the device is not authentic.

    The optional argument `root_pubkey` allows you to specify a root public key either
    as an `ec.EllipticCurvePublicKey` object or as a byte-string representing P-256
    public key.
    """
    if isinstance(root_pubkey, (bytes, bytearray, memoryview)):
        root_pubkey = ec.EllipticCurvePublicKey.from_encoded_point(
            ec.SECP256R1(), root_pubkey
        )

    challenge_bytes = (
        len(CHALLENGE_HEADER).to_bytes(1, "big")
        + CHALLENGE_HEADER
        + len(challenge).to_bytes(1, "big")
        + challenge
    )

    cert_chain_iter = iter(cert_chain)

    failed = False

    try:
        cert = Certificate(next(cert_chain_iter))
    except Exception:
        LOG.error("Failed to parse device certificate.")
        raise DeviceNotAuthentic

    try:
        cert.verify(signature, challenge_bytes)
    except exceptions.InvalidSignature:
        LOG.error("Challenge verification failed.")
        failed = True
    else:
        LOG.debug("Challenge verified successfully.")

    cert_label = "Device certificate"
    for i, issuer_bytes in enumerate(cert_chain_iter, 1):
        try:
            ca_cert = Certificate(issuer_bytes)
        except Exception:
            LOG.error(f"Failed to parse CA certificate #{i}.")
            failed = True
            continue

        if whitelist is None:
            LOG.warning("Skipping public key whitelist check.")
        else:
            if ca_cert.public_key_bytes() not in whitelist:
                LOG.error(f"CA certificate #{i} not in whitelist: %s", ca_cert)
                failed = True

        if not cert.is_issued_by(ca_cert, i - 1):
            failed = True
        else:
            LOG.debug(f"{cert_label} verified successfully: %s", cert)

        cert = ca_cert
        cert_label = f"CA #{i} certificate"

    if root_pubkey is not None:
        try:
            cert.verify_by(root_pubkey)
        except Exception:
            LOG.error(f"{cert_label} was not issued by the specified root.")
            failed = True
        else:
            LOG.info(f"{cert_label} was issued by the specified root.")

    else:
        for root in ROOT_PUBLIC_KEYS:
            try:
                cert.verify_by(root.pubkey)
            except Exception:
                continue
            else:
                LOG.debug(f"{cert_label} verified successfully: %s", cert)

            if root.devel:
                if not allow_development_devices:
                    level = logging.ERROR
                    failed = True
                else:
                    level = logging.WARNING
            else:
                level = logging.DEBUG
            LOG.log(
                level,
                "Successfully verified a %s manufactured by %s.",
                root.device,
                root.name,
            )
            break
        else:
            LOG.error(f"{cert_label} was issued by an unknown root.")
            failed = True

    if failed:
        raise DeviceNotAuthentic


def authenticate_device(
    client: TrezorClient,
    challenge: bytes | None = None,
    *,
    whitelist: t.Collection[bytes] | None = None,
    allow_development_devices: bool = False,
    root_pubkey: bytes | ec.EllipticCurvePublicKey | None = None,
) -> None:
    if challenge is None:
        challenge = secrets.token_bytes(16)

    resp = device.authenticate(client, challenge)

    return verify_authentication_response(
        challenge,
        resp.signature,
        resp.certificates,
        whitelist=whitelist,
        allow_development_devices=allow_development_devices,
        root_pubkey=root_pubkey,
    )
