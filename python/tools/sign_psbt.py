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

from pathlib import Path

import click
from embit.descriptor import Descriptor
from embit.networks import NETWORKS
from embit.psbt import PSBT

from trezorlib import btc, client, messages
from trezorlib.cli.btc import xpub_deserialize

NAME = "signer"


@click.command()
@click.option(
    "-d",
    "--descriptor",
    type=str,
    help="BIP-388 template policy (xpubs separated by newlines)",
)
@click.option("-i", "--input", "src", type=click.Path(exists=True, dir_okay=False))
@click.option("-o", "--output", "dst", type=click.Path(writable=True, dir_okay=False))
@click.option("--coin", type=str)
@click.option("--spend", type=int)
def sign_psbt(descriptor: str, src: str, dst: str, coin: str, spend: int) -> None:
    network = NETWORKS[coin]
    descriptor, *xpubs = descriptor.split("\n")
    nodes = [xpub_deserialize(x.split("]")[1])[1] for x in xpubs]
    policy = messages.MiniscriptPolicy(descriptor=descriptor, nodes=nodes)
    desc = descriptor
    for i, xpub in enumerate(xpubs):
        desc = desc.replace(f"@{i}", xpub)

    desc = Descriptor.from_string(desc)
    print("Policy:", desc)

    psbt = PSBT.from_base64(Path(src).read_text())
    assert all(desc.owns(i) for i in psbt.inputs)

    session = client.get_default_session(
        client.get_default_client(NAME, path_or_transport="udp")
    )
    fpr: bytes = session.get_root_fingerprint()
    print(f"Fingerprint: {fpr.hex()}")

    keys = []
    for k in sorted(desc.keys, key=str):
        origin = k.origin
        if origin.fingerprint != fpr:
            continue
        node = btc.get_public_node(
            session, n=origin.derivation, coin_name=network["name"]
        )
        assert node.xpub == k.key.to_string()
        keys.append(k)

    key = keys[spend]
    print(key.to_string())

    inputs = []
    pubkeys = []
    for i in psbt.inputs:
        for pk, der in i.bip32_derivations.items():
            res = key.check_derivation(der)
            if res is not None:
                idx, branch_idx = res
                derived = key.derive(idx, branch_index=branch_idx)
                assert derived.key.key == pk
                pubkeys.append(pk)
                address_n = derived.origin.derivation
                redeem = messages.MiniscriptRedeemPolicyType(
                    policy=policy, internal=bool(branch_idx), index=idx
                )
                inputs.append(
                    messages.TxInputType(
                        address_n=address_n,
                        prev_hash=i.vin.txid,
                        prev_index=i.vin.vout,
                        script_type=messages.InputScriptType.SPENDWITNESS,
                        miniscript=redeem,
                        amount=i.utxo.value,
                        sequence=i.vin.sequence,
                    )
                )
                break
        else:
            raise ValueError
    outputs = [
        messages.TxOutputType(
            address=o.vout.script_pubkey.address(network),
            amount=o.vout.value,
            script_type=messages.OutputScriptType.PAYTOWITNESS,
        )
        for o in psbt.outputs
    ]
    signatures, _serialized = btc.sign_tx(
        session,
        coin_name=network["name"],
        version=psbt.tx_version,
        lock_time=psbt.locktime,
        inputs=inputs,
        outputs=outputs,
        serialize=False,
        prev_txes=prev_txs(psbt),
    )
    assert len(signatures) == len(psbt.inputs)
    assert len(signatures) == len(pubkeys)
    for i, pk, sig in zip(psbt.inputs, pubkeys, signatures):
        print(pk, sig.hex())
        i.partial_sigs[pk] = sig + b"\x01"  # SIGHASH_ALL

    Path(dst).write_text(psbt.to_base64())


def prev_txs(psbt: PSBT) -> dict[bytes, messages.TransactionType]:
    res = {}
    for i in psbt.inputs:
        if (prev := i.non_witness_utxo) is None:
            continue
        res[prev.txid()] = messages.TransactionType(
            version=prev.version,
            lock_time=prev.locktime,
            inputs=[
                messages.TxInputType(
                    prev_hash=vin.txid,
                    prev_index=vin.vout,
                    script_sig=vin.script_sig.data,
                    sequence=vin.sequence,
                )
                for vin in prev.vin
            ],
            bin_outputs=[
                messages.TxOutputBinType(
                    amount=vout.value, script_pubkey=vout.script_pubkey.data
                )
                for vout in prev.vout
            ],
        )
    return res


if __name__ == "__main__":
    sign_psbt()
