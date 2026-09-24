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

import re

import pytest
from embit.bip32 import HDKey
from embit.descriptor import Key
from embit.networks import NETWORKS
from embit.psbt import PSBT

from trezorlib import btc, messages
from trezorlib.debuglink import DebugSession as Session
from trezorlib.tools import parse_path


def _parse_xpub(xpub: str) -> messages.HDNodeType:
    if xpub.startswith("["):
        xpub = xpub.split("]", 1)[1]  # Remove the derivation path prefix (if present)

    node = HDKey.from_base58(xpub)
    return messages.HDNodeType(
        depth=node.depth,
        fingerprint=int.from_bytes(node.fingerprint, "big"),
        child_num=node.child_number,
        chain_code=node.chain_code,
        public_key=node.get_public_key().serialize(),
    )


pytestmark = [
    pytest.mark.capabilities(messages.Capability.Miniscript),
    pytest.mark.experimental,
]

XPUBS = [
    # ALL x 12
    "[5c9e228d/84h/0h/0h]xpub6DDUPHpUo4pcy43iJeZjbSVWGav1SMMmuWdMHiGtkK8rhKmfbomtkwW6GKs1GGAKehT6QRocrmda3WWxXawpjmwaUHfFRXuKrXSapdckEYF",
    "[5c9e228d/84h/0h/1h]xpub6DDUPHpUo4pd1hyVtRaknvZvCgdPdEDMKx3bB5UFcx73pEHRDVK4rwEZUgeUbVuYWGMNLvuBHp5WeyPevN2Gv7m9FnLHQE6XaKNRPZcYcHH",
    "[5c9e228d/84h/0h/2h]xpub6DDUPHpUo4pd5Z4Dmuk7igUc5DcYBoJXcVA1NJbKaRX1M2WKsTqHF5igMbwLpA23iHBwPXY11cidR2kiJVsQWfuJgaQJuxFrjm7iEhsMm4y",
    "[5c9e228d/84h/0h/3h]xpub6DDUPHpUo4pd97vxcds4Qf1oN6zgLqSJLj17Es2mTozPawXwztmDTm9EDzBthkCoArbawqa66hd3v9Kx1h7ekiMKGb5ywWFCRJjTMNC85Zq",
    "[5c9e228d/84h/0h/4h]xpub6DDUPHpUo4pd9Uvp828RbCzZugQVZy78HupxyvtbwBCbWJWYRtf9eFAuVTgsQQS8wWzx8gHw3MUy8NAGUXBqM9Sm3YwzSYMF6gMcXGwV8Rp",
]

TPUBS = [
    # ALL x 12
    "[5c9e228d/84'/1'/0']tpubDCZB6sR48s4T5Cr8qHUYSZEFCQMMHRg8AoVKVmvcAP5bRw7ArDKeoNwKAJujV3xCPkBvXH5ejSgbgyN6kREmF7sMd41NdbuHa8n1DZNxSMg",
    # GYM x 12
    "[72758bc3/84'/1'/0']tpubDCNhwLKYSSu2FKssoMziAdwhAAKS3bASH7wZYkNmJ7sU5hW9LgDaAQPqe7ivAkskSF29B1CkRRg4g2mbovXgAL9Mby6i9xBdhZh2txDeSLb",
]

TPUBS_48 = [
    # ALL x 12 with passphrases: "", "a", "b", "c", "d", "e", "f", "g",
    "[5c9e228d/48'/1'/0'/2']tpubDEGquuorgFNbDrg8vepq1HnaV2mgQu9TcSBgBYfXw4AX8VMgkWqvkxHNuJmiah8iVnA3Hgj4cSvaGAXEnq814yC6hMEreckLsd7zyLL3o76",
    "[6d96bc8f/48'/1'/0'/2']tpubDFNKLpb6iPByHNd6MRa7gxfAa97aTdtzwp17owgyLp9FFbkAuW1gMfD4Vrn7uVssvYfhiG41eHKmb2kaPz5qhqszYybAfiaBATMv8XfrGvg",
    "[4eb89218/48'/1'/0'/2']tpubDF4uVnH8X1sTG14X1wc5kXLsnMDtyDG7fxSpaz4ajnhFCMWwTgevfdzyLTtRMX5Lg21ajRsHQJ8FyUDo9YEW2cag1vQVKHWRpbiLyv95fTj",
    "[7b4bed5a/48'/1'/0'/2']tpubDEBZzwMptCpUxPPJLapgDoUBCnV5SXNEjRkdasgs1ZwzqrJPahDg2WnGZxFtL9ETLUQNKV2Qi2mdy9GBkwnBYuaq3mNZW8LX1Hf7VxqbEXQ",
    "[cab51272/48'/1'/0'/2']tpubDEbN34MtnQ1LWCT8Z1XKUHeB9tY9ebA4e7P84W5gmAMpqKiud1UWRN2ym68p1ijZ4kxAFqmPPAJVvYNPjopEj4cMUXCS8toffucdDgdXVok",
    "[479c205a/48'/1'/0'/2']tpubDEPMzvruWArtmyH7aZy2FhWvarNBCKECXtV1fYS7LeVtUkHdeEWK85bRwnC1otxJ3pJ9eDtpPJF9dSfhTAn3CWtPA95JnxHdq9iHU9KLAXx",
    "[4dd3052b/48'/1'/0'/2']tpubDE6eirnmQdosibC43AKuiG1jb7LebhDAYXzFFemfWWW5LnJhjwdZo9Nwe19qp5tu3vsb1JZXefcHPbaMig92kEPVUcdyoNGnNV5t8ugMBw1",
    "[bc424d11/48'/1'/0'/2']tpubDF721Fe13ScDgtMcpPmgBbb2gCBcsPscm4E2iDfTJDDNyXM958LbVgVxvHJnDVLg6EkuvKuk1GAwDSz1J8u5UUBWQsevdmDW1LsB745UHt8",
]

DATA = [
    (
        "single-pk",
        "wsh(pk(@0/<0;1>/*))",
        "Bitcoin",
        XPUBS,
        [
            (0, 1, "bc1q7ufefmuhl8qsj5zpmud2p05uyuc3gggf5zvlj9dcxpxw4hd9npnqnnlnlq"),
        ],
    ),
    (
        "multi-older",
        "wsh(or_d(pk(@0/<0;1>/*),and_v(v:pkh(@1/<0;1>/*),older(1))))",
        "Testnet",
        TPUBS,
        [
            (0, 1, "tb1qzvr7ptes6kq2ee0745a7h2n639etfz43nsz9d2jn8u6wz8egx0hqnr5pza"),
        ],
    ),
    (
        "single-older",
        "wsh(or_d(pk(@0/<0;1>/*),and_v(v:pkh(@0/<2;3>/*),older(1))))",
        "Testnet",
        TPUBS,
        [
            (0, 1, "tb1q038uy2ghc75tfjxyc8sqdusyj6nq70pfa5hvrx9kekd6a6xcmxeskf0tjv"),
            (0, 2, "tb1qdl6uec9e4ajrlzesqjm3jqtv4986j20fullm46gq5c0r6qur6s8qhk48qu"),
        ],
    ),
    (
        "2of2-expands-2of3",
        "wsh(or_i(and_v(v:thresh(2,pkh(@0/<2;3>/*),a:pkh(@1/<2;3>/*),a:pkh(@2/<0;1>/*)),older(52596)),and_v(v:pk(@0/<0;1>/*),pk(@1/<0;1>/*))))",
        "Bitcoin",
        XPUBS,
        [
            (0, 1, "bc1qkye36enq7qzxadptuhh4v9t09zhelpw3cz9n0knvg2ayhdns5c7sc6vyde"),
        ],
    ),
    (
        "1of2-large-index",
        "wsh(or_b(pk(@0/<0;1>/*),s:pk(@1/<0;1>/*)))",
        "Bitcoin",
        XPUBS,
        [
            (0, 2048, "bc1qqfljvkn3v8fshem7hpvyw9d8vcwxgflatdgynkpr76gcgaaza0ms3x9gge"),
            (1, 2048, "bc1qpxxvxdhcx7x48zcjptka52qxsj9qlz3kc2kypnws49h9xc9hk0jsdpfzpg"),
        ],
    ),
    (
        "2of3-or-after1of3",
        "wsh(and_v(v:multi(2,@0/<0;1>/*,@1/<0;1>/*,@2/<0;1>/*),after(1893456000)))",
        "Bitcoin",
        XPUBS,
        [
            (0, 77, "bc1qksfktckxm2ca7540q3q4u26t4a4mz20mq3yv2c0afulyj836ud2q0gaszm"),
            (1, 77, "bc1qc7ewhxqxaure8rvnaktdw9wp8jfd8ayj0gd05y3yst439fya4g3sjhwqac"),
        ],
    ),
    (
        "1of1-or-older3of5",
        "wsh(or_d(pk(@0/<0;1>/*),and_v(v:thresh(3,pkh(@1/<0;1>/*),a:pkh(@2/<0;1>/*),a:pkh(@3/<0;1>/*),a:pkh(@4/<0;1>/*)),older(65535))))",
        "Bitcoin",
        XPUBS,
        [
            (0, 120, "bc1qmspe3w3xnkcqc96pf0ekzsr78zmhkdawf3arwegwxr9eu5nkf06qemzzkc"),
            (1, 120, "bc1qxrsupl645gndl64upgsmrjugpt4gf93lamrn0x8reqshv3gh85ksdp565h"),
        ],
    ),
    (
        "5of5-decays-4of5-decays-3of5",
        "wsh(or_i(and_v(v:thresh(3,pkh(@0/<4;5>/*),a:pkh(@1/<4;5>/*),a:pkh(@2/<4;5>/*),a:pkh(@3/<4;5>/*),a:pkh(@4/<4;5>/*)),older(52596)),or_i(and_v(v:thresh(4,pkh(@0/<2;3>/*),a:pkh(@1/<2;3>/*),a:pkh(@2/<2;3>/*),a:pkh(@3/<2;3>/*),a:pkh(@4/<2;3>/*)),older(4383)),and_v(v:and_v(v:and_v(v:and_v(v:pk(@0/<0;1>/*),pk(@1/<0;1>/*)),pk(@2/<0;1>/*)),pk(@3/<0;1>/*)),pk(@4/<0;1>/*)))))",
        "Bitcoin",
        XPUBS,
        [
            (0, 1, "bc1qvqvur38yke37wnzwkx2pr0twl4w4lfz47k50tkxn0lkcwsjz2ejslk63md"),
            (1, 1, "bc1q2xygdukalavq40nhf754ce954nufew3shqv5luylwauyxt4jxpwqzsxvm5"),
            (0, 2, "bc1qsm6nygqwdhtdcw7av4gkyj82nk43taxrsvx5fc6kgfqjywwhnt2s0klz4j"),
            (1, 2, "bc1q6zznz4cqrwc4ssdvrce0964ark24glj9nf3g392vja3nqqx4sw3sryt7uu"),
        ],
    ),
    (
        "liana-simple1",
        "wsh(or_d(pk(@0/<0;1>/*),and_v(v:pkh(@1/<0;1>/*),older(1))))",
        "Signet",
        TPUBS,
        [
            (0, 0, "tb1qwr00r4x9a2ycm7fn48c7kqm6kpsp56ydwx482ns5c3wxmrwqwu2stjh6cc"),
            (0, 1, "tb1qzvr7ptes6kq2ee0745a7h2n639etfz43nsz9d2jn8u6wz8egx0hqnr5pza"),
            (0, 2, "tb1qerjma9tcyn6qh5yt7wdqqm3q8sz7ft6dn7pratjclzc8pha27rcsgjn0sp"),
            (0, 3, "tb1qc6zh83pdaj64tkmvu5969falc95s7sgs6yku5nh9asspzfmtq8cq7yxr2a"),
            (1, 0, "tb1q5f45hdwm06sf9wa20pcwa5rr9xn99m4yfpzdg406044nl9jhadps2ghwl5"),
            (1, 1, "tb1qk47jne78xqrzxwj5wc8l3qypneh96jumw56lkp50akhqpw5jmr6qwxdctf"),
            (1, 2, "tb1q68hg7scyjs20dndpdl7crr3kue0g8a5pkvktwlnwk4ygheazyfzqnhy9gm"),
        ],
    ),
    (
        "liana-simple2",
        "wsh(or_d(pk(@0/<0;1>/*),and_v(v:pkh(@1/<0;1>/*),older(52596))))",
        "Signet",
        TPUBS,
        [
            (0, 1, "tb1qhuvpd22plqpuudu8pn7gm9f5cgyqtkr3vmadlknkazknaat9krrs5p6lyq"),
            (0, 2, "tb1q49avpm6vnwl8ywxk7geaxvp7us3alzu798ccs58jsk4j3c9rkrtqh3c5pz"),
            (0, 3, "tb1qh596vjwju32m6zpdsa49q8dslqvd5a9snp0hp2twgsn54cgvsgdqm7lmxl"),
        ],
    ),
    (
        "liana-simple3",
        "wsh(or_d(pk(@0/<0;1>/*),and_v(v:pkh(@1/<0;1>/*),older(52596))))",
        "Signet",
        TPUBS,
        [
            (0, 1, "tb1qhuvpd22plqpuudu8pn7gm9f5cgyqtkr3vmadlknkazknaat9krrs5p6lyq"),
            (0, 2, "tb1q49avpm6vnwl8ywxk7geaxvp7us3alzu798ccs58jsk4j3c9rkrtqh3c5pz"),
            (0, 3, "tb1qh596vjwju32m6zpdsa49q8dslqvd5a9snp0hp2twgsn54cgvsgdqm7lmxl"),
        ],
    ),
    (
        "liana-large",
        "wsh(or_i(and_v(v:thresh(1,pkh(@0/<6;7>/*),a:pkh(@1/<6;7>/*),a:pkh(@2/<6;7>/*),a:pkh(@3/<6;7>/*),a:pkh(@4/<6;7>/*),a:pkh(@5/<6;7>/*),a:pkh(@6/<6;7>/*),a:pkh(@7/<6;7>/*)),older(3)),or_i(and_v(v:thresh(4,pkh(@0/<4;5>/*),a:pkh(@1/<4;5>/*),a:pkh(@2/<4;5>/*),a:pkh(@3/<4;5>/*),a:pkh(@4/<4;5>/*),a:pkh(@5/<4;5>/*),a:pkh(@6/<4;5>/*),a:pkh(@7/<4;5>/*)),older(2)),or_i(and_v(v:thresh(6,pkh(@0/<2;3>/*),a:pkh(@1/<2;3>/*),a:pkh(@2/<2;3>/*),a:pkh(@3/<2;3>/*),a:pkh(@4/<2;3>/*),a:pkh(@5/<2;3>/*),a:pkh(@6/<2;3>/*),a:pkh(@7/<2;3>/*)),older(1)),and_v(v:and_v(v:and_v(v:and_v(v:and_v(v:and_v(v:and_v(v:pk(@0/<0;1>/*),pk(@1/<0;1>/*)),pk(@2/<0;1>/*)),pk(@3/<0;1>/*)),pk(@4/<0;1>/*)),pk(@5/<0;1>/*)),pk(@6/<0;1>/*)),pk(@7/<0;1>/*))))))",
        "Signet",
        TPUBS_48,
        [
            (0, 1, "tb1qyt2q5ns8z88fj7n7gpxnvqp0frxjx8fnl7k6cywtneak8pq0a33sefyrd8"),
            (0, 2, "tb1q9yxxpms7d3kt4l8zf0g782hykquklmhye507a5q6n605fr50ht6s8l5afw"),
            (0, 3, "tb1qk7gyeu0nh7p8u8zc5d8jg8pxrc4ma4pj56f058g3smmhm3rw87xq03jklx"),
        ],
    ),
]


@pytest.mark.parametrize(
    "name, desc, coin, keys, tests",
    (pytest.param(name, *args, id=name) for name, *args in DATA),
)
def test_miniscript_get_address(
    session: Session,
    name: str,
    desc: str,
    coin: str,
    keys: list[str],
    tests: list[tuple[int, int, str]],
):
    indices = set(map(int, re.findall("@(\\d+)", desc)))
    assert min(indices) == 0
    assert max(indices) == len(indices) - 1
    keys = keys[: len(indices)]

    policy = btc.register_policy(
        session,
        name=name,
        descriptor=desc,
        nodes=list(map(_parse_xpub, keys)),
        coin_name=coin,
    )
    fpr = session.get_root_fingerprint()
    keys = [Key.from_string(k) for k in keys]
    keys = [k for k in keys if k.fingerprint == fpr]  # drop unrelated keys
    assert keys

    for internal, index, expected in tests:
        internal = bool(internal)
        redeem = messages.MiniscriptRedeemPolicyType(
            policy=policy, internal=internal, index=index
        )
        for key in keys:
            assert key.origin is not None
            # TODO: choose correct internal child number based on the descriptor
            address_n = key.origin.derivation + [internal, index]
            address = btc.get_address(
                session,
                n=address_n,
                show_display=True,
                script_type=messages.InputScriptType.SPENDWITNESS,
                miniscript=redeem,
                coin_name=coin,
            )
            assert address == expected


COIN = "Signet"


def test_miniscript_spend(session: Session):
    # 1st always, or 2nd after 1 block
    DESC = "wsh(or_d(pk(@0/<0;1>/*),and_v(v:pkh(@1/<0;1>/*),older(1))))"
    NODES = list(map(_parse_xpub, TPUBS[:2]))

    node = btc.get_public_node(session, parse_path("m/84h/1h/0h"), coin_name=COIN)
    assert node.node == NODES[0]

    reg = messages.MiniscriptRegisterPolicy(
        name="Policy name",
        policy=messages.MiniscriptPolicy(
            descriptor=DESC,
            nodes=NODES,
        ),
        coin_name=COIN,
    )
    session.call(msg=reg, expect=messages.Success)

    redeem = messages.MiniscriptRedeemPolicyType(
        policy=reg.policy, internal=False, index=2
    )
    addr = btc.get_address(
        session,
        n=parse_path("m/84h/1h/0h/0/2"),
        script_type=messages.InputScriptType.SPENDWITNESS,
        miniscript=redeem,
        coin_name=COIN,
    )

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
            miniscript=redeem,
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
        prev_txes=prev_txs(psbt),
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
    # 1st always, or 2nd after 1 block
    DESC = "wsh(or_d(pk(@0/<0;1>/*),and_v(v:pkh(@1/<0;1>/*),older(52596))))"
    TPUBS = [
        "[5c9e228d/48'/1'/0'/2']tpubDEGquuorgFNbDrg8vepq1HnaV2mgQu9TcSBgBYfXw4AX8VMgkWqvkxHNuJmiah8iVnA3Hgj4cSvaGAXEnq814yC6hMEreckLsd7zyLL3o76",  # ALL x 12
        "[72758bc3/84'/1'/0']tpubDCNhwLKYSSu2FKssoMziAdwhAAKS3bASH7wZYkNmJ7sU5hW9LgDaAQPqe7ivAkskSF29B1CkRRg4g2mbovXgAL9Mby6i9xBdhZh2txDeSLb",  # GYM x 12
    ]
    NODES = list(map(_parse_xpub, TPUBS))

    node = btc.get_public_node(session, parse_path("m/48h/1h/0h/2h"), coin_name=COIN)
    assert _parse_xpub(node.xpub) == NODES[0]

    reg = messages.MiniscriptRegisterPolicy(
        name="Policy name",
        policy=messages.MiniscriptPolicy(descriptor=DESC, nodes=NODES),
        coin_name=COIN,
    )
    session.call(reg, expect=messages.Success)

    redeem = messages.MiniscriptRedeemPolicyType(
        policy=reg.policy, internal=False, index=1
    )
    addr = btc.get_address(
        session,
        n=parse_path("m/84h/1h/0h/0/1"),
        script_type=messages.InputScriptType.SPENDWITNESS,
        miniscript=redeem,
        coin_name=COIN,
    )
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
            miniscript=redeem,
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
        prev_txes=prev_txs(psbt),
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


def test_miniscript_spend_liana_decay(session: Session):
    DESC = "wsh(or_i(and_v(v:thresh(1,pkh(@1/<2;3>/*),a:pkh(@0/<2;3>/*)),older(1)),and_v(v:pk(@0/<0;1>/*),pk(@1/<0;1>/*))))"
    TPUBS = [
        "[5c9e228d/48'/1'/0'/2']tpubDEGquuorgFNbDrg8vepq1HnaV2mgQu9TcSBgBYfXw4AX8VMgkWqvkxHNuJmiah8iVnA3Hgj4cSvaGAXEnq814yC6hMEreckLsd7zyLL3o76",  # ALL x 12
        "[6d96bc8f/48'/1'/0'/2']tpubDFNKLpb6iPByHNd6MRa7gxfAa97aTdtzwp17owgyLp9FFbkAuW1gMfD4Vrn7uVssvYfhiG41eHKmb2kaPz5qhqszYybAfiaBATMv8XfrGvg",  # ALL x 12, passphrase='a'
    ]
    NODES = list(map(_parse_xpub, TPUBS))

    node = btc.get_public_node(session, parse_path("m/48h/1h/0h/2h"), coin_name=COIN)
    assert node.node == NODES[0]
    pubkey = HDKey.from_string(node.xpub).derive("m/1/3").key

    reg = messages.MiniscriptRegisterPolicy(
        name="Policy name",
        policy=messages.MiniscriptPolicy(descriptor=DESC, nodes=NODES),
        coin_name=COIN,
    )
    session.call(reg, expect=messages.Success)

    # Spend from primary path
    redeem = messages.MiniscriptRedeemPolicyType(
        policy=reg.policy, internal=True, index=3
    )
    addr = btc.get_address(
        session,
        n=parse_path("m/48h/1h/0h/2h/1/3"),
        script_type=messages.InputScriptType.SPENDWITNESS,
        miniscript=redeem,
        coin_name=COIN,
    )
    assert addr == "tb1qtn0h3kyk7c2h38cz836e6qsys3fmj0qng6j8hqpef0mrwp2eq6gs59um2e"
    psbt = PSBT.from_base64(
        "cHNidP8BAFICAAAAAXyOne0wXOscsTS4+GncbkkuGLFzSK4T9qEOqUWwbyIjAAAAAAD9////AQ6RAAAAAAAAFgAUaV+EASSGwwZoFhIeQkYzOzU0mPX18gQAAAEA/XUBAgAAAAABAfWRv9hJTH8SRmsdBnwuHh0087wTSDMlnnV7xGuEA2oXAAAAAAD9////AUCSAAAAAAAAIgAgXN942Jb2FXifAjx1nQIEhFO5PBNGpHuAOUv2NwVZBpEERzBEAiBxO+Z54gXs3ytEdTWq/6EbQfa5VFK3ZmAqYgiibuytJAIgPt2nUO1RzejG8ggPAf1wwEPYy0DMQoz0YfRTWrHFy+4BRzBEAiAcleadRZ7sN3u8GRDWl0x0oPtPKNWu8CO8EWFdgXBf1AIgZpbDHd5fg+Lp0p8qj9hdwvj0T5N3udKVOpMgiajHOHkBAIJjdqkUrKiKs4B3N/MFLvz11vcz58EC2uWIrGt2qRTdQZogjRRuHOlnFm46z4jGvGdaA4isbJNRiFGyZyEC1+ob/8bj7o+fvkFEtOWHZrW3PMTzoAOgeqwZ281FTh2tIQPOCNaDT42SS6WZWO6AJlak2/tTxxJhjND4D5gdMefXkqxo8fIEAAEBK0CSAAAAAAAAIgAgXN942Jb2FXifAjx1nQIEhFO5PBNGpHuAOUv2NwVZBpEBBYJjdqkU5XDtpADQ39N3zjj+1sog4QTd0ryIrGt2qRTYJ95XtGyxmy9pjDjSk6xyYbWWLIisbJNRiFGyZyEC0N4J/5X26M8VlBImRxsPrtTK5ho87nF4BDDahFrkSNetIQIhVyz2EZeB0isIf8pl8/PkLsK7xA4MSoTgArJEs/fsAKxoIgYCIVcs9hGXgdIrCH/KZfPz5C7Cu8QODEqE4AKyRLP37AAcbZa8jzAAAIABAACAAAAAgAIAAIABAAAAAwAAACIGAiiG/jdVlWgumZ7Zp7x+ahJnabNyGTqawhxWw+F7RDQTHFyeIo0wAACAAQAAgAAAAIACAACAAwAAAAMAAAAiBgK+qEQ8m+Nzh08Lf4T9x9/0iO/NVC7ZH0M6TcpoQor9aBxtlryPMAAAgAEAAIAAAACAAgAAgAMAAAADAAAAIgYC0N4J/5X26M8VlBImRxsPrtTK5ho87nF4BDDahFrkSNccXJ4ijTAAAIABAACAAAAAgAIAAIABAAAAAwAAAAAA"
    )
    inputs = [
        messages.TxInputType(
            address_n=i.bip32_derivations[pubkey].derivation,
            prev_hash=i.vin.txid,
            prev_index=i.vin.vout,
            script_type=messages.InputScriptType.SPENDWITNESS,
            miniscript=redeem,
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
        prev_txes=prev_txs(psbt),
    )
    assert len(signatures) == 1
    assert (
        signatures[0].hex()
        == "3045022100c6e2d81a8b4f03371f0e7687fe1a45ac128beaf79afba8725b849e0807cadb2402202f464a9a9d14b959262179f52afe1874391a7556e887a083a1091aa44c7b89ab"
    )

    # Spend from recovery path
    redeem = messages.MiniscriptRedeemPolicyType(
        policy=reg.policy, internal=False, index=2
    )
    addr = btc.get_address(
        session,
        n=parse_path("m/48h/1h/0h/2h/2/2"),
        script_type=messages.InputScriptType.SPENDWITNESS,
        miniscript=redeem,
        coin_name=COIN,
    )
    psbt = PSBT.from_base64(
        "cHNidP8BAF4CAAAAAWvPLpWD/mhNjNTfxLglYRpwWslcJRacRt3iXJDKHbDjAAAAAAABAAAAAfaUAAAAAAAAIgAgXzNTvMOhzyC5mf2nwsAxC4SbM03GUaH1bRe7Wc2laMLu8gQAAAEA/XMBAgAAAAABAQeZd9F9/iwEVyzp9escCB+AJjcCwlN0ApImeCjSqbOUAAAAAAABAAAAAWKWAAAAAAAAIgAghTirS5bAqgDBvgtrWzAy8PwdDleldBa1Xh51x/pRB3EGACEDv6ZPbO53GoGbzm20Ep3OZRbBt+UXWsatFw7JY3YQFGNHMEQCIDkSloyvQ2xdWnE4TI4KBiHCgMf3k71ywVnZrdo/Jj6dAiBuM9mVS+feZ6k4yTFOqbn8tvEm/0CDR3SH1NwIMODu5gEhA+vzxif8IU5Mu/vpCmdDOq4930IfIEd0nMFyohfrLT9aAQGCY3apFP9a03jShyZuwFvqYyR/UbujiyVRiKxrdqkUIDckcXamVhBNo8voc1L7k4cRmIKIrGyTUYhRsmchAqv/gRHz0YDd8QRUWkGI4FrW4qOj/5Wni/iWZ1XW3SjLrSED4Lan74+icUpfyYmvfitBggXCSMb6CME1RlS3sn5LdpSsaOryBAABAStilgAAAAAAACIAIIU4q0uWwKoAwb4La1swMvD8HQ5XpXQWtV4edcf6UQdxAQWCY3apFBSNDLQwSLJUCnNjpdXg0NX6slzPiKxrdqkUL+35XV12M/lYjfdBgrNqApTuKQGIrGyTUYhRsmchAmhz6kzA4CPeNriOYLiX0MYQuTz2YiMNGSEPLTHVzYLJrSEDhLTzre37aePGwzGGD0Q6jsAmoiveprYzNfp9P/ekIMCsaCIGAmhz6kzA4CPeNriOYLiX0MYQuTz2YiMNGSEPLTHVzYLJHFyeIo0wAACAAQAAgAAAAIACAACAAAAAAAIAAAAiBgJxXQBmEl34zNWubu1uGHVdVatlBulafLg4N+6V0xCVMRxtlryPMAAAgAEAAIAAAACAAgAAgAIAAAACAAAAIgYCy1mVhKOs0tydmYNdBHYn/9TaFMWP3MCgrJOYBvolB4wcXJ4ijTAAAIABAACAAAAAgAIAAIACAAAAAgAAACIGA4S0863t+2njxsMxhg9EOo7AJqIr3qa2MzX6fT/3pCDAHG2WvI8wAACAAQAAgAAAAIACAACAAAAAAAIAAAAAIgICGG89/Jb3Zg9uN2N4zluawTnXViphVrcCxkYszWspwZUcbZa8jzAAAIABAACAAAAAgAIAAIACAAAAAwAAACICAtfqG//G4+6Pn75BRLTlh2a1tzzE86ADoHqsGdvNRU4dHFyeIo0wAACAAQAAgAAAAIACAACAAAAAAAMAAAAiAgM9fbrnhHARl+uWy5NrsOd8E4ZnlbtoOxTqs86khtdyZhxcniKNMAAAgAEAAIAAAACAAgAAgAIAAAADAAAAIgIDzgjWg0+NkkulmVjugCZWpNv7U8cSYYzQ+A+YHTHn15IcbZa8jzAAAIABAACAAAAAgAIAAIAAAAAAAwAAAAA="
    )
    assert addr == "tb1qs5u2kjukcz4qpsd7pd44kvpj7r7p6rjh546pdd27re6u07j3qacs48qcy3"
    pubkey = HDKey.from_string(node.xpub).derive("m/2/2").key
    inputs = [
        messages.TxInputType(
            address_n=i.bip32_derivations[pubkey].derivation,
            prev_hash=i.vin.txid,
            prev_index=i.vin.vout,
            script_type=messages.InputScriptType.SPENDWITNESS,
            miniscript=redeem,
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
        prev_txes=prev_txs(psbt),
    )
    assert len(signatures) == 1
    assert (
        signatures[0].hex()
        == "3045022100a0189c2c2b57aeb522c2737c52039e8d4f3d197c31a28330822c0aa0ae01d15f022023020852beec45a2052e4c54822825d530a5bfc9bdfb88a3c38669bfea4657a2"
    )


def test_miniscript_spend_sparrow(session: Session):
    DESC = "wsh(sortedmulti(2,@0/<0;1>/*,@1/<0;1>/*,@2/<0;1>/*))"
    TPUBS = [
        "[5c9e228d/48h/1h/0h/2h]tpubDEGquuorgFNbDrg8vepq1HnaV2mgQu9TcSBgBYfXw4AX8VMgkWqvkxHNuJmiah8iVnA3Hgj4cSvaGAXEnq814yC6hMEreckLsd7zyLL3o76",  # ALL x 12, no passphrase
        "[cab51272/48h/1h/0h/2h]tpubDEbN34MtnQ1LWCT8Z1XKUHeB9tY9ebA4e7P84W5gmAMpqKiud1UWRN2ym68p1ijZ4kxAFqmPPAJVvYNPjopEj4cMUXCS8toffucdDgdXVok",  # ALL x 12, passphrase='d'
        "[6d96bc8f/48h/1h/0h/2h]tpubDFNKLpb6iPByHNd6MRa7gxfAa97aTdtzwp17owgyLp9FFbkAuW1gMfD4Vrn7uVssvYfhiG41eHKmb2kaPz5qhqszYybAfiaBATMv8XfrGvg",  # ALL x 12, passphrase='a'
    ]
    NODES = list(map(_parse_xpub, TPUBS))

    node = btc.get_public_node(session, parse_path("m/48h/1h/0h/2h"), coin_name=COIN)
    assert _parse_xpub(node.xpub) == NODES[0]

    policy = btc.register_policy(
        session,
        name="NAME",
        descriptor=DESC,
        nodes=NODES,
        coin_name=COIN,
    )
    redeem = messages.MiniscriptRedeemPolicyType(policy=policy, internal=False, index=0)
    addr = btc.get_address(
        session,
        n=parse_path("m/48h/1h/0h/2h/0/0"),
        script_type=messages.InputScriptType.SPENDWITNESS,
        miniscript=redeem,
        coin_name=COIN,
    )
    assert addr == "tb1q4wrndh4nmzs43mcdv6c7wftda6w9urzfvqt33xl6h77cnytuksxqss4y8c"

    psbt = PSBT.from_base64(
        "cHNidP8BAF4CAAAAAT7hiKaaKBeq7VZB1HUynxDvKbKFGwSWxo1cVNZ/nP6wAAAAAAD9////AayPAAAAAAAAIgAgzCs0nB3ja77h+YFmRYrPtYitE202q7nzV3TjbZvJq5P58gQATwEENYfPBDH8vcyAAAACP8N64hBDZxUueKl7mJ5lAnlVEAdZ4ad+BzmeHEsahzQCLscxG1LFIk2oYODSS//lfME9yKWcp4oLoXnvxXs4o88UXJ4ijTAAAIABAACAAAAAgAIAAIBPAQQ1h88ExuBP2YAAAAL+L+YczMjTx5UMTXTnfT75BSNsLqA6NTtpF7gQZOAzSgNUeD2qOp9CSxSjqz80ivIowlWxHG6ieqQMcADYwcvEJxRtlryPMAAAgAEAAIAAAACAAgAAgE8BBDWHzwRdbaTwgAAAAtTu3N4SVtHIdFsD24TvDAD6o8KfOObgOrV33zalySwaA5eEjTcfmIb3BeoTMldtlhOeXjDwyP89GHl5t1iogn84FMq1EnIwAACAAQAAgAAAAIACAACAAAEAXgIAAAABi1EYWmpmVTNbn9zxdWUZ2w1uZoOJXvMGIag4KOGjCbgAAAAAAP3///8BV5AAAAAAAAAiACCrhzbes9ihWO8NZrHnJW3unF4MSWAXGJv6v72JkXy0DPnyBAABAStXkAAAAAAAACIAIKuHNt6z2KFY7w1mseclbe6cXgxJYBcYm/q/vYmRfLQMAQMEAQAAAAEFaVIhAvPBEdutUs+A8nkluwzJo01Huh+HjHM0xo7rOuoSqSRKIQNzQgkSodhiRDiGeiiW1aPXth6Y4NgUk5k9zxnYLAVu4SED8YQRoqx2GPXlgq0iT+5NqE4MxtKcA4MdTT4JQQG4MWxTriIGAvPBEdutUs+A8nkluwzJo01Huh+HjHM0xo7rOuoSqSRKHFyeIo0wAACAAQAAgAAAAIACAACAAAAAAAAAAAAiBgPxhBGirHYY9eWCrSJP7k2oTgzG0pwDgx1NPglBAbgxbBxtlryPMAAAgAEAAIAAAACAAgAAgAAAAAAAAAAAIgYDc0IJEqHYYkQ4hnooltWj17YemODYFJOZPc8Z2CwFbuEcyrUScjAAAIABAACAAAAAgAIAAIAAAAAAAAAAAAABAWlSIQMLvluFREpuxjVrUUkWxDEPqSITNTPiKeWYp9KpmUPklSEDb6dXrxks+icpQ7cwPIw1HlzjmxJ+pvoYBA4aGdV8ULAhA5mS7fFoBW9veimPQ7NaT6yyjXP0UC3AZetccFUCnafCU64iAgMLvluFREpuxjVrUUkWxDEPqSITNTPiKeWYp9KpmUPklRxcniKNMAAAgAEAAIAAAACAAgAAgAAAAAABAAAAIgIDmZLt8WgFb296KY9Ds1pPrLKNc/RQLcBl61xwVQKdp8IcbZa8jzAAAIABAACAAAAAgAIAAIAAAAAAAQAAACICA2+nV68ZLPonKUO3MDyMNR5c45sSfqb6GAQOGhnVfFCwHMq1EnIwAACAAQAAgAAAAIACAACAAAAAAAEAAAAA"
    )

    pubkey = HDKey.from_string(node.xpub).derive("m/0/0").key
    inputs = [
        messages.TxInputType(
            address_n=i.bip32_derivations[pubkey].derivation,
            prev_hash=i.vin.txid,
            prev_index=i.vin.vout,
            script_type=messages.InputScriptType.SPENDWITNESS,
            miniscript=redeem,
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
        prev_txes=prev_txs(psbt),
    )
    assert len(signatures) == 1
    assert (
        signatures[0].hex()
        == "304402202ef958e880e7b4941983ecd2be4aec62c4160e81971992c2ddc87caec76435bf02207ee489081cfa2c0bed32feeaf1554683435ffa8ecb2caa42c80d1d626cef4b54"
    )


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
