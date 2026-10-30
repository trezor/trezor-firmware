#!/usr/bin/env python3

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

import click
from embit.descriptor import Key

from trezorlib import btc, client, messages

NAME = "signer"


@click.command()
@click.option("-c", "--coin", type=str)
@click.option("-n", "--name", type=str)
@click.option("-d", "--descriptor", type=str)
@click.option("-k", "--key", type=str, multiple=True, required=True)
def register_policy(
    coin: str, name: str, descriptor: str, key: tuple[str, ...]
) -> None:
    session = client.get_default_session(
        client.get_default_client(NAME, path_or_transport="udp")
    )

    btc.register_policy(
        session,
        coin_name=coin,
        name=name,
        descriptor=descriptor,
        keys=[
            messages.MiniscriptKey(
                node=messages.HDNodeType(
                    depth=k.key.depth,
                    fingerprint=int.from_bytes(k.key.fingerprint, "big"),
                    child_num=k.key.child_number,
                    chain_code=k.key.chain_code,
                    public_key=k.get_public_key().serialize(),
                ),
                root_fingerprint=int.from_bytes(k.fingerprint, "big"),
                derivation_path=k.derivation,
            )
            for k in map(Key.from_string, key)
        ],
    )


if __name__ == "__main__":
    register_policy()
