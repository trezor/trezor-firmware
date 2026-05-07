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

from trezorlib import btc, messages
from trezorlib.debuglink import DebugSession as Session
from trezorlib.tools import parse_path

from ...input_flows import InputFlowConfirmAllWarnings
from ...tx_cache import TxCache

TPUBS = [
    "tpubDCZB6sR48s4T5Cr8qHUYSZEFCQMMHRg8AoVKVmvcAP5bRw7ArDKeoNwKAJujV3xCPkBvXH5ejSgbgyN6kREmF7sMd41NdbuHa8n1DZNxSMg",
    "tpubDCNhwLKYSSu2FKssoMziAdwhAAKS3bASH7wZYkNmJ7sU5hW9LgDaAQPqe7ivAkskSF29B1CkRRg4g2mbovXgAL9Mby6i9xBdhZh2txDeSLb",
]

pytestmark = [pytest.mark.miniscript]

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
        "wsh(or_d(pk(@0/**),and_v(v:pkh(@1/**),older(1))))".format(*TPUBS),
        [change, index],
        address,
        id=f'Liana-{"internal" if change else "external"}-{index}',
    )
    for change, index, address in DATA
)


@pytest.mark.parametrize("coin, miniscript, n, address", VECTORS)
def test_miniscript_get_address(
    session: Session,
    coin: str,
    miniscript: str,
    n: list[int],
    address: str,
):
    registered = session.call(
        messages.Policy(
            name="Policy name", template=miniscript, xpubs=TPUBS, coin_name=coin
        ),
        expect=messages.RegisteredPolicy,
    )
    assert (
        btc.get_address(
            session,
            coin,
            n=n,
            registered=registered,
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
    DESC = "wsh(or_d(pk(@0/**),and_v(v:pkh(@1/**),older(1))))"
    COIN = "Testnet"

    assert (
        btc.get_public_node(session, parse_path("m/84h/1h/0h"), coin_name=COIN).xpub
        == TPUBS[0]
    )

    registered = session.call(
        messages.Policy(name="Policy name", template=DESC, xpubs=TPUBS, coin_name=COIN),
        expect=messages.RegisteredPolicy,
    )
    assert (
        registered.mac.hex()
        == "c552c38ad4e1eb4d17e163459f07526ad0cab8c64c918d9ff8acf6c6d9293b4e"
    )
    assert (
        btc.get_address(session, n=[0, 2], registered=registered, coin_name=COIN)
        == "tb1qerjma9tcyn6qh5yt7wdqqm3q8sz7ft6dn7pratjclzc8pha27rcsgjn0sp"
    )

    TXHASH_5694f1 = bytes.fromhex(
        "5694f194cb1389ab66c066397534b8ad1cd635c4c1effe26088491d3c8500949"
    )

    inp1 = messages.TxInputType(
        address_n=parse_path("m/84h/1h/0h/0/2"),
        prev_hash=TXHASH_5694f1,
        prev_index=1,
        script_type=messages.InputScriptType.SPENDMINISCRIPT,
        registered=registered,
        amount=10_000,
    )

    out1 = messages.TxOutputType(
        address="tb1ql8qjvr3f6yjjpdlmtuwvjnznad8rx7fkcgwvgg",
        amount=10_000 - 1_000,
        script_type=messages.OutputScriptType.PAYTOWITNESS,
    )

    signatures, serialized = btc.sign_tx(
        session, "Testnet", [inp1], [out1], prev_txes=TX_CACHE_SIGNET
    )

    assert (
        signatures[0].hex()
        == "3045022100e97a3e8284019dcc8eb91cd0bdf8df03dabc1dc55af9af1de4e01b7b7bdc793302204946f21cd7d3d47c5f4f543ce4936187c53eeafc113a2f1cfa72abd0509670ca"
    )

    # f359d5889cdce6aae9ca65d838d30250f3435cf697fb9393a8fe92597f67aad8 on signet (height=303507)
    assert (
        serialized.hex()
        == "01000000000101490950c8d391840826feefc1c435d61cadb834753966c066ab8913cb94f194560100000000ffffffff012823000000000000160014f9c1260e29d12520b7fb5f1cc94c53eb4e33793602483045022100e97a3e8284019dcc8eb91cd0bdf8df03dabc1dc55af9af1de4e01b7b7bdc793302204946f21cd7d3d47c5f4f543ce4936187c53eeafc113a2f1cfa72abd0509670ca0141210357cb3a5918d15d224f14a89f0eb54478272108f6cbb9c473c1565e55260f6e93ac736476a914ebf9ce6f9053f23c2e4053576914d9e238ef9f0588ad51b26800000000"
    )


def test_miniscript_spend_liana(session: Session):
    TPUBS = [
        # ALL x 12 [5c9e228d/48'/1'/0'/2']
        "tpubDEGquuorgFNbDrg8vepq1HnaV2mgQu9TcSBgBYfXw4AX8VMgkWqvkxHNuJmiah8iVnA3Hgj4cSvaGAXEnq814yC6hMEreckLsd7zyLL3o76",
        # GYM x 12 [72758bc3/84'/1'/0']
        "tpubDCNhwLKYSSu2FKssoMziAdwhAAKS3bASH7wZYkNmJ7sU5hW9LgDaAQPqe7ivAkskSF29B1CkRRg4g2mbovXgAL9Mby6i9xBdhZh2txDeSLb",
    ]

    # 1st always, or 2nd after 1 block
    DESC = "wsh(or_d(pk(@0/**),and_v(v:pkh(@1/**),older(52596))))"
    COIN = "Testnet"

    assert (
        btc.get_public_node(session, parse_path("m/48h/1h/0h/2h"), coin_name=COIN).xpub
        == TPUBS[0]
    )
    registered = session.call(
        messages.Policy(name="Policy name", template=DESC, xpubs=TPUBS, coin_name=COIN),
        expect=messages.RegisteredPolicy,
    )
    assert (
        registered.mac.hex()
        == "76fac72a751773625658a22fe55867d30d9988347c03001b657b07fe418e1eb7"
    )
    assert (
        btc.get_address(session, n=[0, 1], registered=registered, coin_name=COIN)
        == "tb1qx54dhwjrq3ay3zwvuazfa4k32lkhh20f9mqhtjvwc8n28z6ahrgq3pejk2"
    )

    TXHASH_d4be22 = bytes.fromhex(
        "d4be22c80cfeab4c5f4fd2e744d24fb94c8af4aaa150530493ed7a973978eee2"
    )

    # unsigned PSBT: cHNidP8BAFICAAAAAeLueDmXeu2TBFNQoar0iky5T9JE59JPX0yr/gzIIr7UAAAAAAD9////AUYhAAAAAAAAFgAUhH7Jd+SNi4/DMKLI3HIJdwhi1+6kowQAAAEAywIAAAAAAQHYqmd/WZL+qJOT+5f2XEPzUALTONhlyumq5tyciNVZ8wAAAAAA/f///wE0IgAAAAAAACIAIDUq27pDBHpIicznRJ7W0Vfte6npLsF1yY7B5qOLXbjQAkcwRAIgEAu12ThbMeLnoUW4gXGoyRNtgLoJiMVTGBmN/EF1Ud8CIFacrJc9i3SqN3KU6pUlTnNm6GK1N4Vxa5D2tgz2MYc/ASEDwaxgrIFP7ymqIm9BGZ+2SbpwuLq5OiGykBIZVIRQOEqjowQAAQErNCIAAAAAAAAiACA1Ktu6QwR6SInM50Se1tFX7Xup6S7BdcmOweaji1240AEFRCEDC75bhURKbsY1a1FJFsQxD6kiEzUz4inlmKfSqZlD5JWsc2R2qRStjQxCX2+O2vUnBSggjUbj8GSQbIitA3TNALJoIgYCI1EpH6IXHxLBFqXb1/FWdb0zvMoXyhBDC5/EcW5MSpUYcnWLw1QAAIABAACAAAAAgAAAAAABAAAAIgYDC75bhURKbsY1a1FJFsQxD6kiEzUz4inlmKfSqZlD5JUcXJ4ijTAAAIABAACAAAAAgAIAAIAAAAAAAQAAAAAA
    # (generated from Liana v13)
    inp1 = messages.TxInputType(
        address_n=parse_path("m/48h/1h/0h/2h/0/1"),
        prev_hash=TXHASH_d4be22,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDMINISCRIPT,
        registered=registered,
        amount=8756,
        sequence=4294967293,
    )

    out1 = messages.TxOutputType(
        address="tb1qs3lvjaly3k9clses5tydcusfwuyx94lwurmc06",
        amount=8518,
        script_type=messages.OutputScriptType.PAYTOWITNESS,
    )

    with session.test_ctx as client:
        IF = InputFlowConfirmAllWarnings(session)
        client.set_input_flow(IF.get())
        signatures, serialized = btc.sign_tx(
            session,
            "Testnet",
            [inp1],
            [out1],
            prev_txes=TX_CACHE_SIGNET,
            version=2,
            lock_time=304036,
        )
    # 657c7c72f8e29eb0f9e97cb6418b8f5a228c2b05148f1b10c0f72982f7d3e38a on signet (height=304038)
    assert (
        signatures[0].hex()
        == "30440220106ef246defefb79999e95d92a1fd63684ea17d5944133762ad589d10b6e2faa02200a73ee663bb732cf78f9f3a61dbc1cc5ca254a9b22b9737ac24149d144c2be18"
    )
    assert (
        serialized.hex()
        == "02000000000101e2ee7839977aed93045350a1aaf48a4cb94fd244e7d24f5f4cabfe0cc822bed40000000000fdffffff014621000000000000160014847ec977e48d8b8fc330a2c8dc7209770862d7ee024730440220106ef246defefb79999e95d92a1fd63684ea17d5944133762ad589d10b6e2faa02200a73ee663bb732cf78f9f3a61dbc1cc5ca254a9b22b9737ac24149d144c2be18014421030bbe5b85444a6ec6356b514916c4310fa922133533e229e598a7d2a99943e495ac736476a914ad8d0c425f6f8edaf5270528208d46e3f064906c88ad0374cd00b268a4a30400"
    )
