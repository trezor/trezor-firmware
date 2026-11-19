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

import json
import secrets
from hashlib import sha256
from pathlib import Path

import keyring
import pytest
from cryptography.hazmat.primitives.asymmetric import x25519
from keyring.errors import PasswordDeleteError

from trezorlib.cli.credentials import (
    KEY_CREDENTIAL,
    KEY_HOST_PRIVKEY,
    KEY_TREZOR_PUBKEY,
    CredentialStore,
)
from trezorlib.thp.credentials import StaticCredential, TrezorPublicKeys

APP = "trezorctl"
ALL_KEYS = (KEY_TREZOR_PUBKEY, KEY_HOST_PRIVKEY, KEY_CREDENTIAL)

Passwords = dict[tuple[str, str], str]


@pytest.fixture
def passwords(monkeypatch: pytest.MonkeyPatch) -> Passwords:
    passwords: Passwords = {}

    def set_password(service: str, username: str, password: str) -> None:
        passwords[service, username] = password

    def delete_password(service: str, username: str) -> None:
        if passwords.pop((service, username), None) is None:
            raise PasswordDeleteError(service)

    monkeypatch.setattr(keyring, "get_password", lambda s, u: passwords.get((s, u)))
    monkeypatch.setattr(keyring, "set_password", set_password)
    monkeypatch.setattr(keyring, "delete_password", delete_password)
    return passwords


def make_credential() -> StaticCredential:
    trezor_privkey = x25519.X25519PrivateKey.generate()
    return StaticCredential(
        trezor_pubkey=trezor_privkey.public_key().public_bytes_raw(),
        host_privkey=secrets.token_bytes(32),
        credential=secrets.token_bytes(64),
    )


def public_keys_for(credential: StaticCredential) -> TrezorPublicKeys:
    ephemeral = secrets.token_bytes(32)
    mask = sha256(credential.trezor_pubkey + ephemeral).digest()
    static_masked = x25519.X25519PrivateKey.from_private_bytes(mask).exchange(
        x25519.X25519PublicKey.from_public_bytes(credential.trezor_pubkey)
    )
    return TrezorPublicKeys(ephemeral=ephemeral, static_masked=static_masked)


def stored_ids(store: CredentialStore) -> list[str]:
    return json.loads(store.config_path.read_text()).get(APP, [])


def setup_store(
    passwords: Passwords, path: Path, removed_keys: tuple[str, ...]
) -> tuple[CredentialStore, StaticCredential, str]:
    store = CredentialStore(APP, config_file=path / "thp-credentials.json")
    store.add(make_credential())
    valid = make_credential()
    store.add(valid)

    # simulate removing the first credential via the OS keyring manager
    stale_id = stored_ids(store)[0]
    for key in removed_keys:
        del passwords[f"{APP}/thp-credentials/{key}", stale_id]
    return store, valid, stale_id


@pytest.mark.parametrize("removed_keys", [ALL_KEYS, (KEY_CREDENTIAL,)])
def test_list_forgets_missing(
    passwords: Passwords, tmp_path: Path, removed_keys: tuple[str, ...]
) -> None:
    store, valid, stale_id = setup_store(passwords, tmp_path, removed_keys)

    assert [c.trezor_pubkey for c in store.list()] == [valid.trezor_pubkey]
    assert stale_id not in stored_ids(store)
    assert all(username != stale_id for _, username in passwords)


def test_delete_with_missing(passwords: Passwords, tmp_path: Path) -> None:
    store, valid, _ = setup_store(passwords, tmp_path, ALL_KEYS)

    assert public_keys_for(valid) in store
    store.delete(public_keys_for(valid))
    assert not passwords
    assert stored_ids(store) == []
