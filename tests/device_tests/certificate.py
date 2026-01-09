from typing import Sequence

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, ed25519
from cryptography.x509 import extensions as ext

from trezorlib import models
from trezorlib.models import TrezorModel

OPTIGA_ROOT_PUBLIC_KEY = {
    models.T2B1: bytes.fromhex(
        "047f77368dea2d4d61e989f474a56723c3212dacf8a808d8795595ef38441427c4389bc454f02089d7f08b873005e4c28d432468997871c0bf286fd3861e21e96a"
    ),
    models.T3T1: bytes.fromhex(
        "04e48b69cd7962068d3cca3bcc6b1747ef496c1e28b5529e34ad7295215ea161dbe8fb08ae0479568f9d2cb07630cb3e52f4af0692102da5873559e45e9fa72959"
    ),
    models.T3B1: bytes.fromhex(
        "047f77368dea2d4d61e989f474a56723c3212dacf8a808d8795595ef38441427c4389bc454f02089d7f08b873005e4c28d432468997871c0bf286fd3861e21e96a"
    ),
    models.T3W1: bytes.fromhex(
        "04521192e173a9da4e3023f747d836563725372681eba3079c56ff11b2fc137ab189eb4155f371127651b5594f8c332fc1e9c0f3b80d4212822668b63189706578"
    ),
}

TROPIC_ROOT_PUBLIC_KEY = {
    models.T3W1: bytes.fromhex(
        "1ab1c5f12f4570e0de5c16a8d9feea381f53c8d813feeb0eb2fb7f393f2b6b5f"
    ),
}


def verify_cert_chain(certs, model_name):
    for cert, ca_cert in zip(certs, certs[1:]):
        assert cert.issuer == ca_cert.subject

        ca_basic_constraints = ca_cert.extensions.get_extension_for_class(
            ext.BasicConstraints
        ).value
        assert ca_basic_constraints.ca is True

        try:
            basic_constraints = cert.extensions.get_extension_for_class(
                ext.BasicConstraints
            ).value
            if basic_constraints.ca:
                assert basic_constraints.path_length < ca_basic_constraints.path_length
        except ext.ExtensionNotFound:
            pass

        ca_public_key = ca_cert.public_key()
        if isinstance(ca_public_key, ed25519.Ed25519PublicKey):
            ca_public_key.verify(
                cert.signature,
                cert.tbs_certificate_bytes,
            )
        else:
            ca_public_key.verify(
                cert.signature,
                cert.tbs_certificate_bytes,
                cert.signature_algorithm_parameters,
            )

    # Verify that the common name matches the Trezor model.
    common_name = cert.subject.get_attributes_for_oid(x509.oid.NameOID.COMMON_NAME)[0]
    assert common_name.value.startswith(model_name)


def check_signature_optiga(
    signature: bytes,
    certificate_chain: Sequence[bytes],
    model: TrezorModel,
    data: bytes,
) -> None:
    certs = [x509.load_der_x509_certificate(cert) for cert in certificate_chain]
    assert len(certs) >= 2  # at least one root and one device cert from Optiga

    # Verify the last certificate in the certificate chain against trust anchor.
    root_public_key = ec.EllipticCurvePublicKey.from_encoded_point(
        ec.SECP256R1(), OPTIGA_ROOT_PUBLIC_KEY[model]
    )
    root_public_key.verify(
        certs[-1].signature,
        certs[-1].tbs_certificate_bytes,
        certs[-1].signature_algorithm_parameters,
    )

    verify_cert_chain(certs, model.internal_name)

    # Verify the signature of the challenge.
    certs[0].public_key().verify(signature, data, ec.ECDSA(hashes.SHA256()))


def check_signature_tropic(
    signature: bytes,
    certificate_chain: Sequence[bytes],
    model: TrezorModel,
    data: bytes,
) -> None:
    certs = [x509.load_der_x509_certificate(cert) for cert in certificate_chain]

    # If this fails, make sure the emulator was built with DISABLE_TROPIC=0
    assert len(certs) >= 2  # at least one root and one device cert from Tropic

    # Verify the last certificate in the certificate chain against trust anchor.
    root_public_key = ed25519.Ed25519PublicKey.from_public_bytes(
        TROPIC_ROOT_PUBLIC_KEY[model]
    )
    root_public_key.verify(
        certs[-1].signature,
        certs[-1].tbs_certificate_bytes,
    )

    verify_cert_chain(certs, model.internal_name)

    # Verify the signature of the challenge.
    certs[0].public_key().verify(signature, bytearray(data))
