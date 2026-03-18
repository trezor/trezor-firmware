# This file is part of the Trezor project.
#
# Copyright (C) SatoshiLabs and contributors
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3
# as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the License along with this library.
# If not, see <https://www.gnu.org/licenses/lgpl-3.0.html>.

from __future__ import annotations

import io
import logging
import secrets
import typing as t

from cryptography import exceptions, x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, ed25519, types, utils
from cryptography.x509.oid import NameOID, ObjectIdentifier, SignatureAlgorithmOID

from . import _root_keys, device
from .client import Session
from .tools import workflow

LOG = logging.getLogger(__name__)


def _pk_p256(pubkey_hex: str) -> PublicKey:
    return EcdsaPublicKey.from_bytes(bytes.fromhex(pubkey_hex), ec.SECP256R1())


def _pk_ed25519(pubkey_hex: str) -> PublicKey:
    return Ed25519PublicKey.from_bytes(bytes.fromhex(pubkey_hex))


def _pk_mldsa44(pubkey_hex: str) -> PublicKey:
    return Mldsa44PublicKey.from_bytes(bytes.fromhex(pubkey_hex))


CHALLENGE_HEADER = b"AuthenticateDevice:"

OID_TO_NAME = {
    NameOID.COMMON_NAME: "CN",
    NameOID.LOCALITY_NAME: "L",
    NameOID.STATE_OR_PROVINCE_NAME: "ST",
    NameOID.ORGANIZATION_NAME: "O",
    NameOID.ORGANIZATIONAL_UNIT_NAME: "OU",
    NameOID.COUNTRY_NAME: "C",
    NameOID.SERIAL_NUMBER: "SERIALNUMBER",
    NameOID.DN_QUALIFIER: "DNQ",
}


class DeviceNotAuthentic(Exception):
    pass


class AllowList:
    def __init__(self, data: dict[str, t.Any]) -> None:
        self.whitelist = None
        self.blacklist = None
        if "ca_pubkeys" in data:
            self.whitelist = [bytes.fromhex(pk) for pk in data["ca_pubkeys"]]
        if "revoked_pubkeys" in data:
            self.blacklist = [bytes.fromhex(pk) for pk in data["revoked_pubkeys"]]
        if self.whitelist is None and self.blacklist is None:
            raise ValueError(
                "Invalid allow list: no CA public keys or revoked public keys."
            )

    def is_allowed(self, pubkey: bytes) -> bool:
        if self.whitelist is not None:
            return pubkey in self.whitelist
        if self.blacklist is not None:
            return pubkey not in self.blacklist
        raise RuntimeError("Invalid allow list: no whitelist or blacklist entries.")


class PublicKey:
    @staticmethod
    def from_bytes_and_oid(data: bytes, oid: ObjectIdentifier) -> PublicKey:
        if oid == SignatureAlgorithmOID.ECDSA_WITH_SHA256:
            return EcdsaPublicKey.from_bytes(data, ec.SECP256R1())
        elif oid == SignatureAlgorithmOID.ED25519:
            return Ed25519PublicKey.from_bytes(data)
        # TODO replace after cryptography 47.0.0 is released
        elif oid == ObjectIdentifier("2.16.840.1.101.3.4.3.17"):
            return Mldsa44PublicKey.from_bytes(data)
        else:
            raise ValueError("Unsupported key type.")

    @staticmethod
    def from_public_key(pubkey: types.CertificatePublicKeyTypes) -> PublicKey:
        if isinstance(pubkey, ec.EllipticCurvePublicKey):
            return EcdsaPublicKey(pubkey)
        elif isinstance(pubkey, ed25519.Ed25519PublicKey):
            return Ed25519PublicKey(pubkey)
        # TODO after cryptography 47.0.0 is released
        else:
            raise ValueError("Unsupported key type.")

    def to_bytes(self) -> bytes:
        raise NotImplementedError

    def verify_message(self, *, message: bytes, signature: bytes) -> None:
        raise NotImplementedError

    def verify_certificate(self, certificate: x509.Certificate) -> None:
        raise NotImplementedError


class EcdsaPublicKey(PublicKey):
    def __init__(self, pubkey: ec.EllipticCurvePublicKey) -> None:
        self.pubkey = pubkey

    def default_algo_params(self) -> ec.ECDSA:
        if isinstance(self.pubkey.curve, ec.SECP256R1):
            return ec.ECDSA(hashes.SHA256())
        raise ValueError("Unsupported curve.")

    @classmethod
    def from_bytes(
        cls, data: bytes, curve: ec.EllipticCurve = ec.SECP256R1()
    ) -> EcdsaPublicKey:
        return cls(ec.EllipticCurvePublicKey.from_encoded_point(curve, data))

    def to_bytes(self) -> bytes:
        return self.pubkey.public_bytes(
            serialization.Encoding.X962,
            serialization.PublicFormat.UncompressedPoint,
        )

    def verify_message(self, *, signature: bytes, message: bytes) -> None:
        self.pubkey.verify(
            signature,
            message,
            self.default_algo_params(),
        )

    def verify_certificate(self, certificate: x509.Certificate) -> None:
        fixed_signature = self.fix_signature(certificate.signature)
        algo_params = certificate.signature_algorithm_parameters
        assert isinstance(algo_params, ec.ECDSA)
        self.pubkey.verify(
            fixed_signature,
            certificate.tbs_certificate_bytes,
            algo_params,
        )

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
        r, s = EcdsaPublicKey._decode_signature_permissive(sig_bytes)
        reencoded = utils.encode_dss_signature(r, s)
        if reencoded != sig_bytes:
            LOG.info(
                "Re-encoding malformed signature: %s -> %s",
                sig_bytes.hex(),
                reencoded.hex(),
            )
        return reencoded


class Ed25519PublicKey(PublicKey):
    def __init__(self, pubkey: ed25519.Ed25519PublicKey) -> None:
        self.pubkey = pubkey

    @classmethod
    def from_bytes(cls, data: bytes) -> Ed25519PublicKey:
        return cls(ed25519.Ed25519PublicKey.from_public_bytes(data))

    def to_bytes(self) -> bytes:
        return self.pubkey.public_bytes(
            serialization.Encoding.Raw,
            serialization.PublicFormat.Raw,
        )

    def verify_message(self, *, signature: bytes, message: bytes) -> None:
        self.pubkey.verify(
            signature,
            message,
        )

    def verify_certificate(self, certificate: x509.Certificate) -> None:
        self.verify_message(
            signature=certificate.signature, message=certificate.tbs_certificate_bytes
        )


class Mldsa44PublicKey(PublicKey):
    def __init__(self, pubkey: t.Any) -> None:
        self.pubkey = pubkey

    @classmethod
    def from_bytes(cls, data: bytes) -> Mldsa44PublicKey:
        # TODO after cryptography 47.0.0 is released
        return cls(None)

    def to_bytes(self) -> bytes:
        # TODO after cryptography 47.0.0 is released
        return bytes()

    def verify_message(self, *, signature: bytes, message: bytes) -> None:
        # TODO after cryptography 47.0.0 is released
        pass

    def verify_certificate(self, certificate: x509.Certificate) -> None:
        # TODO after cryptography 47.0.0 is released
        pass


class RootCertificate(t.NamedTuple):
    name: str
    device: str
    devel: bool
    p256_pubkey: PublicKey
    ed25519_pubkey: PublicKey | None = None
    mldsa44_pubkey: PublicKey | None = None

    def pubkey_for_oid(self, oid: ObjectIdentifier) -> PublicKey:
        if oid == SignatureAlgorithmOID.ECDSA_WITH_SHA256:
            return self.p256_pubkey
        elif oid == SignatureAlgorithmOID.ED25519:
            if self.ed25519_pubkey is None:
                raise ValueError("ED25519 public key not set.")
            return self.ed25519_pubkey
        # TODO replace after cryptography 47.0.0 is released
        elif oid == ObjectIdentifier("2.16.840.1.101.3.4.3.17"):
            if self.mldsa44_pubkey is None:
                raise ValueError("ML-DSA-44 public key not set.")
            return self.mldsa44_pubkey
        else:
            raise ValueError("Unsupported key type.")


ROOT_PUBLIC_KEYS = [
    RootCertificate(
        # Root production key for T2B1.
        "Trezor Company",
        "Trezor Safe 3",
        False,
        _pk_p256(_root_keys.T2B1_DEV_AUTH_ROOT_PROD_P256_HEX),
    ),
    RootCertificate(
        # Root production key for T3B1.
        "Trezor Company",
        "Trezor Safe 3",
        False,
        _pk_p256(_root_keys.T3B1_DEV_AUTH_ROOT_PROD_P256_HEX),
    ),
    RootCertificate(
        # Root production key for T3T1.
        "Trezor Company",
        "Trezor Safe 5",
        False,
        _pk_p256(_root_keys.T3T1_DEV_AUTH_ROOT_PROD_P256_HEX),
    ),
    RootCertificate(
        # Root production keys for T3W1.
        "Trezor Company",
        "Trezor Safe 7",
        False,
        _pk_p256(_root_keys.T3W1_DEV_AUTH_ROOT_PROD_P256_HEX),
        _pk_ed25519(_root_keys.T3W1_DEV_AUTH_ROOT_PROD_ED25519_HEX),
        _pk_mldsa44(_root_keys.T3W1_DEV_AUTH_ROOT_PROD_MLDSA44_HEX),
    ),
    RootCertificate(
        # Root backup production keys for T3W1.
        "Trezor Company",
        "Trezor Safe 7",
        False,
        _pk_p256(_root_keys.T3W1_DEV_AUTH_ROOT_PROD_BACKUP_P256_HEX),
        _pk_ed25519(_root_keys.T3W1_DEV_AUTH_ROOT_PROD_BACKUP_ED25519_HEX),
        _pk_mldsa44(_root_keys.T3W1_DEV_AUTH_ROOT_PROD_BACKUP_MLDSA44_HEX),
    ),
    RootCertificate(
        # Root debug key for T2B1 and T3B1.
        "TESTING ENVIRONMENT. DO NOT USE THIS DEVICE",
        "Trezor Safe 3",
        True,
        _pk_p256(_root_keys.T2B1_DEV_AUTH_ROOT_DEBUG_P256_HEX),
    ),
    RootCertificate(
        # Root debug key for T3T1.
        "TESTING ENVIRONMENT. DO NOT USE THIS DEVICE",
        "Trezor Safe 5",
        True,
        _pk_p256(_root_keys.T3T1_DEV_AUTH_ROOT_DEBUG_P256_HEX),
    ),
    RootCertificate(
        # Root debug keys for T3W1.
        "TESTING ENVIRONMENT. DO NOT USE THIS DEVICE",
        "Trezor Safe 7",
        True,
        _pk_p256(_root_keys.T3W1_DEV_AUTH_ROOT_DEBUG_P256_HEX),
    ),
    RootCertificate(
        # Root staging keys for T3W1.
        "TESTING ENVIRONMENT. DO NOT USE THIS DEVICE",
        "Trezor Safe 7",
        True,
        _pk_p256(_root_keys.T3W1_DEV_AUTH_ROOT_STAGING_P256_HEX),
        _pk_ed25519(_root_keys.T3W1_DEV_AUTH_ROOT_STAGING_ED25519_HEX),
        _pk_mldsa44(_root_keys.T3W1_DEV_AUTH_ROOT_STAGING_MLDSA44_HEX),
    ),
]


class Certificate:
    def __init__(self, cert_bytes: bytes) -> None:
        self.cert_bytes = cert_bytes
        self.cert = x509.load_der_x509_certificate(cert_bytes)
        self.public_key = PublicKey.from_public_key(self.cert.public_key())

    def __str__(self) -> str:
        return self.cert.subject.rfc4514_string(OID_TO_NAME)

    def signature_algorithm_oid(self) -> ObjectIdentifier:
        return self.cert.signature_algorithm_oid

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
            issuer.public_key.verify_certificate(self.cert)
            return True
        except exceptions.InvalidSignature:
            LOG.error("Issuer %s did not sign certificate %s.", issuer, self)

        return False


def verify_authentication_response(
    challenge: bytes,
    signature: bytes,
    cert_chain: t.Iterable[bytes],
    *,
    allowlist: AllowList | None,
    allow_development_devices: bool = False,
    root_pubkey: bytes | PublicKey | None = None,
) -> RootCertificate | None:
    """Evaluate the response to an AuthenticateDevice call.

    Performs all steps and logs their results via the logging facility. (The log can be
    accessed via the `LOG` object in this module.)

    When done, raises DeviceNotAuthentic if the device is not authentic.

    The optional argument `root_pubkey` allows you to specify a root public key either
    as a `PublicKey` object or as a byte-string.
    """
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
        cert.public_key.verify_message(signature=signature, message=challenge_bytes)
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

        if allowlist is None:
            LOG.warning("Skipping public key allowlist check.")
        else:
            if not allowlist.is_allowed(ca_cert.public_key.to_bytes()):
                LOG.error(f"CA certificate #{i} denied by allowlist: %s", ca_cert)
                failed = True

        if not cert.is_issued_by(ca_cert, i - 1):
            failed = True
        else:
            LOG.debug(f"{cert_label} verified successfully: %s", cert)

        cert = ca_cert
        cert_label = f"CA #{i} certificate"

    if isinstance(root_pubkey, (bytes, bytearray, memoryview)):
        root_pubkey = PublicKey.from_bytes_and_oid(
            root_pubkey, cert.signature_algorithm_oid()
        )

    if root_pubkey is not None:
        root = None
        try:
            root_pubkey.verify_certificate(cert.cert)
        except Exception:
            LOG.error(f"{cert_label} was not issued by the specified root.")
            failed = True
        else:
            LOG.info(f"{cert_label} was issued by the specified root.")

    else:
        for root in ROOT_PUBLIC_KEYS:
            try:
                root_pubkey = root.pubkey_for_oid(cert.signature_algorithm_oid())
                root_pubkey.verify_certificate(cert.cert)
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

    return root


@workflow()
def authenticate_device(
    session: Session,
    challenge: bytes | None = None,
    *,
    allowlist: AllowList | None = None,
    allow_development_devices: bool = False,
    p256_root_pubkey: bytes | PublicKey | None = None,
    ed25519_root_pubkey: bytes | PublicKey | None = None,
    mldsa44_root_pubkey: bytes | PublicKey | None = None,
) -> None:
    if challenge is None:
        challenge = secrets.token_bytes(16)

    resp = device.authenticate(session, challenge)

    optiga_root = verify_authentication_response(
        challenge,
        resp.optiga_signature,
        resp.optiga_certificates,
        allowlist=allowlist,
        allow_development_devices=allow_development_devices,
        root_pubkey=p256_root_pubkey,
    )

    if (
        getattr(optiga_root, "ed25519_pubkey", None) is not None
        or ed25519_root_pubkey is not None
    ):
        if not resp.tropic_signature:
            LOG.error("Missing Tropic signature.")
            raise DeviceNotAuthentic

        tropic_root = verify_authentication_response(
            challenge,
            resp.tropic_signature,
            resp.tropic_certificates,
            allowlist=allowlist,
            allow_development_devices=allow_development_devices,
            root_pubkey=ed25519_root_pubkey,
        )

        if optiga_root is not tropic_root:
            LOG.error("Certificates issued by different root authorities.")
            raise DeviceNotAuthentic

    if (
        getattr(optiga_root, "mldsa44_pubkey", None) is not None
        or mldsa44_root_pubkey is not None
    ):
        if not resp.mcu_signature:
            LOG.error("Missing MCU signature.")
            raise DeviceNotAuthentic

        mcu_root = verify_authentication_response(
            challenge,
            resp.mcu_signature,
            resp.mcu_certificates,
            allowlist=allowlist,
            allow_development_devices=allow_development_devices,
            root_pubkey=mldsa44_root_pubkey,
        )

        if optiga_root is not mcu_root:
            LOG.error("Certificates issued by different root authorities.")
            raise DeviceNotAuthentic
