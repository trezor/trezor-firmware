# This file is part of the Trezor project.
#
# Copyright (C) 2012-2022 SatoshiLabs and contributors
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

import json
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import click

from databaselib.digest_patricia_merkle_trie import DigestPatriciaMerkleTrie
from databaselib.time import Time

from .. import database
from . import with_client

if TYPE_CHECKING:
    from ..client import TrezorClient


@click.group(name="database")
def cli() -> None:
    """Database commands."""


class Update:
    def __init__(self, time: Time, key: str, value: Optional[str], signature: bytes):
        self.time = time
        self.key = key
        self.value = value
        self.signature = signature

    def to_json(self) -> Any:
        return {
            "time": self.time.to_json(),
            "key": self.key,
            "value": self.value,
            "signature": self.signature.hex(),
        }

    @classmethod
    def from_json(cls, data: Any) -> "Update":
        return cls(
            Time.from_json(data["time"]),
            data["key"],
            data["value"],
            bytes.fromhex(data["signature"]),
        )


@dataclass
class LocalDatabase:
    identifier: bytes
    tree: DigestPatriciaMerkleTrie
    revision_number: int
    time: Time
    signature: bytes
    items: Dict[str, str]
    updates: List[Update]

    @classmethod
    def wipe(cls, client: "TrezorClient"):
        click.echo("Wiping the database.")

        response = database.wipe(client)

        return cls(
            response.identifier,
            DigestPatriciaMerkleTrie(),
            0,
            Time.zero(),
            response.signature,
            {},
            [],
        )

    def modify_key(
        self,
        client: "TrezorClient",
        key: str,
        value: Optional[str],
    ) -> None:
        old_value = self.items.get(key, None)

        if value is None and old_value is None:
            raise click.ClickException(f"The key '{key}' does not exist.")
        if value == old_value:
            click.echo(f"The key '{key}' already has the value '{value}'.")

        if value is None and old_value is not None:
            click.echo(f"Deleting the key '{key}' with the value '{old_value}'.")
        if value is not None and old_value is None:
            click.echo(f"Inserting the key '{key}' with the value '{value}'.")
        if value is not None and old_value is not None:
            click.echo(
                f"Changing the value of the '{key}' from '{old_value}' to '{value}'."
            )

        proof = self.tree.generate_modification_proof(key, value).to_bytes()
        response = database.modify_key(
            client,
            self.time.to_bytes(),
            self.signature,
            key,
            value,
            proof,
        )

        self.tree.modify(key, value)
        self.time.increment(self.identifier)
        self.revision_number += 1

        self.signature = response.database_signature
        self.items[key] = value

        update = Update(self.time.clone(), key, value, response.update_signature)
        self.updates.append(update)

    def prove_membership(self, client: "TrezorClient", key: str):
        proof, value = self.tree.generate_membership_proof(key)

        click.echo(f"Proving the key '{key}' has the value '{value}'.")

        database.prove_membership(
            client,
            self.time.to_bytes(),
            self.signature,
            key,
            proof.to_bytes(),
        )

    def merge(self, client: "TrezoClient", update_database: "LocalDatabase") -> None:
        for update in sorted(update_database.updates, key=lambda update: update.time):
            key = update.key
            value = update.value
            old_value = self.items.get(key, None)

            click.echo(f"Updating '{key}' from '{old_value}' to '{value}'.")

            proof = self.tree.generate_modification_proof(key, value)

            database_data = database.merge(
                client,
                self.time.to_bytes(),
                self.signature,
                key,
                value,
                proof.to_bytes(),
                update_database.identifier,
                update.time.to_bytes(),
                update.signature,
            )

            self.time.increment(update_database.identifier)
            self.signature = database_data.database_signature

            self.tree.modify(key, value)
            self.items[key] = value

            self.updates.append(update)

    def to_json(self) -> Any:
        return {
            "identifier": self.identifier.hex(),
            "tree": self.tree.to_json(),
            "revision_number": self.revision_number,
            "time": self.time.to_json(),
            "signature": self.signature.hex(),
            "items": self.items,
            "updates": [update.to_json() for update in self.updates],
        }

    @classmethod
    def from_json(cls, data: Any) -> "LocalDatabase":
        return cls(
            identifier=bytes.fromhex(data["identifier"]),
            tree=DigestPatriciaMerkleTrie.from_json(data["tree"]),
            revision_number=data["revision_number"],
            time=Time.from_json(data["time"]),
            signature=bytes.fromhex(data["signature"]),
            items=data["items"],
            updates=[Update.from_json(update) for update in data["updates"]],
        )

    def to_file(self, file_path: Path) -> bytes:
        json.dump(self.to_json(), file_path.open("w"))

    @staticmethod
    def from_file(file_path: Path) -> "LocalDatabase":
        return LocalDatabase.from_json(json.load(file_path.open("r")))


@cli.command()
@click.option("-d", "--database-file-path", type=Path, required=True)
@with_client
def wipe(client: "TrezorClient", database_file_path: Path) -> None:
    LocalDatabase.wipe(client).to_file(database_file_path)


@cli.command()
@click.option("-d", "--database-file-path", type=Path, required=True)
@click.option("-k", "--key", required=True)
@click.option("-v", "--value", required=True)
@with_client
def set_key(
    client: "TrezorClient", database_file_path: Path, key: str, value: str
) -> None:
    local_database = LocalDatabase.from_file(database_file_path)
    local_database.modify_key(client, key, value)
    local_database.to_file(database_file_path)


@cli.command()
@click.option("-d", "--database-file-path", type=Path, required=True)
@click.option("-k", "--key", required=True)
@with_client
def delete_key(
    client: "TrezorClient",
    database_file_path: Path,
    key: str,
) -> None:
    local_database = LocalDatabase.from_file(database_file_path)
    local_database.modify_key(client, key, None)
    local_database.to_file(database_file_path)


@cli.command()
@click.option("-d", "--database-file-path", type=Path, required=True)
@click.option("-k", "--key", required=True)
@with_client
def prove_membership(
    client: "TrezorClient",
    database_file_path: Path,
    key: str,
) -> None:
    local_database = LocalDatabase.from_file(database_file_path)
    local_database.prove_membership(client, key)


@cli.command()
@click.option("-d", "--database-file-path", type=Path, required=True)
@click.option("-u", "--update-file-path", type=Path, required=True)
@with_client
def merge(
    client: "TrezorClient", database_file_path: Path, update_file_path: Path
) -> None:

    local_database = LocalDatabase.from_file(database_file_path)
    update_database = LocalDatabase.from_file(update_file_path)
    local_database.merge(client, update_database)
    local_database.to_file(database_file_path)
