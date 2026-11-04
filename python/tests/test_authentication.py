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

import contextlib
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
    RootKeyType,
    RootPublicKeys,
)

OPTIGA = AttestationSource.OPTIGA
TROPIC = AttestationSource.TROPIC
MCU = AttestationSource.MCU

CHALLENGE = b"authentication test challenge"
MCU_VERSION = authentication.MCU_ATTESTATION_MIN_VERSION

PrivateKey = t.Union[
    ec.EllipticCurvePrivateKey, ed25519.Ed25519PrivateKey, mldsa.MLDSA44PrivateKey
]


def model_cn(model: models.TrezorModel) -> str:
    """Common name used in the device certificates of the model."""
    return f"{model.internal_name} Trezor {model.name}"


def sign(key: PrivateKey, message: bytes) -> bytes:
    if isinstance(key, ec.EllipticCurvePrivateKey):
        return key.sign(message, ec.ECDSA(hashes.SHA256()))
    return key.sign(message)


Rejects = t.Callable[[str], t.ContextManager[None]]


@pytest.fixture
def rejects(caplog: pytest.LogCaptureFixture) -> Rejects:
    """Assert that the block raises `DeviceNotAuthentic` and logs the message."""
    caplog.set_level(logging.DEBUG, logger=authentication.LOG.name)

    @contextlib.contextmanager
    def ctx(message: str) -> t.Iterator[None]:
        with pytest.raises(DeviceNotAuthentic):
            yield
        errors = [r.getMessage() for r in caplog.records if r.levelno >= logging.ERROR]
        assert any(message in error for error in errors), errors

    return ctx


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


class AuthFromProof(t.Protocol):
    def __call__(
        self,
        model: models.TrezorModel,
        proof: messages.AuthenticityProof,
        version: tuple[int, int, int] = MCU_VERSION,
        **kwargs: t.Any,
    ) -> RootPublicKeys | None: ...


@pytest.fixture
def auth_proof(monkeypatch: pytest.MonkeyPatch) -> AuthFromProof:
    """Call `authenticate_device` with a fake session returning the given proof."""

    def do(
        model: models.TrezorModel,
        proof: messages.AuthenticityProof,
        version: tuple[int, int, int] = MCU_VERSION,
        **kwargs: t.Any,
    ) -> RootPublicKeys | None:
        monkeypatch.setattr(
            authentication.device, "authenticate", lambda session, challenge: proof
        )
        return authentication.authenticate_device(
            FakeSession(model, version),  # type: ignore [arg-type]
            CHALLENGE,
            **kwargs,
        )

    return do


# ==== tests with generated root keys ====


SERIAL = "12345678901234"
VALID_FROM = datetime.datetime(2025, 1, 1)
VALID_TO = datetime.datetime(2045, 1, 1)

# most tests build T3W1 chains
DEFAULT_COMMON_NAME = model_cn(models.T3W1)


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
    """Root private keys together with the matching `RootPublicKeys`."""

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
        self.public_keys = RootPublicKeys(
            f"Test {key_type.name} root",
            trezor_models,
            key_type,
            pubkeys[OPTIGA],
            pubkeys.get(TROPIC),
            pubkeys.get(MCU),
        )

    def pubkey_bytes(self, source: AttestationSource) -> bytes:
        return self.public_keys.pubkey_for_attestation_source(source).to_bytes()


class Chain(t.NamedTuple):
    certificates: list[bytes]
    device_key: PrivateKey

    def sign(self, challenge: bytes = CHALLENGE) -> bytes:
        message = authentication.get_challenge_message(challenge)
        return sign(self.device_key, message)


def make_chain(
    root: FakeRoot,
    source: AttestationSource,
    common_name: str | None = DEFAULT_COMMON_NAME,
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
    common_name: str = DEFAULT_COMMON_NAME,
    serial_number: str | None = SERIAL,
) -> dict[AttestationSource, Chain]:
    return {
        source: make_chain(root, source, common_name, serial_number)
        for source in (OPTIGA, TROPIC, MCU)
    }


def make_proof(
    parts: t.Mapping[AttestationSource, tuple[list[bytes], bytes]],
) -> messages.AuthenticityProof:
    def certificates(source: AttestationSource) -> list[bytes] | None:
        part = parts.get(source)
        return part[0] if part is not None else None

    def signature(source: AttestationSource) -> bytes | None:
        part = parts.get(source)
        return part[1] if part is not None else None

    return messages.AuthenticityProof(
        optiga_certificates=certificates(OPTIGA),
        # optiga_signature is a required protobuf field, the other signatures are not
        optiga_signature=signature(OPTIGA) or b"",
        tropic_certificates=certificates(TROPIC),
        tropic_signature=signature(TROPIC),
        mcu_certificates=certificates(MCU),
        mcu_signature=signature(MCU),
    )


class RootSpec(t.NamedTuple):
    name: str
    trezor_models: tuple[models.TrezorModel, ...]
    key_type: RootKeyType
    sources: tuple[AttestationSource, ...] = (OPTIGA, TROPIC, MCU)


ROOT_SPECS = (
    RootSpec("t3w1_prod", (models.T3W1,), RootKeyType.PROD),
    RootSpec("t3w1_backup", (models.T3W1,), RootKeyType.PROD_BACKUP),
    RootSpec("t3w1_debug", (models.T3W1,), RootKeyType.DEBUG),
    RootSpec("t3t1_prod", (models.T3T1,), RootKeyType.PROD, (OPTIGA,)),
    RootSpec("t3t1_debug", (models.T3T1,), RootKeyType.DEBUG, (OPTIGA,)),
    RootSpec("t2b1_prod", (models.T2B1,), RootKeyType.PROD, (OPTIGA,)),
    RootSpec("t3b1_prod", (models.T3B1,), RootKeyType.PROD, (OPTIGA,)),
    RootSpec("safe3_debug", (models.T2B1, models.T3B1), RootKeyType.DEBUG, (OPTIGA,)),
)

# every valid root x model x source combination
ROOT_MATRIX = [
    (spec, model, source)
    for spec in ROOT_SPECS
    for model in spec.trezor_models
    for source in spec.sources
]


class Roots(t.NamedTuple):
    t3w1_prod: FakeRoot
    t3w1_backup: FakeRoot
    t3w1_debug: FakeRoot
    t3t1_prod: FakeRoot
    t3t1_debug: FakeRoot
    t2b1_prod: FakeRoot
    t3b1_prod: FakeRoot
    safe3_debug: FakeRoot

    def prod(self, model: models.TrezorModel) -> FakeRoot:
        (spec,) = (
            s
            for s in ROOT_SPECS
            if s.key_type is RootKeyType.PROD and model in s.trezor_models
        )
        return getattr(self, spec.name)


@pytest.fixture(scope="module")
def module_roots() -> Roots:
    return Roots(
        **{s.name: FakeRoot(s.trezor_models, s.key_type, s.sources) for s in ROOT_SPECS}
    )


@pytest.fixture
def roots(module_roots: Roots, monkeypatch: pytest.MonkeyPatch) -> Roots:
    monkeypatch.setattr(
        authentication,
        "ROOT_PUBLIC_KEYS",
        [root.public_keys for root in module_roots],
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


class AuthFromChains(t.Protocol):
    def __call__(
        self,
        model: models.TrezorModel,
        chains: t.Mapping[AttestationSource, Chain],
        version: tuple[int, int, int] = MCU_VERSION,
        **kwargs: t.Any,
    ) -> RootPublicKeys | None: ...


@pytest.fixture
def auth(auth_proof: AuthFromProof) -> AuthFromChains:
    """Call `authenticate_device` with a fake session returning the given chains."""

    def do(
        model: models.TrezorModel,
        chains: t.Mapping[AttestationSource, Chain],
        version: tuple[int, int, int] = MCU_VERSION,
        **kwargs: t.Any,
    ) -> RootPublicKeys | None:
        parts = {
            source: (chain.certificates, chain.sign())
            for source, chain in chains.items()
        }
        return auth_proof(model, make_proof(parts), version, **kwargs)

    return do


# ---- verify_authentication_response ----


def test_model_cn_format() -> None:
    # pin the CN convention used by the production device certificates
    assert model_cn(models.T3W1) == "T3W1 Trezor Safe 7"


@pytest.mark.parametrize(
    "spec, model, source",
    ROOT_MATRIX,
    ids=[f"{s.name}-{m.internal_name}-{src.value}" for s, m, src in ROOT_MATRIX],
)
def test_verify_builtin_root(
    roots: Roots,
    spec: RootSpec,
    model: models.TrezorModel,
    source: AttestationSource,
) -> None:
    root = getattr(roots, spec.name)
    chain = make_chain(root, source, model_cn(model))
    result = verify(chain, source, allow_development_devices=root.public_keys.devel)
    assert result.root is root.public_keys
    assert result.common_name == model_cn(model)
    assert result.serial_number == SERIAL


def test_verify_without_serial_number(roots: Roots) -> None:
    chain = make_chain(roots.t3t1_prod, OPTIGA, model_cn(models.T3T1), None)
    assert verify(chain, OPTIGA).serial_number is None


@pytest.mark.parametrize(
    "chain_source, verify_source",
    [(OPTIGA, TROPIC), (TROPIC, MCU), (MCU, OPTIGA)],
)
def test_verify_wrong_attestation_source(
    roots: Roots,
    rejects: Rejects,
    chain_source: AttestationSource,
    verify_source: AttestationSource,
) -> None:
    chain = make_chain(roots.t3w1_prod, chain_source)
    with rejects("issued by an unknown root"):
        verify(chain, verify_source)


def test_verify_root_of_other_model(roots: Roots, rejects: Rejects) -> None:
    # signed by the T3W1 root, but claims to be a T3T1
    chain = make_chain(roots.t3w1_prod, OPTIGA, model_cn(models.T3T1))
    with rejects("issued by an unknown root"):
        verify(chain, OPTIGA)


def test_verify_unknown_model(roots: Roots, rejects: Rejects) -> None:
    chain = make_chain(roots.t3w1_prod, OPTIGA, "X1Z9 Trezor Safe 7")
    with rejects("Unknown model in device certificate"):
        verify(chain, OPTIGA)


def test_verify_no_common_name(roots: Roots, rejects: Rejects) -> None:
    chain = make_chain(roots.t3w1_prod, OPTIGA, None)
    with rejects("no common_name"):
        verify(chain, OPTIGA)


def test_verify_wrong_challenge(roots: Roots, rejects: Rejects) -> None:
    chain = make_chain(roots.t3w1_prod, OPTIGA)
    signature = sign(
        chain.device_key, authentication.get_challenge_message(b"other challenge")
    )
    with rejects("Challenge verification failed"):
        verify(chain, OPTIGA, signature=signature)


@pytest.mark.usefixtures("roots")
def test_verify_ca_not_issued_by_root(rejects: Rejects) -> None:
    # chain issued by a root that is not among the known roots
    unknown_root = FakeRoot((models.T3W1,), RootKeyType.PROD, (OPTIGA,))
    chain = make_chain(unknown_root, OPTIGA)
    with rejects("issued by an unknown root"):
        verify(chain, OPTIGA)


def test_verify_device_not_issued_by_ca(roots: Roots, rejects: Rejects) -> None:
    chain = make_chain(roots.t3w1_prod, OPTIGA)
    other_chain = make_chain(roots.t3w1_prod, OPTIGA)
    # device certificate of one chain with CA of another
    mixed = Chain(
        [chain.certificates[0], other_chain.certificates[1]], chain.device_key
    )
    with rejects("did not sign certificate"):
        verify(mixed, OPTIGA)


def test_verify_ca_without_ca_extensions(roots: Roots, rejects: Rejects) -> None:
    chain = make_chain(roots.t3w1_prod, OPTIGA, ca_extensions=False)
    with rejects("Missing extension"):
        verify(chain, OPTIGA)


def test_verify_debug_root_rejected(roots: Roots, rejects: Rejects) -> None:
    chain = make_chain(roots.t3w1_debug, OPTIGA)
    with rejects("Successfully verified a Trezor Safe 7"):
        verify(chain, OPTIGA)


def test_verify_allowlist(roots: Roots, rejects: Rejects) -> None:
    chain = make_chain(roots.t3w1_prod, OPTIGA)
    ca_pubkey = authentication.Certificate(chain.certificates[1]).public_key.to_bytes()

    allowed = authentication.AllowList({"ca_pubkeys": [ca_pubkey.hex()]})
    verify(chain, OPTIGA, allowlist=allowed)

    revoked = authentication.AllowList({"revoked_pubkeys": [ca_pubkey.hex()]})
    with rejects("denied by allowlist"):
        verify(chain, OPTIGA, allowlist=revoked)


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
    roots: Roots, rejects: Rejects, source: AttestationSource
) -> None:
    chain = make_chain(roots.t3w1_prod, source)
    with rejects("not issued by the specified root"):
        verify(chain, source, root_pubkey=roots.t3w1_debug.pubkey_bytes(source))


# ---- authenticate_device ----


def test_authenticate_t3w1(roots: Roots, auth: AuthFromChains) -> None:
    root = auth(models.T3W1, make_chains(roots.t3w1_prod))
    assert root is roots.t3w1_prod.public_keys


def test_authenticate_t3w1_debug_allowed(roots: Roots, auth: AuthFromChains) -> None:
    chains = make_chains(roots.t3w1_debug)
    root = auth(models.T3W1, chains, allow_development_devices=True)
    assert root is roots.t3w1_debug.public_keys


def test_authenticate_t3w1_debug_rejected(
    roots: Roots, auth: AuthFromChains, rejects: Rejects
) -> None:
    chains = make_chains(roots.t3w1_debug)
    with rejects("manufactured by Test DEBUG root"):
        auth(models.T3W1, chains)


@pytest.mark.parametrize(
    "source, message",
    [(TROPIC, "Missing Tropic signature"), (MCU, "Missing MCU signature")],
)
def test_authenticate_t3w1_missing_proof(
    roots: Roots,
    auth: AuthFromChains,
    rejects: Rejects,
    source: AttestationSource,
    message: str,
) -> None:
    chains = make_chains(roots.t3w1_prod)
    del chains[source]
    with rejects(message):
        auth(models.T3W1, chains)


@pytest.mark.parametrize("source", [TROPIC, MCU])
def test_authenticate_t3w1_invalid_proof(
    roots: Roots, auth: AuthFromChains, rejects: Rejects, source: AttestationSource
) -> None:
    chains = make_chains(roots.t3w1_prod)
    unknown_root = FakeRoot((models.T3W1,), RootKeyType.PROD)
    chains[source] = make_chain(unknown_root, source)
    with rejects("issued by an unknown root"):
        auth(models.T3W1, chains)


def test_authenticate_t3w1_mcu_min_version(
    roots: Roots, auth: AuthFromChains, rejects: Rejects
) -> None:
    chains = make_chains(roots.t3w1_prod)
    root = auth(models.T3W1, chains, version=MCU_VERSION)
    assert root is roots.t3w1_prod.public_keys

    major, minor, patch = MCU_VERSION
    older = (major, minor, patch - 1)
    with rejects("does not support MCU attestation"):
        auth(models.T3W1, chains, version=older)


@pytest.mark.parametrize(
    "model",
    authentication.OPTIGA_ONLY_MODELS,
    ids=[m.internal_name for m in authentication.OPTIGA_ONLY_MODELS],
)
def test_authenticate_optiga_only(
    roots: Roots, auth: AuthFromChains, model: models.TrezorModel
) -> None:
    common_name = model_cn(model)
    chain = make_chain(roots.prod(model), OPTIGA, common_name)
    # Tropic and MCU proofs are not checked on models without them
    unknown_root = FakeRoot((model,), RootKeyType.PROD)
    chains = {
        OPTIGA: chain,
        TROPIC: make_chain(unknown_root, TROPIC, common_name),
        MCU: make_chain(unknown_root, MCU, common_name),
    }
    assert auth(model, chains) is roots.prod(model).public_keys


@pytest.mark.parametrize("source", [OPTIGA, TROPIC])
def test_authenticate_allowlist(
    roots: Roots, auth: AuthFromChains, rejects: Rejects, source: AttestationSource
) -> None:
    chains = make_chains(roots.t3w1_prod)
    ca_pubkey = authentication.Certificate(chains[source].certificates[1]).public_key
    revoked = authentication.AllowList(
        {"revoked_pubkeys": [ca_pubkey.to_bytes().hex()]}
    )
    with rejects("denied by allowlist"):
        auth(models.T3W1, chains, allowlist=revoked)


def test_authenticate_custom_roots(roots: Roots, auth: AuthFromChains) -> None:
    chains = make_chains(roots.t3w1_debug)
    root = auth(
        models.T3W1,
        chains,
        p256_root_pubkey=roots.t3w1_debug.pubkey_bytes(OPTIGA),
        ed25519_root_pubkey=roots.t3w1_debug.pubkey_bytes(TROPIC),
        mldsa44_root_pubkey=roots.t3w1_debug.pubkey_bytes(MCU),
    )
    # custom roots are not matched against the built-in ones
    assert root is None


@pytest.mark.parametrize(
    "root_pubkey_arg, source, message",
    [
        ("ed25519_root_pubkey", TROPIC, "Missing Tropic signature"),
        ("mldsa44_root_pubkey", MCU, "Missing MCU signature"),
    ],
)
def test_authenticate_custom_root_requires_proof(
    roots: Roots,
    auth: AuthFromChains,
    rejects: Rejects,
    root_pubkey_arg: str,
    source: AttestationSource,
    message: str,
) -> None:
    # a custom Tropic or MCU root enforces that proof even on a model without it
    chain = make_chain(roots.t3t1_prod, OPTIGA, model_cn(models.T3T1))
    kwargs: dict[str, t.Any] = {root_pubkey_arg: roots.t3w1_debug.pubkey_bytes(source)}
    with rejects(message):
        auth(models.T3T1, {OPTIGA: chain}, **kwargs)


def test_authenticate_mixed_roots(roots: Roots, auth: AuthFromChains, rejects: Rejects) -> None:
    chains = make_chains(roots.t3w1_prod)
    chains[TROPIC] = make_chain(roots.t3w1_backup, TROPIC)
    with rejects("different root authorities"):
        auth(models.T3W1, chains)


def test_authenticate_mixed_custom_and_builtin_roots(
    roots: Roots, auth: AuthFromChains, rejects: Rejects
) -> None:
    chains = make_chains(roots.t3w1_prod)
    with rejects("different root authorities"):
        auth(
            models.T3W1,
            chains,
            ed25519_root_pubkey=roots.t3w1_prod.pubkey_bytes(TROPIC),
        )


def test_authenticate_inconsistent_serial_numbers(
    roots: Roots, auth: AuthFromChains, rejects: Rejects
) -> None:
    chains = make_chains(roots.t3w1_prod)
    chains[MCU] = make_chain(roots.t3w1_prod, MCU, serial_number="99999999999999")
    with rejects("inconsistent serial numbers"):
        auth(models.T3W1, chains)


def test_authenticate_inconsistent_common_names(
    roots: Roots, auth: AuthFromChains, rejects: Rejects
) -> None:
    chains = make_chains(roots.t3w1_prod)
    chains[TROPIC] = make_chain(roots.t3w1_prod, TROPIC, "T3W1 Trezor Safe 7 Pro")
    with rejects("inconsistent common names"):
        auth(models.T3W1, chains)


def test_authenticate_model_mismatch(
    roots: Roots, auth: AuthFromChains, rejects: Rejects
) -> None:
    # A T3W1 reporting itself as a T3T1 to skip the Tropic and MCU checks.
    chains = make_chains(roots.t3w1_prod)
    with rejects("does not match model T3T1"):
        auth(models.T3T1, chains)


def test_authenticate_model_mismatch_safe5_as_t3w1(
    roots: Roots, auth: AuthFromChains, rejects: Rejects
) -> None:
    # A Safe 5 Optiga in a device reporting itself as a T3W1.
    chain = make_chain(roots.t3t1_prod, OPTIGA, model_cn(models.T3T1))
    with rejects("Missing Tropic"):
        auth(models.T3W1, {OPTIGA: chain})


@pytest.mark.parametrize("serial_number", [None, ""])
def test_authenticate_t3w1_missing_serial_number(
    roots: Roots, auth: AuthFromChains, rejects: Rejects, serial_number: str | None
) -> None:
    chains = make_chains(roots.t3w1_prod, serial_number=serial_number)
    with rejects("Missing serial number"):
        auth(models.T3W1, chains)


@pytest.mark.parametrize(
    "model, serial_number",
    [
        # Safe 3 and Safe 5 certificates don't have a serial number
        (models.T2B1, None),
        (models.T3B1, None),
        (models.T3T1, None),
        # but one is accepted if present
        (models.T3T1, SERIAL),
    ],
    ids=["T2B1", "T3B1", "T3T1", "T3T1-with-serial"],
)
def test_authenticate_safe3_safe5_serial_number(
    roots: Roots,
    auth: AuthFromChains,
    model: models.TrezorModel,
    serial_number: str | None,
) -> None:
    root = roots.prod(model)
    chain = make_chain(root, OPTIGA, model_cn(model), serial_number)
    assert auth(model, {OPTIGA: chain}) is root.public_keys


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


def emulator_signature(source: AttestationSource) -> bytes:
    message = authentication.get_challenge_message(CHALLENGE)
    if source is OPTIGA:
        key = ec.derive_private_key(
            int.from_bytes(EMULATOR_OPTIGA_KEY, "big"), ec.SECP256R1()
        )
        return sign(key, message)
    if source is TROPIC:
        return _ed25519.signature_unsafe_expanded(
            message, EMULATOR_TROPIC_SCALAR, EMULATOR_TROPIC_PREFIX
        )
    return sign(mldsa.MLDSA44PrivateKey.from_seed_bytes(EMULATOR_MCU_SEED), message)


TESTING_ROOT_NAME = "TESTING ENVIRONMENT. DO NOT USE THIS DEVICE"


ALL_MODELS = sorted(models.ALL_MODELS, key=lambda m: m.internal_name)


# ---- built-in root keys ----


@pytest.mark.parametrize("model", ALL_MODELS, ids=[m.internal_name for m in ALL_MODELS])
def test_root_keys_for_model(model: models.TrezorModel) -> None:
    # Models with emulator certificates support authentication and need root keys.
    # Models without them must have no root keys, which would remain untested.
    roots = authentication.roots_for_model(model)
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
def test_emulator_chain(rejects: Rejects, chain: EmulatorChain) -> None:
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

    with rejects(f"manufactured by {TESTING_ROOT_NAME}"):
        verify_emulator()


@pytest.mark.parametrize(
    "model", EMULATOR_MODELS, ids=[m.internal_name for m in EMULATOR_MODELS]
)
def test_authenticate_emulator(
    auth_proof: AuthFromProof, model: models.TrezorModel
) -> None:
    proof = make_proof(
        {
            chain.source: (chain.certificates, emulator_signature(chain.source))
            for chain in EMULATOR_CHAINS
            if chain.model is model
        }
    )
    root = auth_proof(model, proof, allow_development_devices=True)
    assert root is not None
    assert root.devel
    assert model in root.trezor_models
