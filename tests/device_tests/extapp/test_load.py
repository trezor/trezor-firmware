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

"""Device tests for the ExtAppLoad flow (core/src/apps/extapp/load.py).

Requires an emulator built with app loading enabled:

    xtask build firmware --emulator -m t3w1 --apps --debug-link

Without ``--apps`` the handler is not registered at all (workflow_handlers.py
gates it on ``utils.USE_APP_LOADING``) and every test here fails with
"Unexpected message".

``ExtAppMessage`` is not covered: ``apps/extapp/run.py`` is still a stub that
raises ``DataError("Not implemented")``.
"""

from __future__ import annotations

import pytest

from trezorlib import messages
from trezorlib.debuglink import DebugSession as Session
from trezorlib.exceptions import TrezorFailure

from .conftest import drive_load

pytestmark = [
    pytest.mark.extapp,
    pytest.mark.emulator,
    pytest.mark.models("t3w1"),
]


@pytest.fixture
def load(session: Session, extapp_fixtures):
    """drive_load bound to this session and the signed root packet.

    Pass ``cold=True`` when a test needs the app *not* to be already resident.
    The app arena lives in RAM and is not cleared by ``wipe_device``, so an image
    loaded by an earlier test survives into the next one; without this, any test
    that expects a header/chunk exchange silently takes the reuse path instead
    and asserts nothing. See ``_evict`` for how the image is dropped.
    """

    def _evict() -> None:
        """Drop the resident image without disturbing the stored root packet.

        Asking for an id nothing matches makes load.py delete the cached image
        (load.py:111-113) before it starts the upload; feeding it a bad header
        then aborts the flow at app_ring_from_header, which is *before* the root
        packet would be requested and stored. Evicting by loading a real app
        instead would persist a valid root packet and break the tests that need
        to see ExtAppRootPacketRequest.
        """
        header = bytearray(extapp_fixtures["valid"].image.header_bytes())
        header[0:4] = b"XXXX"
        with pytest.raises(TrezorFailure):
            drive_load(
                session,
                extapp_fixtures["valid"],
                root_packet=extapp_fixtures.root_packet,
                root_packet_timestamp=extapp_fixtures.root_packet_timestamp,
                load_id="evict.invalid",
                header=bytes(header),
            )

    def _load(app_name: str, *, cold: bool = False, force_root: bool = False, **kwargs):
        if cold:
            _evict()

        timestamp = kwargs.pop(
            "root_packet_timestamp", extapp_fixtures.root_packet_timestamp
        )
        if force_root:
            # The device only asks for a root packet when the timestamp the host
            # claims differs from the one it holds (load.py:57). That state lives
            # in RAM as well as storage, so it survives wipe_device and the very
            # first load in an emulator run is otherwise the only one that ever
            # sees ExtAppRootPacketRequest. Claiming a different timestamp makes
            # the fetch happen regardless of test order; the value is only used
            # for the comparison, never stored (the packet carries its own).
            timestamp += 1

        return drive_load(
            session,
            extapp_fixtures[app_name],
            root_packet=kwargs.pop("root_packet", extapp_fixtures.root_packet),
            root_packet_timestamp=timestamp,
            **kwargs,
        )

    return _load


def _requests(seen: list) -> list[type]:
    return [type(m) for m in seen]


# ---------------------------------------------------------------------------
# A. Happy path / protocol shape
# ---------------------------------------------------------------------------


def test_load_valid_app(load):
    """A1: a well-formed app loads and yields an instance id."""
    resp, _ = load("valid")
    assert isinstance(resp, messages.ExtAppLoaded)
    assert resp.instance_id is not None


def test_request_sequence(load):
    """A2: header first, then the root packet, then chunks, then loaded."""
    resp, seen = load("valid", cold=True, force_root=True)
    assert isinstance(resp, messages.ExtAppLoaded)

    kinds = _requests(seen)
    assert kinds[0] is messages.ExtAppHeaderRequest
    assert messages.ExtAppRootPacketRequest in kinds
    assert kinds[-1] is messages.ExtAppLoaded
    assert kinds.count(messages.ExtAppDataChunkRequest) >= 1


def test_chunk_indices_are_sequential(load, extapp_fixtures):
    """A3: the device walks chunk indices 0..N-1 exactly once each."""
    resp, seen = load("multichunk", cold=True)
    assert isinstance(resp, messages.ExtAppLoaded)

    indices = [m.index for m in seen if isinstance(m, messages.ExtAppDataChunkRequest)]
    expected = len(extapp_fixtures["multichunk"].chunks())
    assert indices == list(range(expected))


def test_exact_fingerprint_accepted(load, extapp_fixtures):
    """A5: pinning the exact fingerprint still loads."""
    resp, _ = load("valid", fingerprint=extapp_fixtures["valid"].image.fingerprint())
    assert isinstance(resp, messages.ExtAppLoaded)


def test_lower_requested_version_accepted(load):
    """A6: the check is image.version() < requested, so asking for less is fine."""
    resp, _ = load("valid", load_version=(0, 1, 0, 0))
    assert isinstance(resp, messages.ExtAppLoaded)


# ---------------------------------------------------------------------------
# B. Load-time rejection
# ---------------------------------------------------------------------------


def test_app_id_mismatch(load):
    """B1: the host asked for a different app than the header describes."""
    with pytest.raises(TrezorFailure, match="Loaded image does not match"):
        load("valid", load_id="somethingelse.trezor.com")


def test_requested_version_too_high(load):
    """B2: requesting a newer version than the image provides."""
    with pytest.raises(TrezorFailure, match="Loaded image does not match"):
        load("valid", load_version=(9, 0, 0, 0))


def test_fingerprint_mismatch(load, extapp_fixtures):
    """B3: a pinned fingerprint that does not match the delivered header."""
    fp = bytearray(extapp_fixtures["valid"].image.fingerprint())
    fp[0] ^= 0xFF
    with pytest.raises(TrezorFailure, match="Loaded image does not match"):
        load("valid", fingerprint=bytes(fp))


def test_corrupted_chunk_hash(load):
    """B4: the declared next-chunk hash is wrong -> chain verification fails."""

    def corrupt(index, data, chunk_hash):
        return (data, b"\x00" * 32) if index == 0 else (data, chunk_hash)

    with pytest.raises(TrezorFailure, match="App image verification failed"):
        load("multichunk", cold=True, chunk_override=corrupt)


def test_corrupted_chunk_data(load):
    """B5: payload byte flipped while keeping the declared hash."""

    def corrupt(index, data, chunk_hash):
        if index != 0:
            return data, chunk_hash
        mutated = bytearray(data)
        mutated[0] ^= 0xFF
        return bytes(mutated), chunk_hash

    with pytest.raises(TrezorFailure, match="App image verification failed"):
        load("multichunk", cold=True, chunk_override=corrupt)


def test_corrupted_proof(load, extapp_fixtures):
    """B6: Merkle proof no longer resolves to the root in the root packet."""
    proof = bytearray(extapp_fixtures["valid"].proof)
    proof[0] ^= 0xFF
    with pytest.raises(TrezorFailure, match="App image verification failed"):
        load("valid", cold=True, proof=bytes(proof))


def test_bad_header_magic(load, extapp_fixtures):
    """B9: header fails app_header_verify before anything else happens."""
    header = bytearray(extapp_fixtures["valid"].image.header_bytes())
    header[0:4] = b"XXXX"
    with pytest.raises(TrezorFailure, match="Failed to load app"):
        load("valid", cold=True, header=bytes(header))


def test_wrong_target_arch(load):
    """B8: an ARM payload is rejected by the unix loader on the final chunk."""
    with pytest.raises(TrezorFailure, match="App image verification failed"):
        load("wrong_arch", cold=True)


# ---------------------------------------------------------------------------
# C. Root packet / trust chain
# ---------------------------------------------------------------------------


def test_root_packet_requested_when_timestamp_differs(load):
    """C2: a timestamp the device does not have forces a root packet fetch."""
    _, seen = load("valid", cold=True, force_root=True)
    assert messages.ExtAppRootPacketRequest in _requests(seen)


def test_root_packet_skipped_when_already_current(load):
    """C1: once the root packet is stored, the device stops asking for it."""
    resp, _ = load("valid", cold=True)
    assert isinstance(resp, messages.ExtAppLoaded)

    # Second load of a *different* app: the image cache cannot satisfy it, so
    # the header flow runs again -- but the root packet is already current.
    resp, seen = load("other")
    assert isinstance(resp, messages.ExtAppLoaded)
    assert messages.ExtAppRootPacketRequest not in _requests(seen)


def test_unsigned_root_packet_rejected(load, extapp_fixtures):
    """C3: the unsigned packet must not be accepted."""
    with pytest.raises(TrezorFailure, match="Failed to load app"):
        load(
            "valid",
            cold=True,
            force_root=True,
            root_packet=extapp_fixtures.root_packet_unsigned,
        )


def test_garbage_root_packet_rejected(load):
    """C4: a structurally invalid packet is rejected."""
    with pytest.raises(TrezorFailure, match="Failed to load app"):
        load("valid", cold=True, force_root=True, root_packet=b"\x00" * 128)


# ---------------------------------------------------------------------------
# D. Truncation
# ---------------------------------------------------------------------------


def test_truncated_image(load):
    """D1: every chunk verifies but the payload never reaches code_size."""
    with pytest.raises(TrezorFailure, match="App image truncated"):
        load("truncated", cold=True)


def test_image_deleted_after_failure(load):
    """D2: a failed load leaves nothing cached -- the next load runs in full."""
    with pytest.raises(TrezorFailure):
        load("valid", cold=True, proof=b"\x00" * 32)

    resp, seen = load("valid")
    assert isinstance(resp, messages.ExtAppLoaded)
    assert messages.ExtAppHeaderRequest in _requests(seen)


# ---------------------------------------------------------------------------
# E. Reuse / caching
# ---------------------------------------------------------------------------


def test_second_load_reuses_cached_image(load):
    """E1: loading the same app again skips the whole upload."""
    resp, _ = load("valid", cold=True)
    assert isinstance(resp, messages.ExtAppLoaded)

    resp, seen = load("valid")
    assert isinstance(resp, messages.ExtAppLoaded)
    assert messages.ExtAppHeaderRequest not in _requests(seen)
    assert messages.ExtAppDataChunkRequest not in _requests(seen)


def test_reload_yields_new_instance_id(load):
    """E2: each load mints a fresh instance id."""
    first, _ = load("valid", cold=True)
    second, _ = load("valid")
    assert first.instance_id != second.instance_id


def test_loading_other_app_evicts_the_first(load):
    """E3: only one image is resident, so app B forces a full reload."""
    resp, _ = load("valid", cold=True)
    assert isinstance(resp, messages.ExtAppLoaded)

    resp, seen = load("other")
    assert isinstance(resp, messages.ExtAppLoaded)
    assert messages.ExtAppHeaderRequest in _requests(seen)

    # ...and going back to the first app has to upload it again.
    resp, seen = load("valid")
    assert isinstance(resp, messages.ExtAppLoaded)
    assert messages.ExtAppHeaderRequest in _requests(seen)


# ---------------------------------------------------------------------------
# F. Known gaps -- these pin current behaviour and flip when fixed
# ---------------------------------------------------------------------------


@pytest.mark.xfail(
    reason="load.py:81 divides by header chunk_size, which app_header_verify "
    "never validates -> ZeroDivisionError instead of a clean DataError",
    strict=True,
)
def test_zero_chunk_size_is_reported_cleanly(load):
    """F2: chunk_size == 0 should fail as a DataError, not an internal error."""
    with pytest.raises(TrezorFailure, match="Failed to load app"):
        load("zero_chunk", cold=True)


@pytest.mark.xfail(
    reason="modtrezorapp-image.h:289 raises a bare ValueError that load.py's "
    "handlers do not convert to DataError",
    strict=True,
)
def test_short_chunk_hash_is_reported_cleanly(load):
    """F3: a malformed hash length should surface as a DataError."""

    def short_hash(index, data, chunk_hash):
        return data, b"\x00" * 31

    with pytest.raises(TrezorFailure, match="App image verification failed"):
        load("valid", cold=True, chunk_override=short_hash)
