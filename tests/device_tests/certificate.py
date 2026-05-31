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
        "0423bf3b9859e851a40820d6c142074f495fd7d2714064e26cc5abcb09bff287b4ca835f861c5da427221adc8f5c009925fee638d1ee4d8a85cb2e0754b6069576"
    ),
}

TROPIC_ROOT_PUBLIC_KEY = {
    models.T3W1: bytes.fromhex(
        # This is `DEV_AUTH_ROOT_DEBUG_ED25519` from `hsm_keys.json`
        "70d67d085ca885a3a1d850c5dfec3a7ae53d9e0a7fe43b6e78d3a7da0b5c0484"
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

        ski = ca_cert.extensions.get_extension_for_class(ext.SubjectKeyIdentifier).value
        aki = cert.extensions.get_extension_for_class(ext.AuthorityKeyIdentifier).value
        assert aki.key_identifier == ski.key_identifier

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

    # Verify the authority key identifier in the last certificate.
    aki = certs[-1].extensions.get_extension_for_class(ext.AuthorityKeyIdentifier).value
    assert (
        aki.key_identifier
        == ext.SubjectKeyIdentifier.from_public_key(root_public_key).key_identifier
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

    # Verify the authority key identifier in the last certificate.
    aki = certs[-1].extensions.get_extension_for_class(ext.AuthorityKeyIdentifier).value
    assert (
        aki.key_identifier
        == ext.SubjectKeyIdentifier.from_public_key(root_public_key).key_identifier
    )

    verify_cert_chain(certs, model.internal_name)

    # Verify the signature of the challenge.
    certs[0].public_key().verify(signature, bytearray(data))
