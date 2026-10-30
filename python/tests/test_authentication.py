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

import datetime
import logging
import typing as t
from pathlib import Path

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, ed25519, mldsa
from cryptography.x509.oid import NameOID

from trezorlib import _ed25519, authentication, messages, models
from trezorlib.authentication import (
    AttestationSource,
    DeviceNotAuthentic,
    RootCertificate,
    RootKeyType,
)

OPTIGA = AttestationSource.OPTIGA
TROPIC = AttestationSource.TROPIC
MCU = AttestationSource.MCU

CHALLENGE = b"authentication test challenge"
MCU_VERSION = authentication.MCU_ATTESTATION_MIN_VERSION

PrivateKey = t.Union[
    ec.EllipticCurvePrivateKey, ed25519.Ed25519PrivateKey, mldsa.MLDSA44PrivateKey
]


def sign(key: PrivateKey, message: bytes) -> bytes:
    if isinstance(key, ec.EllipticCurvePrivateKey):
        return key.sign(message, ec.ECDSA(hashes.SHA256()))
    return key.sign(message)


@pytest.fixture
def caplog_error(caplog: pytest.LogCaptureFixture) -> pytest.LogCaptureFixture:
    caplog.set_level(logging.DEBUG, logger=authentication.LOG.name)
    return caplog


def assert_logged_error(caplog: pytest.LogCaptureFixture, message: str) -> None:
    errors = [r.getMessage() for r in caplog.records if r.levelno >= logging.ERROR]
    assert any(message in error for error in errors), errors


class FakeSession:
    def __init__(
        self, model: models.TrezorModel, version: tuple[int, int, int]
    ) -> None:
        self.model = model
        self.version = version

    def __enter__(self) -> FakeSession:
        return self

    def __exit__(self, *args: t.Any) -> None:
        pass


def authenticate_proof(
    monkeypatch: pytest.MonkeyPatch,
    model: models.TrezorModel,
    proof: messages.AuthenticityProof,
    version: tuple[int, int, int] = MCU_VERSION,
    **kwargs: t.Any,
) -> None:
    monkeypatch.setattr(
        authentication.device, "authenticate", lambda session, challenge: proof
    )
    authentication.authenticate_device(
        FakeSession(model, version),  # type: ignore [arg-type]
        CHALLENGE,
        **kwargs,
    )


# ==== tests with generated root keys ====


SERIAL = "12345678901234"
VALID_FROM = datetime.datetime(2025, 1, 1)
VALID_TO = datetime.datetime(2045, 1, 1)


def generate_key(source: AttestationSource) -> PrivateKey:
    if source is OPTIGA:
        return ec.generate_private_key(ec.SECP256R1())
    if source is TROPIC:
        return ed25519.Ed25519PrivateKey.generate()
    if source is MCU:
        return mldsa.MLDSA44PrivateKey.generate()
    raise ValueError("Unknown attestation source")


def make_x509_name(
    common_name: str | None, serial_number: str | None = None
) -> x509.Name:
    attributes = []
    if serial_number is not None:
        attributes.append(x509.NameAttribute(NameOID.SERIAL_NUMBER, serial_number))
    if common_name is not None:
        attributes.append(x509.NameAttribute(NameOID.COMMON_NAME, common_name))
    return x509.Name(attributes)


def make_certificate(
    subject: x509.Name,
    issuer: x509.Name,
    public_key: t.Any,
    signing_key: PrivateKey,
    *,
    ca: bool = False,
) -> bytes:
    builder = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(public_key)
        .serial_number(x509.random_serial_number())
        .not_valid_before(VALID_FROM)
        .not_valid_after(VALID_TO)
    )
    if ca:
        builder = builder.add_extension(
            x509.BasicConstraints(ca=True, path_length=0), critical=True
        ).add_extension(
            x509.KeyUsage(
                digital_signature=False,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=True,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
    algorithm = (
        hashes.SHA256() if isinstance(signing_key, ec.EllipticCurvePrivateKey) else None
    )
    certificate = builder.sign(signing_key, algorithm)
    return certificate.public_bytes(serialization.Encoding.DER)


class FakeRoot:
    """Root private keys together with the matching `RootCertificate`."""

    def __init__(
        self,
        trezor_models: tuple[models.TrezorModel, ...],
        key_type: RootKeyType,
        sources: tuple[AttestationSource, ...] = (OPTIGA, TROPIC, MCU),
    ) -> None:
        self.keys = {source: generate_key(source) for source in sources}
        pubkeys = {
            source: authentication.PublicKey.from_public_key(key.public_key())
            for source, key in self.keys.items()
        }
        self.certificate = RootCertificate(
            f"Test {key_type.name} root",
            trezor_models,
            key_type,
            pubkeys[OPTIGA],
            pubkeys.get(TROPIC),
            pubkeys.get(MCU),
        )

    def pubkey_bytes(self, source: AttestationSource) -> bytes:
        return self.certificate.pubkey_for_attestation_source(source).to_bytes()


class Chain(t.NamedTuple):
    certificates: list[bytes]
    device_key: PrivateKey

    def sign(self, challenge: bytes = CHALLENGE) -> bytes:
        message = authentication.get_challenge_message(challenge)
        return sign(self.device_key, message)


def make_chain(
    root: FakeRoot,
    source: AttestationSource,
    common_name: str | None = "T3W1 Trezor Safe 7",
    serial_number: str | None = SERIAL,
    *,
    ca_extensions: bool = True,
) -> Chain:
    """Build a certificate chain like the device returns it.

    Optiga and Tropic chains are [device, CA] with the CA issued by the root; the MCU
    chain is [device] issued by the root directly.
    """
    root_key = root.keys[source]
    root_name = make_x509_name("Test Root")
    device_key = generate_key(source)
    device_name = make_x509_name(common_name, serial_number)
    if source is MCU:
        device_cert = make_certificate(
            device_name, root_name, device_key.public_key(), root_key
        )
        return Chain([device_cert], device_key)

    ca_key = generate_key(source)
    ca_name = make_x509_name("Test CA")
    ca_cert = make_certificate(
        ca_name, root_name, ca_key.public_key(), root_key, ca=ca_extensions
    )
    device_cert = make_certificate(
        device_name, ca_name, device_key.public_key(), ca_key
    )
    return Chain([device_cert, ca_cert], device_key)


def make_chains(
    root: FakeRoot,
    common_name: str = "T3W1 Trezor Safe 7",
    serial_number: str | None = SERIAL,
) -> dict[AttestationSource, Chain]:
    return {
        source: make_chain(root, source, common_name, serial_number)
        for source in (OPTIGA, TROPIC, MCU)
    }


def make_proof(
    chains: t.Mapping[AttestationSource, Chain],
) -> messages.AuthenticityProof:
    def certificates(source: AttestationSource) -> list[bytes] | None:
        chain = chains.get(source)
        return chain.certificates if chain is not None else None

    def signature(source: AttestationSource) -> bytes | None:
        chain = chains.get(source)
        return chain.sign() if chain is not None else None

    return messages.AuthenticityProof(
        optiga_certificates=certificates(OPTIGA),
        optiga_signature=signature(OPTIGA) or b"",
        tropic_certificates=certificates(TROPIC),
        tropic_signature=signature(TROPIC),
        mcu_certificates=certificates(MCU),
        mcu_signature=signature(MCU),
    )


class Roots(t.NamedTuple):
    t3w1_prod: FakeRoot
    t3w1_backup: FakeRoot
    t3w1_debug: FakeRoot
    t3t1_prod: FakeRoot
    t3t1_debug: FakeRoot
    t2b1_prod: FakeRoot
    t3b1_prod: FakeRoot
    safe3_debug: FakeRoot


@pytest.fixture(scope="module")
def module_roots() -> Roots:
    return Roots(
        t3w1_prod=FakeRoot((models.T3W1,), RootKeyType.PROD),
        t3w1_backup=FakeRoot((models.T3W1,), RootKeyType.PROD_BACKUP),
        t3w1_debug=FakeRoot((models.T3W1,), RootKeyType.DEBUG),
        t3t1_prod=FakeRoot((models.T3T1,), RootKeyType.PROD, (OPTIGA,)),
        t3t1_debug=FakeRoot((models.T3T1,), RootKeyType.DEBUG, (OPTIGA,)),
        t2b1_prod=FakeRoot((models.T2B1,), RootKeyType.PROD, (OPTIGA,)),
        t3b1_prod=FakeRoot((models.T3B1,), RootKeyType.PROD, (OPTIGA,)),
        safe3_debug=FakeRoot((models.T2B1, models.T3B1), RootKeyType.DEBUG, (OPTIGA,)),
    )


@pytest.fixture
def roots(module_roots: Roots, monkeypatch: pytest.MonkeyPatch) -> Roots:
    monkeypatch.setattr(
        authentication,
        "ROOT_PUBLIC_KEYS",
        [root.certificate for root in module_roots],
    )
    return module_roots


def verify(
    chain: Chain,
    source: AttestationSource,
    *,
    signature: bytes | None = None,
    allowlist: authentication.AllowList | None = None,
    allow_development_devices: bool = False,
    root_pubkey: bytes | authentication.PublicKey | None = None,
) -> authentication.AuthenticationResult:
    return authentication.verify_authentication_response(
        CHALLENGE,
        chain.sign() if signature is None else signature,
        chain.certificates,
        source,
        allowlist=allowlist,
        allow_development_devices=allow_development_devices,
        root_pubkey=root_pubkey,
    )


def authenticate(
    monkeypatch: pytest.MonkeyPatch,
    model: models.TrezorModel,
    chains: t.Mapping[AttestationSource, Chain],
    version: tuple[int, int, int] = MCU_VERSION,
    **kwargs: t.Any,
) -> None:
    authenticate_proof(monkeypatch, model, make_proof(chains), version, **kwargs)


# ---- verify_authentication_response ----


@pytest.mark.parametrize("source", [OPTIGA, TROPIC, MCU])
def test_verify_builtin_root(roots: Roots, source: AttestationSource) -> None:
    chain = make_chain(roots.t3w1_prod, source)
    result = verify(chain, source)
    assert result.root is roots.t3w1_prod.certificate
    assert result.common_name == "T3W1 Trezor Safe 7"
    assert result.serial_number == SERIAL


def test_verify_backup_root(roots: Roots) -> None:
    chain = make_chain(roots.t3w1_backup, OPTIGA)
    assert verify(chain, OPTIGA).root is roots.t3w1_backup.certificate


def test_verify_without_serial_number(roots: Roots) -> None:
    chain = make_chain(roots.t3t1_prod, OPTIGA, "T3T1 Trezor Safe 5", None)
    assert verify(chain, OPTIGA).serial_number is None


@pytest.mark.parametrize(
    "chain_source, verify_source",
    [(OPTIGA, TROPIC), (TROPIC, MCU), (MCU, OPTIGA)],
)
def test_verify_wrong_attestation_source(
    roots: Roots,
    caplog_error: pytest.LogCaptureFixture,
    chain_source: AttestationSource,
    verify_source: AttestationSource,
) -> None:
    chain = make_chain(roots.t3w1_prod, chain_source)
    with pytest.raises(DeviceNotAuthentic):
        verify(chain, verify_source)
    assert_logged_error(caplog_error, "issued by an unknown root")


def test_verify_root_of_other_model(
    roots: Roots, caplog_error: pytest.LogCaptureFixture
) -> None:
    # signed by the T3W1 root, but claims to be a T3T1
    chain = make_chain(roots.t3w1_prod, OPTIGA, "T3T1 Trezor Safe 5")
    with pytest.raises(DeviceNotAuthentic):
        verify(chain, OPTIGA)
    assert_logged_error(caplog_error, "issued by an unknown root")


@pytest.mark.parametrize("common_name", ["T2B1 Trezor Safe 3", "T3B1 Trezor Safe 3"])
def test_verify_root_shared_by_models(roots: Roots, common_name: str) -> None:
    chain = make_chain(roots.safe3_debug, OPTIGA, common_name, None)
    result = verify(chain, OPTIGA, allow_development_devices=True)
    assert result.root is roots.safe3_debug.certificate


def test_verify_unknown_model(
    roots: Roots, caplog_error: pytest.LogCaptureFixture
) -> None:
    chain = make_chain(roots.t3w1_prod, OPTIGA, "X1Z9 Trezor Safe 7")
    with pytest.raises(DeviceNotAuthentic):
        verify(chain, OPTIGA)
    assert_logged_error(caplog_error, "Unknown model in device certificate")


def test_verify_no_common_name(
    roots: Roots, caplog_error: pytest.LogCaptureFixture
) -> None:
    chain = make_chain(roots.t3w1_prod, OPTIGA, None)
    with pytest.raises(DeviceNotAuthentic):
        verify(chain, OPTIGA)
    assert_logged_error(caplog_error, "no common_name")


def test_verify_wrong_challenge(
    roots: Roots, caplog_error: pytest.LogCaptureFixture
) -> None:
    chain = make_chain(roots.t3w1_prod, OPTIGA)
    signature = sign(
        chain.device_key, authentication.get_challenge_message(b"other challenge")
    )
    with pytest.raises(DeviceNotAuthentic):
        verify(chain, OPTIGA, signature=signature)
    assert_logged_error(caplog_error, "Challenge verification failed")


@pytest.mark.usefixtures("roots")
def test_verify_ca_not_issued_by_root(caplog_error: pytest.LogCaptureFixture) -> None:
    # chain issued by a root that is not among the known roots
    unknown_root = FakeRoot((models.T3W1,), RootKeyType.PROD, (OPTIGA,))
    chain = make_chain(unknown_root, OPTIGA)
    with pytest.raises(DeviceNotAuthentic):
        verify(chain, OPTIGA)
    assert_logged_error(caplog_error, "issued by an unknown root")


def test_verify_device_not_issued_by_ca(
    roots: Roots, caplog_error: pytest.LogCaptureFixture
) -> None:
    chain = make_chain(roots.t3w1_prod, OPTIGA)
    other_chain = make_chain(roots.t3w1_prod, OPTIGA)
    # device certificate of one chain with CA of another
    mixed = Chain(
        [chain.certificates[0], other_chain.certificates[1]], chain.device_key
    )
    with pytest.raises(DeviceNotAuthentic):
        verify(mixed, OPTIGA)
    assert_logged_error(caplog_error, "did not sign certificate")


def test_verify_ca_without_ca_extensions(
    roots: Roots, caplog_error: pytest.LogCaptureFixture
) -> None:
    chain = make_chain(roots.t3w1_prod, OPTIGA, ca_extensions=False)
    with pytest.raises(DeviceNotAuthentic):
        verify(chain, OPTIGA)
    assert_logged_error(caplog_error, "Missing extension")


@pytest.mark.parametrize("devel_allowed", [False, True])
def test_verify_debug_root(
    roots: Roots, caplog_error: pytest.LogCaptureFixture, devel_allowed: bool
) -> None:
    chain = make_chain(roots.t3w1_debug, OPTIGA)
    if devel_allowed:
        result = verify(chain, OPTIGA, allow_development_devices=True)
        assert result.root is roots.t3w1_debug.certificate
    else:
        with pytest.raises(DeviceNotAuthentic):
            verify(chain, OPTIGA)
        assert_logged_error(caplog_error, "Successfully verified a Trezor Safe 7")


def test_verify_allowlist(roots: Roots, caplog_error: pytest.LogCaptureFixture) -> None:
    chain = make_chain(roots.t3w1_prod, OPTIGA)
    ca_pubkey = authentication.Certificate(chain.certificates[1]).public_key.to_bytes()

    allowed = authentication.AllowList({"ca_pubkeys": [ca_pubkey.hex()]})
    verify(chain, OPTIGA, allowlist=allowed)

    revoked = authentication.AllowList({"revoked_pubkeys": [ca_pubkey.hex()]})
    with pytest.raises(DeviceNotAuthentic):
        verify(chain, OPTIGA, allowlist=revoked)
    assert_logged_error(caplog_error, "denied by allowlist")


@pytest.mark.parametrize("source", [OPTIGA, TROPIC, MCU])
def test_verify_custom_root_bytes(roots: Roots, source: AttestationSource) -> None:
    chain = make_chain(roots.t3w1_debug, source)
    # a debug root passed explicitly is accepted without allow_development_devices
    result = verify(chain, source, root_pubkey=roots.t3w1_debug.pubkey_bytes(source))
    assert result.root is None
    assert result.serial_number == SERIAL


def test_verify_custom_root_unknown_model(roots: Roots) -> None:
    # a custom root does not need the model to be known
    chain = make_chain(roots.t3w1_prod, OPTIGA, "X1Z9 Future Trezor")
    root_pubkey = roots.t3w1_prod.pubkey_bytes(OPTIGA)
    assert verify(chain, OPTIGA, root_pubkey=root_pubkey).root is None


@pytest.mark.parametrize("source", [OPTIGA, TROPIC, MCU])
def test_verify_custom_root_mismatch(
    roots: Roots, caplog_error: pytest.LogCaptureFixture, source: AttestationSource
) -> None:
    chain = make_chain(roots.t3w1_prod, source)
    with pytest.raises(DeviceNotAuthentic):
        verify(chain, source, root_pubkey=roots.t3w1_debug.pubkey_bytes(source))
    assert_logged_error(caplog_error, "not issued by the specified root")


# ---- authenticate_device ----


def test_authenticate_t3w1(roots: Roots, monkeypatch: pytest.MonkeyPatch) -> None:
    authenticate(monkeypatch, models.T3W1, make_chains(roots.t3w1_prod))


def test_authenticate_t3w1_debug(
    roots: Roots,
    monkeypatch: pytest.MonkeyPatch,
    caplog_error: pytest.LogCaptureFixture,
) -> None:
    chains = make_chains(roots.t3w1_debug)
    authenticate(monkeypatch, models.T3W1, chains, allow_development_devices=True)
    with pytest.raises(DeviceNotAuthentic):
        authenticate(monkeypatch, models.T3W1, chains)
    assert_logged_error(caplog_error, "manufactured by Test DEBUG root")


@pytest.mark.parametrize(
    "source, message",
    [(TROPIC, "Missing Tropic signature"), (MCU, "Missing MCU signature")],
)
def test_authenticate_t3w1_missing_proof(
    roots: Roots,
    monkeypatch: pytest.MonkeyPatch,
    caplog_error: pytest.LogCaptureFixture,
    source: AttestationSource,
    message: str,
) -> None:
    chains = make_chains(roots.t3w1_prod)
    del chains[source]
    with pytest.raises(DeviceNotAuthentic):
        authenticate(monkeypatch, models.T3W1, chains)
    assert_logged_error(caplog_error, message)


@pytest.mark.parametrize("source", [TROPIC, MCU])
def test_authenticate_t3w1_invalid_proof(
    roots: Roots,
    monkeypatch: pytest.MonkeyPatch,
    caplog_error: pytest.LogCaptureFixture,
    source: AttestationSource,
) -> None:
    chains = make_chains(roots.t3w1_prod)
    unknown_root = FakeRoot((models.T3W1,), RootKeyType.PROD)
    chains[source] = make_chain(unknown_root, source)
    with pytest.raises(DeviceNotAuthentic):
        authenticate(monkeypatch, models.T3W1, chains)
    assert_logged_error(caplog_error, "issued by an unknown root")


def test_authenticate_t3w1_mcu_min_version(
    roots: Roots,
    monkeypatch: pytest.MonkeyPatch,
    caplog_error: pytest.LogCaptureFixture,
) -> None:
    chains = make_chains(roots.t3w1_prod)
    authenticate(monkeypatch, models.T3W1, chains, version=MCU_VERSION)

    major, minor, patch = MCU_VERSION
    older = (major, minor, patch - 1)
    with pytest.raises(DeviceNotAuthentic):
        authenticate(monkeypatch, models.T3W1, chains, version=older)
    assert_logged_error(caplog_error, "does not support MCU attestation")


@pytest.mark.parametrize(
    "model, root_name, common_name",
    [
        (models.T3T1, "t3t1_prod", "T3T1 Trezor Safe 5"),
        (models.T2B1, "t2b1_prod", "T2B1 Trezor Safe 3"),
    ],
)
def test_authenticate_optiga_only(
    roots: Roots,
    monkeypatch: pytest.MonkeyPatch,
    model: models.TrezorModel,
    root_name: str,
    common_name: str,
) -> None:
    root = getattr(roots, root_name)
    chain = make_chain(root, OPTIGA, common_name)
    # Tropic and MCU proofs are not checked on models without them
    garbage = make_chain(FakeRoot((model,), RootKeyType.PROD), TROPIC, common_name)
    garbage_mcu = make_chain(FakeRoot((model,), RootKeyType.PROD), MCU, common_name)
    authenticate(monkeypatch, model, {OPTIGA: chain, TROPIC: garbage, MCU: garbage_mcu})


@pytest.mark.parametrize("source", [OPTIGA, TROPIC])
def test_authenticate_allowlist(
    roots: Roots,
    monkeypatch: pytest.MonkeyPatch,
    caplog_error: pytest.LogCaptureFixture,
    source: AttestationSource,
) -> None:
    chains = make_chains(roots.t3w1_prod)
    ca_pubkey = authentication.Certificate(chains[source].certificates[1]).public_key
    revoked = authentication.AllowList(
        {"revoked_pubkeys": [ca_pubkey.to_bytes().hex()]}
    )
    with pytest.raises(DeviceNotAuthentic):
        authenticate(monkeypatch, models.T3W1, chains, allowlist=revoked)
    assert_logged_error(caplog_error, "denied by allowlist")


def test_authenticate_custom_roots(
    roots: Roots, monkeypatch: pytest.MonkeyPatch
) -> None:
    chains = make_chains(roots.t3w1_debug)
    authenticate(
        monkeypatch,
        models.T3W1,
        chains,
        p256_root_pubkey=roots.t3w1_debug.pubkey_bytes(OPTIGA),
        ed25519_root_pubkey=roots.t3w1_debug.pubkey_bytes(TROPIC),
        mldsa44_root_pubkey=roots.t3w1_debug.pubkey_bytes(MCU),
    )


@pytest.mark.parametrize(
    "root_pubkey_arg, source, message",
    [
        ("ed25519_root_pubkey", TROPIC, "Missing Tropic signature"),
        ("mldsa44_root_pubkey", MCU, "Missing MCU signature"),
    ],
)
def test_authenticate_custom_root_requires_proof(
    roots: Roots,
    monkeypatch: pytest.MonkeyPatch,
    caplog_error: pytest.LogCaptureFixture,
    root_pubkey_arg: str,
    source: AttestationSource,
    message: str,
) -> None:
    # a custom Tropic or MCU root enforces that proof even on a model without it
    chain = make_chain(roots.t3t1_prod, OPTIGA, "T3T1 Trezor Safe 5")
    kwargs = {root_pubkey_arg: roots.t3w1_debug.pubkey_bytes(source)}
    with pytest.raises(DeviceNotAuthentic):
        authenticate(monkeypatch, models.T3T1, {OPTIGA: chain}, **kwargs)
    assert_logged_error(caplog_error, message)


def test_authenticate_mixed_roots(
    roots: Roots,
    monkeypatch: pytest.MonkeyPatch,
    caplog_error: pytest.LogCaptureFixture,
) -> None:
    chains = make_chains(roots.t3w1_prod)
    chains[TROPIC] = make_chain(roots.t3w1_backup, TROPIC)
    with pytest.raises(DeviceNotAuthentic):
        authenticate(monkeypatch, models.T3W1, chains)
    assert_logged_error(caplog_error, "different root authorities")


def test_authenticate_mixed_custom_and_builtin_roots(
    roots: Roots,
    monkeypatch: pytest.MonkeyPatch,
    caplog_error: pytest.LogCaptureFixture,
) -> None:
    chains = make_chains(roots.t3w1_prod)
    with pytest.raises(DeviceNotAuthentic):
        authenticate(
            monkeypatch,
            models.T3W1,
            chains,
            ed25519_root_pubkey=roots.t3w1_prod.pubkey_bytes(TROPIC),
        )
    assert_logged_error(caplog_error, "different root authorities")


def test_authenticate_inconsistent_serial_numbers(
    roots: Roots,
    monkeypatch: pytest.MonkeyPatch,
    caplog_error: pytest.LogCaptureFixture,
) -> None:
    chains = make_chains(roots.t3w1_prod)
    chains[MCU] = make_chain(roots.t3w1_prod, MCU, serial_number="99999999999999")
    with pytest.raises(DeviceNotAuthentic):
        authenticate(monkeypatch, models.T3W1, chains)
    assert_logged_error(caplog_error, "inconsistent serial numbers")


def test_authenticate_inconsistent_common_names(
    roots: Roots,
    monkeypatch: pytest.MonkeyPatch,
    caplog_error: pytest.LogCaptureFixture,
) -> None:
    chains = make_chains(roots.t3w1_prod)
    chains[TROPIC] = make_chain(roots.t3w1_prod, TROPIC, "T3W1 Trezor Safe 7 Pro")
    with pytest.raises(DeviceNotAuthentic):
        authenticate(monkeypatch, models.T3W1, chains)
    assert_logged_error(caplog_error, "inconsistent common names")


def test_authenticate_model_mismatch(
    roots: Roots,
    monkeypatch: pytest.MonkeyPatch,
    caplog_error: pytest.LogCaptureFixture,
) -> None:
    # A T3W1 reporting itself as a T3T1 to skip the Tropic and MCU checks.
    chains = make_chains(roots.t3w1_prod)
    with pytest.raises(DeviceNotAuthentic):
        authenticate(monkeypatch, models.T3T1, chains)
    assert_logged_error(caplog_error, "does not match model T3T1")


def test_authenticate_model_mismatch_safe5_as_t3w1(
    roots: Roots,
    monkeypatch: pytest.MonkeyPatch,
    caplog_error: pytest.LogCaptureFixture,
) -> None:
    # A Safe 5 Optiga in a device reporting itself as a T3W1.
    chain = make_chain(roots.t3t1_prod, OPTIGA, "T3T1 Trezor Safe 5")
    with pytest.raises(DeviceNotAuthentic):
        authenticate(monkeypatch, models.T3W1, {OPTIGA: chain})
    assert_logged_error(caplog_error, "Missing Tropic")


@pytest.mark.parametrize("serial_number", [None, ""])
def test_authenticate_t3w1_missing_serial_number(
    roots: Roots,
    monkeypatch: pytest.MonkeyPatch,
    caplog_error: pytest.LogCaptureFixture,
    serial_number: str | None,
) -> None:
    chains = make_chains(roots.t3w1_prod, serial_number=serial_number)
    with pytest.raises(DeviceNotAuthentic):
        authenticate(monkeypatch, models.T3W1, chains)
    assert_logged_error(caplog_error, "Missing serial number")


@pytest.mark.parametrize(
    "model, root_name, common_name, serial_number",
    [
        # Safe 3 and Safe 5 certificates don't have a serial number
        (models.T2B1, "t2b1_prod", "T2B1 Trezor Safe 3", None),
        (models.T3B1, "t3b1_prod", "T3B1 Trezor Safe 3", None),
        (models.T3T1, "t3t1_prod", "T3T1 Trezor Safe 5", None),
        # but one is accepted if present
        (models.T3T1, "t3t1_prod", "T3T1 Trezor Safe 5", SERIAL),
    ],
)
def test_authenticate_safe3_safe5_serial_number(
    roots: Roots,
    monkeypatch: pytest.MonkeyPatch,
    model: models.TrezorModel,
    root_name: str,
    common_name: str,
    serial_number: str | None,
) -> None:
    chain = make_chain(getattr(roots, root_name), OPTIGA, common_name, serial_number)
    authenticate(monkeypatch, model, {OPTIGA: chain})


# ==== tests with the built-in root keys ====


EMULATOR_CERTS = Path(__file__).parent / "emulator_certs"


class EmulatorChain(t.NamedTuple):
    model: models.TrezorModel
    source: AttestationSource
    certificates: list[bytes]


def split_certificates(data: bytes) -> list[bytes]:
    """Split concatenated DER certificates."""
    certificates = []
    while data:
        # SEQUENCE with a long-form length
        assert data[0] == 0x30 and data[1] & 0x80
        length_size = data[1] & 0x7F
        end = 2 + length_size + int.from_bytes(data[2 : 2 + length_size], "big")
        certificates.append(data[:end])
        data = data[end:]
    return certificates


def find_emulator_chains() -> list[EmulatorChain]:
    """Load the emulator certificate chains, named <attestation_source>_<MODEL>.der."""
    chains = []
    for path in sorted(EMULATOR_CERTS.glob("*.der")):
        source, internal_name = path.stem.split("_")
        model = models.by_internal_name(internal_name)
        assert model is not None, f"unknown model in {path.name}"
        certificates = split_certificates(path.read_bytes())
        chains.append(EmulatorChain(model, AttestationSource(source), certificates))
    assert chains, f"no certificates in {EMULATOR_CERTS}"
    return chains


EMULATOR_CHAINS = find_emulator_chains()
EMULATOR_MODELS = sorted(
    {chain.model for chain in EMULATOR_CHAINS}, key=lambda m: m.internal_name
)


# device keys of the emulators, see emulator_certs/README.md
EMULATOR_OPTIGA_KEY = (1 << 248).to_bytes(32, "big")
EMULATOR_MCU_SEED = b"\x03" * 32
EMULATOR_TROPIC_SCALAR = bytes.fromhex(
    "82dd598afde591037404da3802b9d3f314018c06c873829956972c0be0c24b07"
)
EMULATOR_TROPIC_PREFIX = bytes.fromhex(
    "98f2c4a414c8457f399a41a3863327aa67095f278d314fdc2e0b5146d7d55dfb"
)


def sign_ed25519_expanded(scalar: bytes, prefix: bytes, message: bytes) -> bytes:
    """Ed25519 signature with an expanded secret key, as stored in Tropic."""
    a = _ed25519.decodeint(scalar)
    public_key = _ed25519.encodepoint(_ed25519.scalarmult_B(a))
    r = _ed25519.Hint(prefix + message)
    R = _ed25519.encodepoint(_ed25519.scalarmult_B(r))
    S = (r + _ed25519.Hint(R + public_key + message) * a) % _ed25519.l
    return R + _ed25519.encodeint(S)


def emulator_signature(source: AttestationSource) -> bytes:
    message = authentication.get_challenge_message(CHALLENGE)
    if source is OPTIGA:
        key = ec.derive_private_key(
            int.from_bytes(EMULATOR_OPTIGA_KEY, "big"), ec.SECP256R1()
        )
        return sign(key, message)
    if source is TROPIC:
        return sign_ed25519_expanded(
            EMULATOR_TROPIC_SCALAR, EMULATOR_TROPIC_PREFIX, message
        )
    return sign(mldsa.MLDSA44PrivateKey.from_seed_bytes(EMULATOR_MCU_SEED), message)


TESTING_ROOT_NAME = "TESTING ENVIRONMENT. DO NOT USE THIS DEVICE"


def builtin_roots(model: models.TrezorModel) -> list[RootCertificate]:
    return [r for r in authentication.ROOT_PUBLIC_KEYS if model in r.trezor_models]


ALL_MODELS = sorted(models.ALL_MODELS, key=lambda m: m.internal_name)


# ---- built-in root keys ----


@pytest.mark.parametrize("model", ALL_MODELS, ids=[m.internal_name for m in ALL_MODELS])
def test_root_keys_for_model(model: models.TrezorModel) -> None:
    # Models with emulator certificates support authentication and need root keys.
    # Models without them must have no root keys, which would remain untested.
    roots = builtin_roots(model)
    if model not in EMULATOR_MODELS:
        assert not roots, "root keys without emulator certificates"
        return

    assert any(root.key_type is RootKeyType.PROD for root in roots)
    if model not in authentication.OPTIGA_ONLY_MODELS:
        # authenticate_device requires the Tropic and MCU chains for this model
        for root in roots:
            assert root.ed25519_pubkey is not None, root.key_type
            assert root.mldsa44_pubkey is not None, root.key_type


def test_root_keys_devel() -> None:
    # The name is shown to the user as the manufacturer, it must not hide a debug or
    # staging root.
    for root in authentication.ROOT_PUBLIC_KEYS:
        assert root.devel is (root.name == TESTING_ROOT_NAME), root.name


def test_root_keys_unique() -> None:
    keys = [
        pubkey.to_bytes()
        for root in authentication.ROOT_PUBLIC_KEYS
        for pubkey in (root.p256_pubkey, root.ed25519_pubkey, root.mldsa44_pubkey)
        if pubkey is not None
    ]
    assert len(keys) == len(set(keys))


def test_root_keys_mldsa44_valid() -> None:
    # ML-DSA-44 keys are only parsed when first used
    for root in authentication.ROOT_PUBLIC_KEYS:
        if root.mldsa44_pubkey is not None:
            mldsa.MLDSA44PublicKey.from_public_bytes(root.mldsa44_pubkey.to_bytes())


# ---- emulator certificates ----


@pytest.mark.parametrize(
    "chain",
    EMULATOR_CHAINS,
    ids=[f"{c.source.value}-{c.model.internal_name}" for c in EMULATOR_CHAINS],
)
def test_emulator_chain(
    caplog_error: pytest.LogCaptureFixture, chain: EmulatorChain
) -> None:
    def verify_emulator(**kwargs: t.Any) -> authentication.AuthenticationResult:
        return authentication.verify_authentication_response(
            CHALLENGE,
            emulator_signature(chain.source),
            chain.certificates,
            chain.source,
            allowlist=None,
            **kwargs,
        )

    result = verify_emulator(allow_development_devices=True)
    assert result.root is not None
    assert result.root.key_type is RootKeyType.DEBUG
    assert chain.model in result.root.trezor_models

    with pytest.raises(DeviceNotAuthentic):
        verify_emulator()
    assert_logged_error(caplog_error, f"manufactured by {TESTING_ROOT_NAME}")


@pytest.mark.parametrize(
    "model", EMULATOR_MODELS, ids=[m.internal_name for m in EMULATOR_MODELS]
)
def test_authenticate_emulator(
    monkeypatch: pytest.MonkeyPatch, model: models.TrezorModel
) -> None:
    proof = messages.AuthenticityProof(optiga_signature=b"")
    for chain in EMULATOR_CHAINS:
        if chain.model is model:
            source = chain.source.value
            setattr(proof, f"{source}_signature", emulator_signature(chain.source))
            setattr(proof, f"{source}_certificates", chain.certificates)
    authenticate_proof(monkeypatch, model, proof, allow_development_devices=True)
