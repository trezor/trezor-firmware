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
import typing as t
from functools import cached_property
from pathlib import Path

import keyring
import platformdirs
from typing_extensions import Self

from ..thp.credentials import Credential

LOG = logging.getLogger(__name__)


class KeyringCredential:
    def __init__(self, app_name: str, trezor_pubkey: bytes) -> None:
        self.app_name = app_name
        self.trezor_pubkey = trezor_pubkey

    @property
    def _system(self) -> str:
        return f"{self.app_name}/thp-credentials"

    @property
    def _system_privkey(self) -> str:
        return self._system + "/privkey"

    @property
    def _system_credential(self) -> str:
        return self._system + "/credential"

    @cached_property
    def _username(self) -> str:
        return base64.b64encode(self.trezor_pubkey).decode()

    @cached_property
    def host_privkey(self) -> bytes:
        privkey_b64 = keyring.get_password(self._system_privkey, self._username)
        if privkey_b64 is None:
            raise ValueError("Private key not found")
        return base64.b64decode(privkey_b64)

    @cached_property
    def credential(self) -> bytes:
        credential_b64 = keyring.get_password(self._system_credential, self._username)
        if credential_b64 is None:
            raise ValueError("Credential not found")
        return base64.b64decode(credential_b64)

    @classmethod
    def save(cls, app_name: str, credential: Credential) -> Self:
        new = cls(app_name, credential.trezor_pubkey)
        new.host_privkey = credential.host_privkey
        new.credential = credential.credential
        keyring.set_password(
            new._system_privkey,
            new._username,
            base64.b64encode(new.host_privkey).decode(),
        )
        keyring.set_password(
            new._system_credential,
            new._username,
            base64.b64encode(new.credential).decode(),
        )
        return new

    def delete(self) -> None:
        try:
            keyring.delete_password(self._system_privkey, self._username)
        except Exception:
            pass
        try:
            keyring.delete_password(self._system_credential, self._username)
        except Exception:
            pass

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

    def _load(self) -> dict[str, t.Any]:
        if not self.config_path.exists():
            return {}
        return json.loads(self.config_path.read_text())

    def _save(self, data: dict[str, t.Any]) -> None:
        self.config_path.write_text(json.dumps(data, indent=2) + "\n")

    def list(self) -> t.Collection[Credential]:
        data = self._load()
        app_data = data.get(self.app_name, ())
        return [
            KeyringCredential(
                self.app_name, base64.b64decode(credential)
            ).as_credential()
            for credential in app_data
        ]

    def add(self, credential: Credential) -> None:
        data = self._load()
        app_data = data.setdefault(self.app_name, [])
        saved_credential = KeyringCredential.save(self.app_name, credential)
        app_data.append(saved_credential._username)
        self._save(data)
        LOG.info(
            "Added credential for %s: %s", self.app_name, credential.trezor_pubkey.hex()
        )

    def delete(self, trezor_pubkey: bytes) -> None:
        data = self._load()
        app_data = data.setdefault(self.app_name, [])
        credential = KeyringCredential(self.app_name, trezor_pubkey)
        app_data.remove(credential._username)
        credential.delete()
        self._save(data)
