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
from embit.descriptor import Descriptor, Key
from embit.networks import NETWORKS
from embit.psbt import PSBT

from trezorlib import btc, messages
from trezorlib.debuglink import DebugSession as Session
from trezorlib.tools import parse_path

pytestmark = [
    pytest.mark.capabilities(messages.Capability.Miniscript),
    pytest.mark.experimental,
]


def _parse_keys(*keys: str) -> list[Key]:
    return [Key.from_string(k) for k in keys]


def _to_protobuf(k: Key) -> messages.MiniscriptKey:
    key = k.key
    return messages.MiniscriptKey(
        node=messages.HDNodeType(
            depth=key.depth,
            fingerprint=int.from_bytes(key.fingerprint, "big"),
            child_num=key.child_number,
            chain_code=key.chain_code,
            public_key=key.get_public_key().serialize(),
        ),
        root_fingerprint=int.from_bytes(k.fingerprint, "big"),
        derivation_path=k.derivation,
    )


TEST_XPUBS = _parse_keys(
    # SLIP-0014 + passphrases ("", "a", "b", "c", "d", "e", "f", "g")
    "[5c9e228d/48'/1'/0'/2']tpubDEGquuorgFNbDrg8vepq1HnaV2mgQu9TcSBgBYfXw4AX8VMgkWqvkxHNuJmiah8iVnA3Hgj4cSvaGAXEnq814yC6hMEreckLsd7zyLL3o76",
    "[6d96bc8f/48'/1'/0'/2']tpubDFNKLpb6iPByHNd6MRa7gxfAa97aTdtzwp17owgyLp9FFbkAuW1gMfD4Vrn7uVssvYfhiG41eHKmb2kaPz5qhqszYybAfiaBATMv8XfrGvg",
    "[4eb89218/48'/1'/0'/2']tpubDF4uVnH8X1sTG14X1wc5kXLsnMDtyDG7fxSpaz4ajnhFCMWwTgevfdzyLTtRMX5Lg21ajRsHQJ8FyUDo9YEW2cag1vQVKHWRpbiLyv95fTj",
    "[7b4bed5a/48'/1'/0'/2']tpubDEBZzwMptCpUxPPJLapgDoUBCnV5SXNEjRkdasgs1ZwzqrJPahDg2WnGZxFtL9ETLUQNKV2Qi2mdy9GBkwnBYuaq3mNZW8LX1Hf7VxqbEXQ",
    "[cab51272/48'/1'/0'/2']tpubDEbN34MtnQ1LWCT8Z1XKUHeB9tY9ebA4e7P84W5gmAMpqKiud1UWRN2ym68p1ijZ4kxAFqmPPAJVvYNPjopEj4cMUXCS8toffucdDgdXVok",
    "[479c205a/48'/1'/0'/2']tpubDEPMzvruWArtmyH7aZy2FhWvarNBCKECXtV1fYS7LeVtUkHdeEWK85bRwnC1otxJ3pJ9eDtpPJF9dSfhTAn3CWtPA95JnxHdq9iHU9KLAXx",
    "[4dd3052b/48'/1'/0'/2']tpubDE6eirnmQdosibC43AKuiG1jb7LebhDAYXzFFemfWWW5LnJhjwdZo9Nwe19qp5tu3vsb1JZXefcHPbaMig92kEPVUcdyoNGnNV5t8ugMBw1",
    "[bc424d11/48'/1'/0'/2']tpubDF721Fe13ScDgtMcpPmgBbb2gCBcsPscm4E2iDfTJDDNyXM958LbVgVxvHJnDVLg6EkuvKuk1GAwDSz1J8u5UUBWQsevdmDW1LsB745UHt8",
)

DATA = [
    (
        "single-pk",
        "wsh(pk(@0/<0;1>/*))",
        "Testnet",
        TEST_XPUBS,
        [
            (0, 1, "tb1q703xyg0j3c9wzzd3yxdhgwncly5az9dqyts4zrmykt0e5p5lxy8sne8axp"),
            (1, 1, "tb1qj05c6cyeyndu0h57ta4tk2f0vgssx8ekava0wn0lx726gcp5ltvsvnxvzt"),
        ],
    ),
    (
        "single-older",
        "wsh(or_d(pk(@0/<0;1>/*),and_v(v:pkh(@0/<2;3>/*),older(1))))",
        "Testnet",
        TEST_XPUBS,
        [
            (0, 1, "tb1qaznv7g9tmjcw6645mu3w3yevzfx9ehl6fr457v9kaeaqsfsaccgqpgpyrt"),
            (0, 2, "tb1qw7eafckyanwxrvsv0xd0wtsah3zjrww2nh34h0x5llgw9tdlja5sjh8rl6"),
        ],
    ),
    (
        "2of2-or-2of3-older",
        "wsh(or_i(and_v(v:thresh(2,pkh(@0/<2;3>/*),a:pkh(@1/<2;3>/*),a:pkh(@2/<0;1>/*)),older(52596)),and_v(v:pk(@0/<0;1>/*),pk(@1/<0;1>/*))))",
        "Testnet",
        TEST_XPUBS,
        [
            (0, 1, "tb1q3f4vdlua4uea7laa6z26tnrar8pqlqdyl479n3mngzk94xfa8m0s0jykwf"),
            (1, 1, "tb1qcq8rfuu0syn7pj6xx2xqlr0mjtw9nyee53qd5ytj90geatc0md3qqgxkm9"),
        ],
    ),
    (
        "1of2-large-index",
        "wsh(or_b(pk(@0/<0;1>/*),s:pk(@1/<0;1>/*)))",
        "Testnet",
        TEST_XPUBS,
        [
            (0, 2048, "tb1qchnl803tsze6k790uxxkcyaw8xgpjyx6w9knrtgv7mpwpu26z3ks7wdq42"),
            (1, 2048, "tb1q4ptneqznmnfftfw2wv088d0znssupn45j25f8mh0nutrwt6f7ursvfd4kw"),
        ],
    ),
    (
        "2of3-or-1of3-after",
        "wsh(and_v(v:multi(2,@0/<0;1>/*,@1/<0;1>/*,@2/<0;1>/*),after(1893456000)))",
        "Testnet",
        TEST_XPUBS,
        [
            (0, 77, "tb1qe07rhznj4vqwgqyvwn55jw2z07cz777uxn6rftd5kxgl3a2px75swaqrvg"),
            (1, 77, "tb1ql3csnefc442n7m20gucppydhq929z6vr72p9fk9ypal5m760etjq6xvrmj"),
        ],
    ),
    (
        "1of1-or-3of5-older",
        "wsh(or_d(pk(@0/<0;1>/*),and_v(v:thresh(3,pkh(@1/<0;1>/*),a:pkh(@2/<0;1>/*),a:pkh(@3/<0;1>/*),a:pkh(@4/<0;1>/*)),older(65535))))",
        "Testnet",
        TEST_XPUBS,
        [
            (0, 120, "tb1q57juettdzl7gjkg2cmmh4k9qyj3ffqr9w2wq5htna9juzadz39uqsgsr79"),
            (1, 120, "tb1qeanwcjlhljjh7r55ca272mpjqsrp8xq399tl8pc9u5mjw0leppfsvs9tlh"),
        ],
    ),
    (
        "5of5-decays-4of5-decays-3of5",
        "wsh(or_i(and_v(v:thresh(3,pkh(@0/<4;5>/*),a:pkh(@1/<4;5>/*),a:pkh(@2/<4;5>/*),a:pkh(@3/<4;5>/*),a:pkh(@4/<4;5>/*)),older(52596)),or_i(and_v(v:thresh(4,pkh(@0/<2;3>/*),a:pkh(@1/<2;3>/*),a:pkh(@2/<2;3>/*),a:pkh(@3/<2;3>/*),a:pkh(@4/<2;3>/*)),older(4383)),and_v(v:and_v(v:and_v(v:and_v(v:pk(@0/<0;1>/*),pk(@1/<0;1>/*)),pk(@2/<0;1>/*)),pk(@3/<0;1>/*)),pk(@4/<0;1>/*)))))",
        "Testnet",
        TEST_XPUBS,
        [
            (0, 1, "tb1qaxepwdnllqdudlk5d98ff4fmwdcwjj3q7x5hc0tjcwux25p4lqsq9f4mmv"),
            (1, 1, "tb1q257a0828hrwcd04y4rs7vcrlr8lcge5el9j4g6s8vtq5hknucx6sza36km"),
            (0, 2, "tb1qmxnl8yc0fkey5p2e4eeh3msdv8tsju6j98sp44vkjks0hz5yux0qvpzs74"),
            (1, 2, "tb1qz4ffyxpd2nkl6hkcy2gzqagtv7epsw4h6wxmspjz5ky4c4fgdsfqy46yea"),
        ],
    ),
    (
        "liana-simple1",
        "wsh(or_d(pk(@0/<0;1>/*),and_v(v:pkh(@1/<0;1>/*),older(1))))",
        "Signet",
        TEST_XPUBS,
        [
            (0, 0, "tb1q2selxcpsa9nv689nt00zjysudh8w0ampqypg0yx26wcjz0zjrl2q96hf5e"),
            (0, 1, "tb1qkz0pdqjf83nmgr8mlttwn5467vpxpm73anhs5ln0laq3cf3cx22qcxzkep"),
            (1, 0, "tb1qgkve9za3p6lasx4zuhcrmen3lmjfkrg9g7g63uy2zvp23e5gysksdedkwn"),
            (1, 1, "tb1qnf7zpt7nev8mau2a96mwl7epws88e6k8rv9vfa4wunyarysdx0msd9czyy"),
        ],
    ),
    (
        "liana-simple2",
        "wsh(or_d(pk(@0/<0;1>/*),and_v(v:pkh(@1/<0;1>/*),older(52596))))",
        "Signet",
        TEST_XPUBS,
        [
            (0, 1, "tb1q2cp2fxh68hw09cwc3ma8ecmkt6270vw35lww3hyuqskzjnemfa5qutwhqf"),
            (0, 2, "tb1qpcac9zfvjp5pw50dxjehh6y23e44xh2p45c45zsjgyvlvzg0ktkst64xeg"),
            (0, 3, "tb1qhwr4lr799xcs4ndgej87cvgg4lgd2we9kpk73t4ajvr0r902t7usmedptj"),
        ],
    ),
    (
        "liana-large",
        "wsh(or_i(and_v(v:thresh(1,pkh(@0/<6;7>/*),a:pkh(@1/<6;7>/*),a:pkh(@2/<6;7>/*),a:pkh(@3/<6;7>/*),a:pkh(@4/<6;7>/*),a:pkh(@5/<6;7>/*),a:pkh(@6/<6;7>/*),a:pkh(@7/<6;7>/*)),older(3)),or_i(and_v(v:thresh(4,pkh(@0/<4;5>/*),a:pkh(@1/<4;5>/*),a:pkh(@2/<4;5>/*),a:pkh(@3/<4;5>/*),a:pkh(@4/<4;5>/*),a:pkh(@5/<4;5>/*),a:pkh(@6/<4;5>/*),a:pkh(@7/<4;5>/*)),older(2)),or_i(and_v(v:thresh(6,pkh(@0/<2;3>/*),a:pkh(@1/<2;3>/*),a:pkh(@2/<2;3>/*),a:pkh(@3/<2;3>/*),a:pkh(@4/<2;3>/*),a:pkh(@5/<2;3>/*),a:pkh(@6/<2;3>/*),a:pkh(@7/<2;3>/*)),older(1)),and_v(v:and_v(v:and_v(v:and_v(v:and_v(v:and_v(v:and_v(v:pk(@0/<0;1>/*),pk(@1/<0;1>/*)),pk(@2/<0;1>/*)),pk(@3/<0;1>/*)),pk(@4/<0;1>/*)),pk(@5/<0;1>/*)),pk(@6/<0;1>/*)),pk(@7/<0;1>/*))))))",
        "Signet",
        TEST_XPUBS,
        [
            (0, 1, "tb1qyt2q5ns8z88fj7n7gpxnvqp0frxjx8fnl7k6cywtneak8pq0a33sefyrd8"),
            (0, 2, "tb1q9yxxpms7d3kt4l8zf0g782hykquklmhye507a5q6n605fr50ht6s8l5afw"),
            (0, 3, "tb1qk7gyeu0nh7p8u8zc5d8jg8pxrc4ma4pj56f058g3smmhm3rw87xq03jklx"),
            (1, 1, "tb1qpg949j8wvaarryw7nt9x4pyh7tnjfta0dcef7pldvvu334rprxdsmtfa2g"),
            (1, 2, "tb1qdmrkhfw0hxftqe7h0jh94pmyk3xxzl72uxzj2w6pkkq3r23l6vxq8tmglk"),
            (1, 3, "tb1qktvztjh0zx804nwtmya3z4g8y6wn69x3vm095x7xtansjwvarmts357lde"),
        ],
    ),
]


def _from_bip388(desc: str, keys: list[Key]) -> Descriptor:
    for i, k in enumerate(keys):
        desc = desc.replace(f"@{i}", k.to_string())

    try:
        return Descriptor.from_string(desc)
    except Exception as e:
        raise ValueError(desc) from e


@pytest.mark.parametrize(
    "name, desc, coin, keys, tests",
    (pytest.param(name, *args, id=name) for name, *args in DATA),
)
def test_miniscript_get_address(
    session: Session,
    name: str,
    desc: str,
    coin: str,
    keys: list[Key],
    tests: list[tuple[int, int, str]],
):
    indices = set(map(int, re.findall("@(\\d+)", desc)))
    assert min(indices) == 0
    assert max(indices) == len(indices) - 1
    keys = keys[: len(indices)]
    assert len(indices) == len(keys)

    descriptor = _from_bip388(desc, keys)
    for k in descriptor.keys:
        assert len(k.branches) == 2

    policy = btc.register_policy(
        session,
        name=name,
        descriptor=desc,
        keys=list(map(_to_protobuf, keys)),
        coin_name=coin,
    )
    fpr = session.get_root_fingerprint()
    keys = [k for k in keys if k.fingerprint == fpr]  # drop unrelated keys
    assert keys

    for internal, index, expected in tests:
        internal = bool(internal)
        address = btc.get_miniscript_address(
            session,
            policy,
            messages.MiniscriptDerivation(internal=internal, index=index),
            coin_name=coin,
            show_display=True,
        ).address
        assert address == expected


def test_miniscript_spend_liana(session: Session):
    COIN = "Signet"
    # 1st always, or 2nd after 1 block
    DESC = "wsh(or_d(pk(@0/<0;1>/*),and_v(v:pkh(@1/<0;1>/*),older(52596))))"
    TPUBS = _parse_keys(
        "[5c9e228d/48'/1'/0'/2']tpubDEGquuorgFNbDrg8vepq1HnaV2mgQu9TcSBgBYfXw4AX8VMgkWqvkxHNuJmiah8iVnA3Hgj4cSvaGAXEnq814yC6hMEreckLsd7zyLL3o76",  # ALL x 12
        "[72758bc3/84'/1'/0']tpubDCNhwLKYSSu2FKssoMziAdwhAAKS3bASH7wZYkNmJ7sU5hW9LgDaAQPqe7ivAkskSF29B1CkRRg4g2mbovXgAL9Mby6i9xBdhZh2txDeSLb",  # GYM x 12
    )
    keys = list(map(_to_protobuf, TPUBS))

    node = btc.get_public_node(session, parse_path("m/48h/1h/0h/2h"), coin_name=COIN)
    assert _to_protobuf(Key.from_string(node.xpub)).node == keys[0].node

    policy = btc.register_policy(
        session, name="Liana", descriptor=DESC, keys=keys, coin_name=COIN
    )
    derivation = messages.MiniscriptDerivation(internal=False, index=1)
    redeem = messages.MiniscriptRedeemPolicyType(policy_index=0, derivation=derivation)
    addr = btc.get_miniscript_address(session, policy, derivation, COIN).address
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
        policies=[policy],
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
    COIN = "Signet"
    # 2-of-2, decays to 1-of-2
    DESC = "wsh(or_i(and_v(v:thresh(1,pkh(@1/<2;3>/*),a:pkh(@0/<2;3>/*)),older(1)),and_v(v:pk(@0/<0;1>/*),pk(@1/<0;1>/*))))"
    TPUBS = _parse_keys(
        "[5c9e228d/48'/1'/0'/2']tpubDEGquuorgFNbDrg8vepq1HnaV2mgQu9TcSBgBYfXw4AX8VMgkWqvkxHNuJmiah8iVnA3Hgj4cSvaGAXEnq814yC6hMEreckLsd7zyLL3o76",  # ALL x 12
        "[6d96bc8f/48'/1'/0'/2']tpubDFNKLpb6iPByHNd6MRa7gxfAa97aTdtzwp17owgyLp9FFbkAuW1gMfD4Vrn7uVssvYfhiG41eHKmb2kaPz5qhqszYybAfiaBATMv8XfrGvg",  # ALL x 12, passphrase='a'
    )
    keys = [_to_protobuf(key) for key in TPUBS]

    node = btc.get_public_node(session, parse_path("m/48h/1h/0h/2h"), coin_name=COIN)
    assert node.node == keys[0].node
    pubkey = HDKey.from_string(node.xpub).derive("m/1/3").key

    policy = btc.register_policy(
        session, name="Liana", descriptor=DESC, keys=keys, coin_name=COIN
    )

    # Spend from primary path
    derivation = messages.MiniscriptDerivation(internal=True, index=3)
    redeem = messages.MiniscriptRedeemPolicyType(policy_index=0, derivation=derivation)
    addr = btc.get_miniscript_address(session, policy, derivation, COIN).address
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
        policies=[policy],
    )
    assert len(signatures) == 1
    assert (
        signatures[0].hex()
        == "3045022100c6e2d81a8b4f03371f0e7687fe1a45ac128beaf79afba8725b849e0807cadb2402202f464a9a9d14b959262179f52afe1874391a7556e887a083a1091aa44c7b89ab"
    )

    # Spend from recovery path
    derivation = messages.MiniscriptDerivation(internal=False, index=2)
    redeem = messages.MiniscriptRedeemPolicyType(policy_index=0, derivation=derivation)
    addr = btc.get_miniscript_address(session, policy, derivation, COIN).address
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
        policies=[policy],
    )
    assert len(signatures) == 1
    assert (
        signatures[0].hex()
        == "3045022100a0189c2c2b57aeb522c2737c52039e8d4f3d197c31a28330822c0aa0ae01d15f022023020852beec45a2052e4c54822825d530a5bfc9bdfb88a3c38669bfea4657a2"
    )


@pytest.mark.setup_client(passphrase=True)
def test_miniscript_spend_sparrow(session: Session):
    COIN = "Signet"
    DESC = "wsh(sortedmulti(2,@0/<0;1>/*,@1/<0;1>/*,@2/<0;1>/*))"

    # 2-of-3 multisig
    TPUBS = _parse_keys(
        "[5c9e228d/48h/1h/0h/2h]tpubDEGquuorgFNbDrg8vepq1HnaV2mgQu9TcSBgBYfXw4AX8VMgkWqvkxHNuJmiah8iVnA3Hgj4cSvaGAXEnq814yC6hMEreckLsd7zyLL3o76",  # ALL x 12, no passphrase
        "[6d96bc8f/48h/1h/0h/2h]tpubDFNKLpb6iPByHNd6MRa7gxfAa97aTdtzwp17owgyLp9FFbkAuW1gMfD4Vrn7uVssvYfhiG41eHKmb2kaPz5qhqszYybAfiaBATMv8XfrGvg",  # ALL x 12, passphrase='a'
        "[cab51272/48h/1h/0h/2h]tpubDEbN34MtnQ1LWCT8Z1XKUHeB9tY9ebA4e7P84W5gmAMpqKiud1UWRN2ym68p1ijZ4kxAFqmPPAJVvYNPjopEj4cMUXCS8toffucdDgdXVok",  # ALL x 12, passphrase='d'
    )
    keys = list(map(_to_protobuf, TPUBS))
    policy = btc.register_policy(
        session, name="2-of-3", descriptor=DESC, keys=keys, coin_name=COIN
    )
    VECTORS = [
        (
            # external
            "tb1q4wrndh4nmzs43mcdv6c7wftda6w9urzfvqt33xl6h77cnytuksxqss4y8c",
            "tb1qes4nf8qaud4mac0es9nytzk0kky26ymdx64mnu6hwn3kmx7f4wfs8q7cnz",
            "tb1qknf9mz4qm5p8xfznvntsndyptncxt756nmcgyvft6rauc3cghecqq0d2fk",
        ),
        (
            # internal
            "tb1q8e0wu6cp3zund45d229d08svwf0xpe3ctsl75m7aupdtnt5u525s3ffg7h",
            "tb1qqusplm8zcf2923zr5p46tkjff4vs43f2zh7kymyx7uttxww25ams4e9kly",
            "tb1qn5ntykjvq6jc5tcejx8ujpl70d5ahkjh4309hm0nj9x0pkkcf28qsxjeux",
        ),
    ]
    for internal, addrs in enumerate(VECTORS):
        for index, addr in enumerate(addrs):
            res = btc.get_miniscript_address(
                session,
                policy=policy,
                derivation=messages.MiniscriptDerivation(
                    internal=bool(internal), index=index
                ),
                coin_name=COIN,
            )
            assert addr == res.address

    client = session.client
    expected_sigs = [
        "304402202ef958e880e7b4941983ecd2be4aec62c4160e81971992c2ddc87caec76435bf02207ee489081cfa2c0bed32feeaf1554683435ffa8ecb2caa42c80d1d626cef4b54",
        "3044022023924b17e02e72172270562f92442eb17dba63f4bb87b1edd57515bda66ca56a0220413abaf216b5f5adb955242dd1b43a2f0ac02a05a0a783d2611bd855307ea4ab",
        "3045022100c50d7f39af5bffac21c8249e340455e7b038b3e5d509632932db06ba7ac53ccb02204f7323e8d4c7e82e8211d02abcab24634686c74be3ff915f457fbc395f0bdcd4",
    ]
    for i, passphrase in enumerate(("", "a", "d")):
        session = client.get_session(passphrase=passphrase)
        node = btc.get_public_node(
            session, parse_path("m/48h/1h/0h/2h"), coin_name=COIN
        )
        assert node.node == keys[i].node

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
                miniscript=messages.MiniscriptRedeemPolicyType(
                    policy_index=0,
                    derivation=messages.MiniscriptDerivation(internal=False, index=0),
                ),
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
            policies=[policy],
        )
        # https://mempool.space/signet/tx/9805d1cd6fe5cf8206d34a9f346ba105d3043931f610b7ed657e144c8b522df1
        assert len(signatures) == 1
        assert signatures[0].hex() == expected_sigs[i]


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
