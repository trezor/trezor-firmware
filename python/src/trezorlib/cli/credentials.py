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

import base64
import json
import logging
import secrets
import typing as t
from contextlib import contextmanager
from functools import cached_property
from pathlib import Path

import keyring
import platformdirs
from typing_extensions import Self

from ..thp.credentials import Credential, TrezorPublicKeys, matches

LOG = logging.getLogger(__name__)

KEY_TREZOR_PUBKEY = "trezor-pubkey"
KEY_HOST_PRIVKEY = "host-privkey"
KEY_CREDENTIAL = "credential"


class KeyringCredential:
    def __init__(self, app_name: str, id: bytes) -> None:
        self.id = id
        self.app_name = app_name

    def _key(self, key: str) -> str:
        return f"{self.app_name}/thp-credentials/{key}"

    @cached_property
    def _username(self) -> str:
        return base64.b64encode(self.id).decode()

    def _load_from_keyring(self, key: str) -> bytes:
        keyring_key = self._key(key)
        value_b64 = keyring.get_password(keyring_key, self._username)
        if value_b64 is None:
            raise ValueError(f"Not found in keyring: {keyring_key}")
        return base64.b64decode(value_b64)

    def _save_to_keyring(self, key: str, value: bytes) -> None:
        keyring_key = self._key(key)
        value_b64 = base64.b64encode(value).decode()
        keyring.set_password(keyring_key, self._username, value_b64)

    def _delete_from_keyring(self, key: str) -> None:
        keyring_key = self._key(key)
        try:
            keyring.delete_password(keyring_key, self._username)
        except Exception as e:
            LOG.warning("Failed to delete %s from keyring: %s", keyring_key, e)

    @cached_property
    def trezor_pubkey(self) -> bytes:
        return self._load_from_keyring(KEY_TREZOR_PUBKEY)

    @cached_property
    def host_privkey(self) -> bytes:
        return self._load_from_keyring(KEY_HOST_PRIVKEY)

    @cached_property
    def credential(self) -> bytes:
        return self._load_from_keyring(KEY_CREDENTIAL)

    @classmethod
    def save(cls, app_name: str, credential: Credential) -> Self:
        new_id = base64.b64encode(secrets.token_bytes(16))
        new = cls(app_name, new_id)
        new.trezor_pubkey = credential.trezor_pubkey
        new.host_privkey = credential.host_privkey
        new.credential = credential.credential
        new._save_to_keyring(KEY_TREZOR_PUBKEY, credential.trezor_pubkey)
        new._save_to_keyring(KEY_HOST_PRIVKEY, credential.host_privkey)
        new._save_to_keyring(KEY_CREDENTIAL, credential.credential)
        LOG.info("Saved credential %s for %s", new.id.hex(), new.app_name)
        return new

    def delete(self) -> None:
        self._delete_from_keyring(KEY_TREZOR_PUBKEY)
        self._delete_from_keyring(KEY_HOST_PRIVKEY)
        self._delete_from_keyring(KEY_CREDENTIAL)
        LOG.info("Deleted credential %s for %s", self.id.hex(), self.app_name)

    def as_credential(self) -> Credential:
        # limitation of pyright:
        # https://github.com/microsoft/pyright/issues/10252
        # at runtime, KeyringCredential does conform to Credential, but this
        # can't be cleanly expressed via the type system.
        return self  # type: ignore ["cached_property[bytes]" is not assignable to "bytes"]


class CredentialStore:
    def __init__(
        self,
        app_name: str,
        config_file: Path | None = None,
        config_appname: str = "trezorctl",
    ) -> None:
        self.app_name = app_name
        if config_file is not None:
            self.config_path = config_file
        else:
            config_dir = Path(
                platformdirs.user_config_dir(config_appname, ensure_exists=True)
            )
            self.config_path = config_dir / "thp-credentials.json"

    @contextmanager
    def _with_app(self) -> t.Generator[list[bytes], None, None]:
        data = self._load()
        app_data_b64 = data.get(self.app_name, ())
        app_data = [base64.b64decode(id) for id in app_data_b64]
        original = app_data[:]
        yield app_data
        if original != app_data:
            modified_b64 = [base64.b64encode(id).decode() for id in app_data]
            if modified_b64:
                data[self.app_name] = modified_b64
            else:
                data.pop(self.app_name, None)
            self._save(data)

    def _load(self) -> dict[str, t.Any]:
        if not self.config_path.exists():
            return {}
        return json.loads(self.config_path.read_text())

    def _save(self, data: dict[str, t.Any]) -> None:
        self.config_path.write_text(json.dumps(data, indent=2) + "\n")

    def list(self) -> t.Collection[Credential]:
        with self._with_app() as app_data:
            return [
                KeyringCredential(self.app_name, id).as_credential() for id in app_data
            ]

    def add(self, credential: Credential) -> None:
        with self._with_app() as app_data:
            saved_credential = KeyringCredential.save(self.app_name, credential)
            app_data.append(saved_credential.id)

    def _get(
        self, app_data: list[bytes], id_or_key: bytes | TrezorPublicKeys
    ) -> KeyringCredential | None:
        if isinstance(id_or_key, bytes):
            if id_or_key in app_data:
                # found by the unique identifier
                return KeyringCredential(self.app_name, id_or_key)
        for id in app_data:
            credential = KeyringCredential(self.app_name, id)
            if isinstance(id_or_key, TrezorPublicKeys) and matches(
                credential.as_credential(), id_or_key
            ):
                # found by matching TrezorPublicKeys
                return credential
            if id_or_key == credential.trezor_pubkey:
                # found by Trezor public key
                return credential
        return None

    def __getitem__(self, id_or_key: bytes | TrezorPublicKeys) -> KeyringCredential:
        with self._with_app() as app_data:
            credential = self._get(app_data, id_or_key)
            if credential is not None:
                return credential
            raise KeyError(f"Credential not found: {id_or_key}")

    def __contains__(self, id_or_key: bytes | TrezorPublicKeys) -> bool:
        with self._with_app() as app_data:
            return self._get(app_data, id_or_key) is not None

    def delete(self, id_or_key: bytes | TrezorPublicKeys) -> None:
        with self._with_app() as app_data:
            credential = self._get(app_data, id_or_key)
            if credential is None:
                LOG.warning("Credential not found: %s", id_or_key)
            else:
                credential.delete()
                app_data.remove(credential.id)

    def clear(self) -> None:
        with self._with_app() as app_data:
            for id in app_data:
                credential = KeyringCredential(self.app_name, id)
                credential.delete()
            app_data.clear()
