# This file is part of the Trezor project.
#
# Copyright (C) 2012-2019 SatoshiLabs and contributors
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

"""Fixtures for the ExtAppLoad device tests.

App images are built here with trezorlib's ``AppHeader``/``AppImage`` rather than
with ``extapp_tool generate-apps``: that command deliberately emits placeholder
headers (``abi_version=5``, ``target_arch=5``, ``code_size=1``, zeroed
``chunk_hash``) which exist to produce Merkle-tree leaves, and which the device
rejects at the very first header check. ``extapp_tool`` is still used for the
part it owns -- the Merkle proofs and the signed root packet.

Because the Merkle leaf is the *header fingerprint*, any header field a test
wants to vary has to be baked in before proofs are generated. Hence the variants
below are all built up-front and fed into a single tree, so each one gets a
valid proof of its own.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import typing as t
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

import pytest

from trezorlib import messages
from trezorlib.extapp import AppHeader, AppImage
from trezorlib.root_packet import RootPacket

if t.TYPE_CHECKING:
    from trezorlib.debuglink import DebugSession as Session

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent
EXTAPP_TOOL = ROOT / "core" / "tools" / "trezor_core_tools" / "extapp_tool.py"

# Device-side constants (core/embed/io/app_arena/inc/io/app_header.h).
ABI_VERSION = 1
TARGET_ARCH_ARMV8M = 0
TARGET_ARCH_X86_64 = 1

# Ring 0 keeps the root packet simple: a single-ring packet with chain_timestamp 0.
APP_RING = 0

# A payload that dlopen() will reject, fine for every test that is expected to
# fail before `image.run()` is ever reached.
DUMMY_PAYLOAD = b"\xde\xad\xbe\xef" * 64

APPLET_STUB_SOURCE = """
/* Minimal loadable applet: unix app_loader dlopen()s the payload and
   dlsym()s "applet_main" (core/embed/io/app_arena/unix/app_loader.c). */
void applet_main(void *api_getter) { (void)api_getter; }
"""


def _chunk_hash_chain(payload: bytes, chunk_size: int) -> bytes:
    """Compute the header's ``chunk_hash`` for ``payload``.

    Mirrors ``AppImage.chunks()``, which only *validates* the chain and offers no
    way to compute it. The chain runs backwards: each chunk is hashed together
    with the hash of the chunk that follows it, so the head of the chain commits
    to the whole payload.
    """
    chunks = [payload[i : i + chunk_size] for i in range(0, len(payload), chunk_size)]
    digest = b"\x00" * 32
    for chunk in reversed(chunks):
        digest = sha256(digest + chunk).digest()
    return digest


def make_image(
    app_id: str,
    payload: bytes = DUMMY_PAYLOAD,
    *,
    chunk_size: int = 1024,
    version: tuple[int, int, int, int] = (1, 0, 0, 0),
    code_size: int | None = None,
    target_arch: int = TARGET_ARCH_X86_64,
    abi_version: int = ABI_VERSION,
    app_ring: int = APP_RING,
) -> AppImage:
    """Build a coherent, device-loadable app image.

    ``code_size`` defaults to the real payload length; overriding it to something
    larger is what produces the "App image truncated" case.
    """
    # chunk_size 0 is a deliberately malformed variant -- the hash chain is
    # meaningless there, and the device divides by it before asking for a chunk.
    chunk_hash = _chunk_hash_chain(payload, chunk_size) if chunk_size else b"\x00" * 32
    header = AppHeader(
        magic=b"TRZA",
        header_size=484,
        id=app_id,
        name=app_id,
        vendor="",
        model="T3W1",
        version=version,
        sdk_version=(0, 1, 0, 0),
        abi_version=abi_version,
        target_arch=target_arch,
        app_ring=app_ring,
        code_size=len(payload) if code_size is None else code_size,
        data_size=8 * 1024,
        chunk_hash=chunk_hash,
        chunk_size=chunk_size,
        curves=[],
        paths=[],
    )
    return AppImage(header=header, payload=payload)


@dataclass
class AppFixture:
    """One built app plus the Merkle proof binding it to the root packet."""

    image: AppImage
    binary: bytes
    proof: bytes

    def chunks(self) -> list[tuple[bytes, bytes]]:
        return self.image.chunks()


@dataclass
class ExtappFixtures:
    apps: dict[str, AppFixture]
    root_packet: bytes
    # The same packet before signing -- the device must reject it.
    root_packet_unsigned: bytes
    root_packet_timestamp: int

    def __getitem__(self, name: str) -> AppFixture:
        return self.apps[name]


def _run_tool(*args: str | Path) -> None:
    subprocess.run(
        [sys.executable, str(EXTAPP_TOOL), *(str(a) for a in args)],
        check=True,
        capture_output=True,
        text=True,
    )


@pytest.fixture(scope="session")
def applet_stub() -> bytes:
    """A payload the unix loader will actually accept: an ELF .so with applet_main.

    TODO: swap this for a real SDK-built app once those land in-tree; the tests
    consuming it only care that the payload is loadable, so the swap is local to
    this fixture.
    """
    if shutil.which("gcc") is None:
        pytest.skip("gcc not available to build the loadable applet stub")

    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "applet.c"
        so = Path(tmp) / "applet.so"
        src.write_text(APPLET_STUB_SOURCE)
        subprocess.run(
            ["gcc", "-shared", "-fPIC", "-o", str(so), str(src)],
            check=True,
            capture_output=True,
        )
        return so.read_bytes()


@pytest.fixture(scope="session")
def extapp_fixtures(tmp_path_factory: pytest.TempPathFactory, applet_stub: bytes):
    """Build every app variant, then one Merkle tree + signed root packet over them."""
    variants: dict[str, AppImage] = {
        # dlopen-able, single chunk -- the only one that can reach ExtAppLoaded.
        "valid": make_image("valid.trezor.com", applet_stub, chunk_size=4096),
        # Same, but small chunks so the device has to ask for several.
        "multichunk": make_image("multi.trezor.com", applet_stub, chunk_size=512),
        # A second distinct app, for the "load A then B" eviction case.
        "other": make_image("other.trezor.com", applet_stub, chunk_size=4096),
        # code_size deliberately larger than the payload: every chunk validates,
        # but the image never becomes ready => "App image truncated".
        # code_size has to stay inside the *same* chunk count as the payload
        # (ceil(256/128) == ceil(200/128) == 2), otherwise the device asks for
        # chunks the host does not have instead of reaching the ready check.
        "truncated": make_image(
            "truncated.trezor.com",
            DUMMY_PAYLOAD[:200],
            chunk_size=128,
            code_size=256,
        ),
        # chunk_size == 0 is not validated by app_header_verify; the device
        # divides by it (load.py:81).
        "zero_chunk": make_image("zerochunk.trezor.com", chunk_size=0),
        # ARM payload on a unix emulator -- rejected by app_loader_verify_payload
        # on the final chunk.
        "wrong_arch": make_image(
            "wrongarch.trezor.com", target_arch=TARGET_ARCH_ARMV8M
        ),
    }

    work = tmp_path_factory.mktemp("extapp")
    apps_dir = work / "apps"
    apps_dir.mkdir()
    for name, image in variants.items():
        (apps_dir / f"{name}.tapp").write_bytes(image.build())

    out = work / "rp"
    _run_tool("build-rootpackets", *sorted(apps_dir.glob("*.tapp")), "-o", out)
    _run_tool("timestamp", out / "rootpacket_0.tmr")
    _run_tool("sign", out / "rootpacket_0-timestamped.tmr")

    unsigned = (out / "rootpacket_0-timestamped.tmr").read_bytes()
    signed = (out / "rootpacket_0-timestamped-signed.tmr").read_bytes()

    apps: dict[str, AppFixture] = {}
    for name, image in variants.items():
        # build-rootpackets renames each app to its canonical {id}_{version}.tapp
        # and drops the proof next to it.
        version = ".".join(str(v) for v in image.header.version)
        stem = f"{image.header.id}_{version}"
        apps[name] = AppFixture(
            image=image,
            binary=(out / f"{stem}.tapp").read_bytes(),
            proof=(out / f"{stem}.proof").read_bytes(),
        )

    return ExtappFixtures(
        apps=apps,
        root_packet=signed,
        root_packet_unsigned=unsigned,
        root_packet_timestamp=RootPacket.parse(signed).auth.timestamp,
    )


def drive_load(
    session: Session,
    app: AppFixture,
    *,
    root_packet: bytes,
    root_packet_timestamp: int,
    load_id: str | None = None,
    load_version: tuple[int, int, int, int] | None = None,
    fingerprint: bytes = b"",
    header: bytes | None = None,
    proof: bytes | None = None,
    chunk_override: t.Callable[[int, bytes, bytes], tuple[bytes, bytes]] | None = None,
) -> tuple[t.Any, list[messages.MessageType]]:
    """Drive ExtAppLoad by hand so individual fields can be perturbed.

    Mirrors ``trezorlib.extapp.load`` but lets a test override exactly one thing.
    Returns the final response plus every request the device made, so tests can
    assert on the protocol shape (e.g. that the root packet was *not* requested).
    """
    image = app.image
    seen: list[messages.MessageType] = []

    major, minor, patch, build = load_version or image.header.version
    resp = session.call(
        messages.ExtAppLoad(
            fingerprint=fingerprint,
            id=image.header.id if load_id is None else load_id,
            version=messages.Version(
                major=major, minor=minor, patch=patch, build=build
            ),
        )
    )

    chunks: list[tuple[bytes, bytes]] | None = None

    while True:
        seen.append(resp)

        if isinstance(resp, messages.ExtAppHeaderRequest):
            resp = session.call(
                messages.ExtAppHeaderAck(
                    header=image.header_bytes() if header is None else header,
                    proof=app.proof if proof is None else proof,
                    root_packet_timestamp=root_packet_timestamp,
                )
            )
        elif isinstance(resp, messages.ExtAppRootPacketRequest):
            resp = session.call(messages.ExtAppRootPacketAck(root_packet=root_packet))
        elif isinstance(resp, messages.ExtAppDataChunkRequest):
            if chunks is None:
                chunks = image.chunks()
            data, chunk_hash = chunks[resp.index]
            if chunk_override is not None:
                data, chunk_hash = chunk_override(resp.index, data, chunk_hash)
            resp = session.call(messages.ExtAppDataChunkAck(data=data, hash=chunk_hash))
        else:
            return resp, seen
