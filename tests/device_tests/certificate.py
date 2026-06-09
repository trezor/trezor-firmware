from typing import Sequence

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, ed25519, mldsa
from cryptography.x509 import extensions as ext

from trezorlib import _root_keys, models
from trezorlib.models import TrezorModel

OPTIGA_ROOT_PUBLIC_KEY = {
    models.T2B1: bytes.fromhex(_root_keys.T2B1_DEV_AUTH_ROOT_DEBUG_P256_HEX),
    models.T3T1: bytes.fromhex(_root_keys.T3T1_DEV_AUTH_ROOT_DEBUG_P256_HEX),
    models.T3B1: bytes.fromhex(_root_keys.T3B1_DEV_AUTH_ROOT_DEBUG_P256_HEX),
    models.T3W1: bytes.fromhex(_root_keys.T3W1_DEV_AUTH_ROOT_DEBUG_P256_HEX),
}

TROPIC_ROOT_PUBLIC_KEY = {
    models.T3W1: bytes.fromhex(_root_keys.T3W1_DEV_AUTH_ROOT_DEBUG_ED25519_HEX),
}

MCU_ROOT_PUBLIC_KEY = {
    models.T3W1: bytes.fromhex(_root_keys.T3W1_DEV_AUTH_ROOT_DEBUG_MLDSA44_HEX),
}


def verify_cert_chain(certs, model_name, root_public_key):
    def verify_cert_signature(public_key, cert):
        if isinstance(public_key, ed25519.Ed25519PublicKey):
            public_key.verify(cert.signature, cert.tbs_certificate_bytes)
        elif isinstance(public_key, ec.EllipticCurvePublicKey):
            public_key.verify(
                cert.signature,
                cert.tbs_certificate_bytes,
                cert.signature_algorithm_parameters,
            )
        elif isinstance(public_key, mldsa.MLDSA44PublicKey):
            public_key.verify(cert.signature, cert.tbs_certificate_bytes)
        else:
            raise ValueError("Unsupported public key type")

    # Verify that the common name matches the Trezor model.
    common_name = certs[0].subject.get_attributes_for_oid(x509.oid.NameOID.COMMON_NAME)[
        0
    ]
    assert common_name.value.startswith(model_name)

    for i, (cert, ca_cert) in enumerate(zip(certs, certs[1:])):
        assert cert.issuer == ca_cert.subject

        ca_basic_constraints = ca_cert.extensions.get_extension_for_class(
            ext.BasicConstraints
        ).value
        assert ca_basic_constraints.ca is True
        # It is assumed that certs[0] is not a CA
        assert (
            ca_basic_constraints.path_length is not None
            and i <= ca_basic_constraints.path_length
        )

        try:
            ski = ca_cert.extensions.get_extension_for_class(
                ext.SubjectKeyIdentifier
            ).value
            aki = cert.extensions.get_extension_for_class(
                ext.AuthorityKeyIdentifier
            ).value
            assert aki.key_identifier == ski.key_identifier
        except ext.ExtensionNotFound:
            pass

        verify_cert_signature(ca_cert.public_key(), cert)

    # Verify the last certificate in the certificate chain against trust anchor.
    verify_cert_signature(root_public_key, certs[-1])

    # Verify the authority key identifier in the last certificate.
    try:
        aki = (
            certs[-1]
            .extensions.get_extension_for_class(ext.AuthorityKeyIdentifier)
            .value
        )
        assert (
            aki.key_identifier
            == ext.SubjectKeyIdentifier.from_public_key(root_public_key).key_identifier
        )
    except ext.ExtensionNotFound:
        pass


def check_signature_optiga(
    signature: bytes,
    certificate_chain: Sequence[bytes],
    model: TrezorModel,
    data: bytes,
) -> None:
    certs = [x509.load_der_x509_certificate(cert) for cert in certificate_chain]
    assert len(certs) >= 2  # at least one root and one device cert from Optiga

    root_public_key = ec.EllipticCurvePublicKey.from_encoded_point(
        ec.SECP256R1(), OPTIGA_ROOT_PUBLIC_KEY[model]
    )
    verify_cert_chain(certs, model.internal_name, root_public_key)

    # Verify the signature of the challenge.
    certs[0].public_key().verify(signature, data, ec.ECDSA(hashes.SHA256()))


def check_signature_mcu(
    signature: bytes,
    certificate_chain: Sequence[bytes],
    model: TrezorModel,
    data: bytes,
) -> None:
    certs = [x509.load_der_x509_certificate(cert) for cert in certificate_chain]
    assert len(certs) >= 1

    root_public_key = mldsa.MLDSA44PublicKey.from_public_bytes(
        MCU_ROOT_PUBLIC_KEY[model]
    )
    verify_cert_chain(certs, model.internal_name, root_public_key)

    certs[0].public_key().verify(signature, data)


def check_signature_tropic(
    signature: bytes,
    certificate_chain: Sequence[bytes],
    model: TrezorModel,
    data: bytes,
) -> None:
    certs = [x509.load_der_x509_certificate(cert) for cert in certificate_chain]

    # If this fails, make sure the emulator was built with DISABLE_TROPIC=0
    assert len(certs) >= 2  # at least one root and one device cert from Tropic

    root_public_key = ed25519.Ed25519PublicKey.from_public_bytes(
        TROPIC_ROOT_PUBLIC_KEY[model]
    )
    verify_cert_chain(certs, model.internal_name, root_public_key)

    # Verify the signature of the challenge.
    certs[0].public_key().verify(signature, bytearray(data))
