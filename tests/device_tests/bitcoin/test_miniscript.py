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

import pytest
from embit.bip32 import HDKey
from embit.networks import NETWORKS
from embit.psbt import PSBT

from trezorlib import btc, messages
from trezorlib.debuglink import DebugSession as Session
from trezorlib.tools import parse_path

from ...tx_cache import TxCache

TPUBS = [
    "tpubDCZB6sR48s4T5Cr8qHUYSZEFCQMMHRg8AoVKVmvcAP5bRw7ArDKeoNwKAJujV3xCPkBvXH5ejSgbgyN6kREmF7sMd41NdbuHa8n1DZNxSMg",
    "tpubDCNhwLKYSSu2FKssoMziAdwhAAKS3bASH7wZYkNmJ7sU5hW9LgDaAQPqe7ivAkskSF29B1CkRRg4g2mbovXgAL9Mby6i9xBdhZh2txDeSLb",
]

pytestmark = [
    pytest.mark.capabilities(messages.Capability.Miniscript),
    pytest.mark.experimental,
]

DATA = [
    (0, 0, "tb1qwr00r4x9a2ycm7fn48c7kqm6kpsp56ydwx482ns5c3wxmrwqwu2stjh6cc"),
    (0, 1, "tb1qzvr7ptes6kq2ee0745a7h2n639etfz43nsz9d2jn8u6wz8egx0hqnr5pza"),
    (0, 2, "tb1qerjma9tcyn6qh5yt7wdqqm3q8sz7ft6dn7pratjclzc8pha27rcsgjn0sp"),
    (0, 3, "tb1qc6zh83pdaj64tkmvu5969falc95s7sgs6yku5nh9asspzfmtq8cq7yxr2a"),
    (1, 0, "tb1q5f45hdwm06sf9wa20pcwa5rr9xn99m4yfpzdg406044nl9jhadps2ghwl5"),
    (1, 1, "tb1qk47jne78xqrzxwj5wc8l3qypneh96jumw56lkp50akhqpw5jmr6qwxdctf"),
    (1, 2, "tb1q68hg7scyjs20dndpdl7crr3kue0g8a5pkvktwlnwk4ygheazyfzqnhy9gm"),
]

VECTORS = (  # coin, path, script_type, address
    pytest.param(
        "Testnet",
        "wsh(or_d(pk({0}/<0;1>/*),and_v(v:pkh({1}/<0;1>/*),older(1))))".format(*TPUBS),
        [change, index],
        address,
        id=f"Liana-{'internal' if change else 'external'}-{index}",
    )
    for change, index, address in DATA
)


@pytest.mark.parametrize("coin, desc, n, address", VECTORS)
def test_miniscript_get_address(
    session: Session,
    coin: str,
    desc: str,
    n: list[int],
    address: str,
):
    reg = messages.MiniscriptRegisterPolicy(
        name="Policy name",
        policy=messages.MiniscriptPolicy(descriptor=desc),
        coin_name=coin,
    )
    session.call(msg=reg, expect=messages.Success)
    assert (
        btc.get_address(
            session,
            coin,
            n=n,
            policy=reg.policy,
        )
        == address
    )


TX_CACHE_SIGNET = TxCache("Signet")


def test_miniscript_spend(session: Session):
    TPUBS = [
        # ALL x 12 [5c9e228d/84'/1'/0']
        "tpubDCZB6sR48s4T5Cr8qHUYSZEFCQMMHRg8AoVKVmvcAP5bRw7ArDKeoNwKAJujV3xCPkBvXH5ejSgbgyN6kREmF7sMd41NdbuHa8n1DZNxSMg",
        # GYM x 12 [72758bc3/84'/1'/0']
        "tpubDCNhwLKYSSu2FKssoMziAdwhAAKS3bASH7wZYkNmJ7sU5hW9LgDaAQPqe7ivAkskSF29B1CkRRg4g2mbovXgAL9Mby6i9xBdhZh2txDeSLb",
    ]

    # 1st always, or 2nd after 1 block
    DESC = "wsh(or_d(pk({0}/<0;1>/*),and_v(v:pkh({1}/<0;1>/*),older(1))))".format(
        *TPUBS
    )
    COIN = "Testnet"

    node = btc.get_public_node(session, parse_path("m/84h/1h/0h"), coin_name=COIN)
    assert node.xpub == TPUBS[0]

    reg = messages.MiniscriptRegisterPolicy(
        name="Policy name",
        policy=messages.MiniscriptPolicy(descriptor=DESC),
        coin_name=COIN,
    )
    session.call(msg=reg, expect=messages.Success)
    addr = btc.get_address(session, n=[0, 2], policy=reg.policy, coin_name=COIN)
    assert addr == "tb1qerjma9tcyn6qh5yt7wdqqm3q8sz7ft6dn7pratjclzc8pha27rcsgjn0sp"

    psbt = PSBT.from_base64(
        "cHNidP8BAFIBAAAAAUkJUMjTkYQIJv7vwcQ11hytuDR1OWbAZquJE8uU8ZRWAQAAAAD/////ASgjAAAAAAAAFgAU+cEmDinRJSC3+18cyUxT604zeTYAAAAAAAEA/X4BAgAAAAABAs97FfR7YmrQgT60XxgweHVUVWN3kbXvx389VFuhSomfAAAAAAD9////mfy9e2lkaxldpZhLS2RCtaoyCXJoUm35pM/CGqPgvMEAAAAAAP3///8CsB0AAAAAAAAWABTUUK+8fPAsy9+ngGznvlwYhnu6BhAnAAAAAAAAIgAgyOW+lXgk9AvQi/OaAG4gPAXkr02fgj6uWPiwcN+q8PECRzBEAiAgRlDdAl6Mwfm7YWsZhNr7bkbOh+BZeqfHo+/Y2BYFpgIgEjEaWU6zIRaeHWk72udpjuC84neQgC60U2uHd8UPjLABIQKjNseUzXuUV7pYCAx8bJA7thu3YD+k8vbWbQ0ns06ssQJHMEQCIBPfXQ4Nkvgxxwo0iWvRKa/XRfHlZBPBL1qhZG/+kT09AiAAnZQoXLA4ME+uirBmtDUQFqlE7ET45+R6AZivgO4BwAEhAktl+El745lSZBje9Ef7wtgcZWFaFGCki/VwTzLq9xkpgKEEAAEBKxAnAAAAAAAAIgAgyOW+lXgk9AvQi/OaAG4gPAXkr02fgj6uWPiwcN+q8PEBBUEhA1fLOlkY0V0iTxSonw61RHgnIQj2y7nEc8FWXlUmD26TrHNkdqkU6/nOb5BT8jwuQFNXaRTZ4jjvnwWIrVGyaCIGAm1hwe6Gs0eHzElWWP2v/VtTYLEBUWvEyGTQTLbjI1BSGHJ1i8NUAACAAQAAgAAAAIAAAAAAAgAAACIGA1fLOlkY0V0iTxSonw61RHgnIQj2y7nEc8FWXlUmD26TGFyeIo1UAACAAQAAgAAAAIAAAAAAAgAAAAAA"
    )
    pubkey = HDKey.from_string(node.xpub).derive("m/0/2").key
    inputs = [
        messages.TxInputType(
            address_n=i.bip32_derivations[pubkey].derivation,
            prev_hash=i.vin.txid,
            prev_index=i.vin.vout,
            script_type=messages.InputScriptType.SPENDWITNESS,
            policy=reg.policy,
            amount=i.utxo.value,
            sequence=i.vin.sequence,
        )
        for i in psbt.inputs
    ]
    outputs = [
        messages.TxOutputType(
            address=o.vout.script_pubkey.address(NETWORKS["test"]),
            amount=o.vout.value,
            script_type=messages.OutputScriptType.PAYTOWITNESS,
        )
        for o in psbt.outputs
    ]

    signatures, _serialized = btc.sign_tx(
        session,
        COIN,
        inputs,
        outputs,
        version=psbt.tx_version,
        lock_time=psbt.locktime,
        serialize=False,
        prev_txes=TX_CACHE_SIGNET,
    )

    assert (
        signatures[0].hex()
        == "3045022100e97a3e8284019dcc8eb91cd0bdf8df03dabc1dc55af9af1de4e01b7b7bdc793302204946f21cd7d3d47c5f4f543ce4936187c53eeafc113a2f1cfa72abd0509670ca"
    )

    # f359d5889cdce6aae9ca65d838d30250f3435cf697fb9393a8fe92597f67aad8 on signet (height=303507)
    # assert (
    #     serialized.hex()
    #     == "01000000000101490950c8d391840826feefc1c435d61cadb834753966c066ab8913cb94f194560100000000ffffffff012823000000000000160014f9c1260e29d12520b7fb5f1cc94c53eb4e33793602483045022100e97a3e8284019dcc8eb91cd0bdf8df03dabc1dc55af9af1de4e01b7b7bdc793302204946f21cd7d3d47c5f4f543ce4936187c53eeafc113a2f1cfa72abd0509670ca0141210357cb3a5918d15d224f14a89f0eb54478272108f6cbb9c473c1565e55260f6e93ac736476a914ebf9ce6f9053f23c2e4053576914d9e238ef9f0588ad51b26800000000"
    # )


def test_miniscript_spend_liana(session: Session):
    TPUBS = [
        # ALL x 12 [5c9e228d/48'/1'/0'/2']
        "tpubDEGquuorgFNbDrg8vepq1HnaV2mgQu9TcSBgBYfXw4AX8VMgkWqvkxHNuJmiah8iVnA3Hgj4cSvaGAXEnq814yC6hMEreckLsd7zyLL3o76",
        # GYM x 12 [72758bc3/84'/1'/0']
        "tpubDCNhwLKYSSu2FKssoMziAdwhAAKS3bASH7wZYkNmJ7sU5hW9LgDaAQPqe7ivAkskSF29B1CkRRg4g2mbovXgAL9Mby6i9xBdhZh2txDeSLb",
    ]

    # 1st always, or 2nd after 1 block
    DESC = "wsh(or_d(pk({0}/<0;1>/*),and_v(v:pkh({1}/<0;1>/*),older(52596))))".format(
        *TPUBS
    )
    COIN = "Testnet"

    node = btc.get_public_node(session, parse_path("m/48h/1h/0h/2h"), coin_name=COIN)
    assert node.xpub == TPUBS[0]

    reg = messages.MiniscriptRegisterPolicy(
        name="Policy name",
        policy=messages.MiniscriptPolicy(descriptor=DESC),
        coin_name=COIN,
    )
    session.call(reg, expect=messages.Success)
    addr = btc.get_address(session, n=[0, 1], policy=reg.policy, coin_name=COIN)
    assert addr == "tb1qx54dhwjrq3ay3zwvuazfa4k32lkhh20f9mqhtjvwc8n28z6ahrgq3pejk2"

    # (generated from Liana v13)
    psbt = PSBT.from_base64(
        "cHNidP8BAFICAAAAAeLueDmXeu2TBFNQoar0iky5T9JE59JPX0yr/gzIIr7UAAAAAAD9////AUYhAAAAAAAAFgAUhH7Jd+SNi4/DMKLI3HIJdwhi1+6kowQAAAEAywIAAAAAAQHYqmd/WZL+qJOT+5f2XEPzUALTONhlyumq5tyciNVZ8wAAAAAA/f///wE0IgAAAAAAACIAIDUq27pDBHpIicznRJ7W0Vfte6npLsF1yY7B5qOLXbjQAkcwRAIgEAu12ThbMeLnoUW4gXGoyRNtgLoJiMVTGBmN/EF1Ud8CIFacrJc9i3SqN3KU6pUlTnNm6GK1N4Vxa5D2tgz2MYc/ASEDwaxgrIFP7ymqIm9BGZ+2SbpwuLq5OiGykBIZVIRQOEqjowQAAQErNCIAAAAAAAAiACA1Ktu6QwR6SInM50Se1tFX7Xup6S7BdcmOweaji1240AEFRCEDC75bhURKbsY1a1FJFsQxD6kiEzUz4inlmKfSqZlD5JWsc2R2qRStjQxCX2+O2vUnBSggjUbj8GSQbIitA3TNALJoIgYCI1EpH6IXHxLBFqXb1/FWdb0zvMoXyhBDC5/EcW5MSpUYcnWLw1QAAIABAACAAAAAgAAAAAABAAAAIgYDC75bhURKbsY1a1FJFsQxD6kiEzUz4inlmKfSqZlD5JUcXJ4ijTAAAIABAACAAAAAgAIAAIAAAAAAAQAAAAAA"
    )
    pubkey = HDKey.from_string(node.xpub).derive("m/0/1").key
    inputs = [
        messages.TxInputType(
            address_n=i.bip32_derivations[pubkey].derivation,
            prev_hash=i.vin.txid,
            prev_index=i.vin.vout,
            script_type=messages.InputScriptType.SPENDWITNESS,
            policy=reg.policy,
            amount=i.utxo.value,
            sequence=i.vin.sequence,
        )
        for i in psbt.inputs
    ]
    outputs = [
        messages.TxOutputType(
            address=o.vout.script_pubkey.address(NETWORKS["test"]),
            amount=o.vout.value,
            script_type=messages.OutputScriptType.PAYTOWITNESS,
        )
        for o in psbt.outputs
    ]
    signatures, _serialized = btc.sign_tx(
        session,
        COIN,
        inputs,
        outputs,
        version=psbt.tx_version,
        lock_time=psbt.locktime,
        serialize=False,
        prev_txes=TX_CACHE_SIGNET,
    )
    # 657c7c72f8e29eb0f9e97cb6418b8f5a228c2b05148f1b10c0f72982f7d3e38a on signet (height=304038)
    assert (
        signatures[0].hex()
        == "30440220106ef246defefb79999e95d92a1fd63684ea17d5944133762ad589d10b6e2faa02200a73ee663bb732cf78f9f3a61dbc1cc5ca254a9b22b9737ac24149d144c2be18"
    )
    # assert (
    #     serialized.hex()
    #     == "02000000000101e2ee7839977aed93045350a1aaf48a4cb94fd244e7d24f5f4cabfe0cc822bed40000000000fdffffff014621000000000000160014847ec977e48d8b8fc330a2c8dc7209770862d7ee024730440220106ef246defefb79999e95d92a1fd63684ea17d5944133762ad589d10b6e2faa02200a73ee663bb732cf78f9f3a61dbc1cc5ca254a9b22b9737ac24149d144c2be18014421030bbe5b85444a6ec6356b514916c4310fa922133533e229e598a7d2a99943e495ac736476a914ad8d0c425f6f8edaf5270528208d46e3f064906c88ad0374cd00b268a4a30400"
    # )
