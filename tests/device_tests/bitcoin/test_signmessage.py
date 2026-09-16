# This file is part of the Trezor project.
#
# Copyright (C) 2012-2019 SatoshiLabs and contributors
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

from typing import Any

import pytest

from trezorlib import btc, messages
from trezorlib.debuglink import DebugSession as Session
from trezorlib.debuglink import LayoutType, message_filters
from trezorlib.exceptions import Cancelled, TrezorFailure
from trezorlib.tools import parse_path

from ...common import is_core
from ...input_flows import (
    InputFlowConfirmAllWarnings,
    InputFlowSignMessageInfo,
    InputFlowSignMessagePagination,
    InputFlowSignVerifyMessageLong,
)

S = messages.InputScriptType


def case(
    id: str,
    *args: Any,
    models: str | None = None,
    altcoin: bool = False,
):
    marks = []
    if altcoin:
        marks.append(pytest.mark.altcoin)
    if models:
        marks.append(pytest.mark.models(models))
    return pytest.param(*args, id=id, marks=marks)


MESSAGE_NFKD = "Pr\u030ci\u0301s\u030cerne\u030c z\u030clut\u030couc\u030cky\u0301 ku\u030an\u030c u\u0301pe\u030cl d\u030ca\u0301belske\u0301 o\u0301dy za\u0301ker\u030cny\u0301 uc\u030cen\u030c be\u030cz\u030ci\u0301 pode\u0301l zo\u0301ny u\u0301lu\u030a"
MESSAGE_NFC = "P\u0159\xed\u0161ern\u011b \u017elu\u0165ou\u010dk\xfd k\u016f\u0148 \xfap\u011bl \u010f\xe1belsk\xe9 \xf3dy z\xe1ke\u0159n\xfd u\u010de\u0148 b\u011b\u017e\xed pod\xe9l z\xf3ny \xfal\u016f"
NFKD_NFC_SIGNATURE = "2046a0b46e81492f82e0412c73701b9740e6462c603575ee2d36c7d7b4c20f0f33763ca8cb3027ea8e1ce5e83fda8b6746fea8f5c82655d78fd419e7c766a5e17a"

VECTORS = (  # case name, coin_name, path, script_type, address, message, signature
    # ==== Bitcoin script types ====
    case(
        "p2pkh",
        "Bitcoin",
        "m/44h/0h/0h/0/0",
        S.SPENDADDRESS,
        False,
        "1JAd7XCBzGudGpJQSDSfpmJhiygtLQWaGL",
        "This is an example of a signed message.",
        "20fd8f2f7db5238fcdd077d5204c3e6949c261d700269cefc1d9d2dcef6b95023630ee617f6c8acf9eb40c8edd704c9ca74ea4afc393f43f35b4e8958324cbdd1c",
    ),
    case(
        "segwit-p2sh",
        "Bitcoin",
        "m/49h/0h/0h/0/0",
        S.SPENDP2SHWITNESS,
        False,
        "3L6TyTisPBmrDAj6RoKmDzNnj4eQi54gD2",
        "This is an example of a signed message.",
        "23744de4516fac5c140808015664516a32fead94de89775cec7e24dbc24fe133075ac09301c4cc8e197bea4b6481661d5b8e9bf19d8b7b8a382ecdb53c2ee0750d",
    ),
    case(
        "segwit-native",
        "Bitcoin",
        "m/84h/0h/0h/0/0",
        S.SPENDWITNESS,
        False,
        "bc1qannfxke2tfd4l7vhepehpvt05y83v3qsf6nfkk",
        "This is an example of a signed message.",
        "28b55d7600d9e9a7e2a49155ddf3cfdb8e796c207faab833010fa41fb7828889bc47cf62348a7aaa0923c0832a589fab541e8f12eb54fb711c90e2307f0f66b194",
    ),
    case(
        "p2pkh",
        "Bitcoin",
        "m/44h/0h/0h/0/0",
        S.SPENDADDRESS,
        True,
        "1JAd7XCBzGudGpJQSDSfpmJhiygtLQWaGL",
        "This is an example of a signed message.",
        "20fd8f2f7db5238fcdd077d5204c3e6949c261d700269cefc1d9d2dcef6b95023630ee617f6c8acf9eb40c8edd704c9ca74ea4afc393f43f35b4e8958324cbdd1c",
    ),
    case(
        "segwit-p2sh",
        "Bitcoin",
        "m/49h/0h/0h/0/0",
        S.SPENDP2SHWITNESS,
        True,
        "3L6TyTisPBmrDAj6RoKmDzNnj4eQi54gD2",
        "This is an example of a signed message.",
        "1f744de4516fac5c140808015664516a32fead94de89775cec7e24dbc24fe133075ac09301c4cc8e197bea4b6481661d5b8e9bf19d8b7b8a382ecdb53c2ee0750d",
    ),
    case(
        "segwit-native",
        "Bitcoin",
        "m/84h/0h/0h/0/0",
        S.SPENDWITNESS,
        True,
        "bc1qannfxke2tfd4l7vhepehpvt05y83v3qsf6nfkk",
        "This is an example of a signed message.",
        "20b55d7600d9e9a7e2a49155ddf3cfdb8e796c207faab833010fa41fb7828889bc47cf62348a7aaa0923c0832a589fab541e8f12eb54fb711c90e2307f0f66b194",
    ),
    # ==== NFKD vs NFC message - signatures must be identical ====
    case(
        "NFKD message",
        "Bitcoin",
        "m/44h/0h/0h/0/1",
        S.SPENDADDRESS,
        False,
        "1GWFxtwWmNVqotUPXLcKVL2mUKpshuJYo",
        MESSAGE_NFKD,
        NFKD_NFC_SIGNATURE,
    ),
    case(
        "NFC message",
        "Bitcoin",
        "m/44h/0h/0h/0/1",
        S.SPENDADDRESS,
        False,
        "1GWFxtwWmNVqotUPXLcKVL2mUKpshuJYo",
        MESSAGE_NFC,
        NFKD_NFC_SIGNATURE,
    ),
    # ==== T1 FW signing ====
    case(
        "t1 firmware path",
        "Bitcoin",
        "m/10026'/826421588'/2'/0'",
        S.SPENDADDRESS,
        False,
        "1FoHjQT6bAEu2FQGzTgqj4PBneoiCAk4ZN",
        b"BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB",
        "1f40ae58dd68480a2f39eecf4decfe79ceacde3f865502db67c083b8465b33535c0750d5377b7ac62e534f71c922cd029f659761f8ac99e859df36322c5b320eff",
        models="core",
    ),
    # ==== Testnet script types ====
    case(
        "p2pkh",
        "Testnet",
        "m/44h/1h/0h/0/0",
        S.SPENDADDRESS,
        False,
        "mvbu1Gdy8SUjTenqerxUaZyYjmveZvt33q",
        "This is an example of a signed message.",
        "2030cd7f116c0481d1936cfef48137fd23ee56aaf00787bfa08a94837466ec9909390c3efacfc56bae5782f1db4cf49ae05f242b5f62a47f871ec46bf1a3253e7f",
    ),
    case(
        "segwit-p2sh",
        "Testnet",
        "m/49h/1h/0h/0/0",
        S.SPENDP2SHWITNESS,
        False,
        "2N4Q5FhU2497BryFfUgbqkAJE87aKHUhXMp",
        "This is an example of a signed message.",
        "23ef39fd388c3425d6aaa04274dcd5c7dd4c283a411b616443474fbcde5dd966050d91bc7c57e9578f28efdd84c9a9bcba415f93c5727b5d3f2bf3de46d7084896",
    ),
    case(
        "segwit-native",
        "Testnet",
        "m/84h/1h/0h/0/0",
        S.SPENDWITNESS,
        False,
        "tb1qkvwu9g3k2pdxewfqr7syz89r3gj557l3uuf9r9",
        "This is an example of a signed message.",
        "27758b3393396ad9fe48f6ce81f63410145e7b2b69a5dfc1d48b5e6e623e91e08e3afb60bda1546f9c6f9fb5bd0a41887b784c266036dd4b4015a0abc1137daa1d",
    ),
    # ==== Altcoins ====
    case(
        "bcash",
        "Bcash",
        "m/44h/145h/0h/0/0",
        S.SPENDADDRESS,
        False,
        "bitcoincash:qr08q88p9etk89wgv05nwlrkm4l0urz4cyl36hh9sv",
        "This is an example of a signed message.",
        "1fda7733e666a4ab8ba86f3cfc3728d318ecf824a3bf99597570297aa131607c10316959136b2c500b2b478a73c563ba314c0b7b2a22065b6d9596118f246d360e",
        altcoin=True,
    ),
    case(
        "grs-p2pkh",
        "Groestlcoin",
        "m/44h/17h/0h/0/0",
        S.SPENDADDRESS,
        False,
        "Fj62rBJi8LvbmWu2jzkaUX1NFXLEqDLoZM",
        "test",
        "20d39869afe38fc631cf7983e64f9b65f5268e48c1f55ce857874d1bbf91b015322b7d312fb23dc8c816595bec2f8e82e7242dc6d658d1c45193babd37a6fe6133",
        altcoin=True,
    ),
    case(
        "grs-segwit-p2sh",
        "Groestlcoin",
        "m/49h/17h/0h/0/0",
        S.SPENDP2SHWITNESS,
        False,
        "31inaRqambLsd9D7Ke4USZmGEVd3PHkh7P",
        "test",
        "23f340fc9f9ea6469e13dbc743b70313e4d076bcd8ce867eddd71ec41160d02a4a462205d21ec6e49502bf3e2a8463d48e895ca56f6b385b15ec2cc7556292ecae",
        altcoin=True,
    ),
    case(
        "grs-segwit-native",
        "Groestlcoin",
        "m/84h/17h/0h/0/0",
        S.SPENDWITNESS,
        False,
        "grs1qw4teyraux2s77nhjdwh9ar8rl9dt7zww8r6lne",
        "test",
        "288253db4b4a1d5dac059296385310a353ef80992c4777a44133a335d12d3444da6c287d32aec4071ec49ae327e208f89ba0a115a129f106221c8dd5590fd3df13",
        altcoin=True,
    ),
    case(
        "decred",
        "Decred",
        "m/44h/42h/0h/0/0",
        S.SPENDADDRESS,
        False,
        "DsZtHtXHwvNR3nWf1PqfxrEdnRJisKEyzp1",
        "This is an example of a signed message.",
        "206b1f8ba47ef9eaf87aa900e41ab1e97f67e8c09292faa4acf825228d074c4b774484046dcb1d9bbf0603045dbfb328c3e1b0c09c5ae133e89e604a67a1fc6cca",
        altcoin=True,
        models="t1b1,t2t1",
    ),
    case(
        "decred-empty",
        "Decred",
        "m/44h/42h/0h/0/0",
        S.SPENDADDRESS,
        False,
        "DsZtHtXHwvNR3nWf1PqfxrEdnRJisKEyzp1",
        "",
        "1fd2d57490b44a0361c7809768cad032d41ba1d4b7a297f935fc65ae05f71de7ea0c6c6fd265cc5154f1fa4acd7006b6a00ddd67fb7333c1594aff9120b3ba8024",
        altcoin=True,
        models="t1b1,t2t1",
    ),
)


VECTORS_LONG_MESSAGE = (
    # ==== Bitcoin with long message ====
    case(
        "p2pkh long message",
        "Bitcoin",
        "m/44h/0h/0h/0/0",
        S.SPENDADDRESS,
        False,
        "1JAd7XCBzGudGpJQSDSfpmJhiygtLQWaGL",
        "VeryLongMessage!" * 64,
        "200a46476ceb84d06ef5784828026f922c8815f57aac837b8c013007ca8a8460db63ef917dbebaebd108b1c814bbeea6db1f2b2241a958e53fe715cc86b199d9c3",
    ),
    case(
        "segwit-p2sh long message",
        "Bitcoin",
        "m/49h/0h/0h/0/0",
        S.SPENDP2SHWITNESS,
        False,
        "3L6TyTisPBmrDAj6RoKmDzNnj4eQi54gD2",
        "VeryLongMessage!" * 64,
        "236eadee380684f70749c52141c8aa7c3b6afd84d0e5f38cfa71823f3b1105a5f34e23834a5bb6f239ff28ad87f409f44e4ce6269754adc00388b19507a5d9386f",
    ),
    case(
        "segwit-native long message",
        "Bitcoin",
        "m/84h/0h/0h/0/0",
        S.SPENDWITNESS,
        False,
        "bc1qannfxke2tfd4l7vhepehpvt05y83v3qsf6nfkk",
        "VeryLongMessage!" * 64,
        "28c6f86e255eaa768c447d635d91da01631ac54af223c2c182d4fa3676cfecae4a199ad33a74fe04fb46c39432acb8d83de74da90f5f01123b3b7d8bc252bc7f71",
    ),
)


@pytest.mark.parametrize(
    "coin_name, path, script_type, no_script_type, address, message, signature", VECTORS
)
def test_signmessage(
    session: Session,
    coin_name: str,
    path: str,
    script_type: messages.InputScriptType,
    no_script_type: bool,
    address: str,
    message: str,
    signature: str,
):
    sig = btc.sign_message(
        session,
        coin_name=coin_name,
        n=parse_path(path),
        script_type=script_type,
        no_script_type=no_script_type,
        message=message,
    )
    assert sig.address == address
    assert sig.signature.hex() == signature


@pytest.mark.models("core")
@pytest.mark.parametrize(
    "coin_name, path, script_type, no_script_type, address, message, signature",
    VECTORS_LONG_MESSAGE,
)
def test_signmessage_long(
    session: Session,
    coin_name: str,
    path: str,
    script_type: messages.InputScriptType,
    no_script_type: bool,
    address: str,
    message: str,
    signature: str,
):
    with session.test_ctx as client:
        IF = InputFlowSignVerifyMessageLong(session)
        client.set_input_flow(IF.get())
        sig = btc.sign_message(
            session,
            coin_name=coin_name,
            n=parse_path(path),
            script_type=script_type,
            no_script_type=no_script_type,
            message=message,
        )
        assert sig.address == address
        assert sig.signature.hex() == signature


@pytest.mark.models("core", skip=["safe3"], reason="Not implemented")
@pytest.mark.parametrize(
    "coin_name, path, script_type, no_script_type, address, message, signature", VECTORS
)
def test_signmessage_info(
    session: Session,
    coin_name: str,
    path: str,
    script_type: messages.InputScriptType,
    no_script_type: bool,
    address: str,
    message: str,
    signature: str,
):
    with session.test_ctx as client, pytest.raises(Cancelled):
        IF = InputFlowSignMessageInfo(session)
        client.set_input_flow(IF.get())
        sig = btc.sign_message(
            session,
            coin_name=coin_name,
            n=parse_path(path),
            script_type=script_type,
            no_script_type=no_script_type,
            message=message,
            chunkify=True,
        )
        assert sig.address == address
        assert sig.signature.hex() == signature


MESSAGE_LENGTHS = (
    pytest.param("This is a very long message. " * 16, False, id="normal_text"),
    pytest.param("ThisIsAMessageWithoutSpaces" * 16, False, id="no_spaces"),
    pytest.param("ThisIsAMessageWithLongWords " * 16, False, id="long_words"),
    pytest.param(
        "This\nmessage\nhas\nnewlines\nafter\nevery\nsingle\nword", False, id="newlines"
    ),
    pytest.param(
        "Příšerně žluťoučký kůň úpěl ďábelské ódy. " * 16, True, id="utf_text"
    ),
    pytest.param("PříšerněŽluťoučkýKůňÚpělĎábelskéÓdy" * 16, True, id="utf_nospace"),
    pytest.param("1\n2\n3\n4\n5\n6\n7", False, id="single_line_over"),
)

MESSAGE_LENGTHS_ECKHART = (
    pytest.param("This is a very long message. " * 27, False, id="normal_text"),
    pytest.param("ThisIsAMessageWithoutSpaces" * 29, False, id="no_spaces"),
    pytest.param("ThisIsAMessageWithLongWords " * 28, False, id="long_words"),
    pytest.param(
        "This\nmessage\nhas\nnewlines\nafter\nevery\nsingle\none\nword",
        False,
        id="newlines",
    ),
    pytest.param(
        "Příšerně žluťoučký kůň úpěl ďábelské ódy. " * 19, True, id="utf_text"
    ),
    pytest.param("PříšerněŽluťoučkýKůňÚpělĎábelskéÓdy" * 23, True, id="utf_nospace"),
    pytest.param("1\n2\n3\n4\n5\n6\n7\n8\n9", False, id="single_line_over"),
)


def _pagination_test(session: Session, message: str, is_long: bool):

    with session.test_ctx as client:
        IF = (
            InputFlowSignVerifyMessageLong
            if is_long
            else InputFlowSignMessagePagination
        )(session)
        client.set_input_flow(IF.get())
        btc.sign_message(
            session,
            coin_name="Bitcoin",
            n=parse_path("m/44h/0h/0h/0/0"),
            message=message,
        )

    message_read = IF.message_read.replace(" ", "").replace("...", "")
    signed_message = message.replace("\n", "").replace(" ", "")

    if session.layout_type in (
        LayoutType.Bolt,
        LayoutType.Delizia,
        LayoutType.Eckhart,
    ):
        assert signed_message in message_read


@pytest.mark.models(
    "core",
    skip=["eckhart"],
    reason="Test with different parameters implemented for eckhart",
)
@pytest.mark.parametrize("message,is_long", MESSAGE_LENGTHS)
def test_signmessage_pagination(session: Session, message: str, is_long: bool):
    _pagination_test(session, message, is_long)


@pytest.mark.models("eckhart")
@pytest.mark.parametrize("message,is_long", MESSAGE_LENGTHS_ECKHART)
def test_signmessage_pagination_eckhart(session: Session, message: str, is_long: bool):
    _pagination_test(session, message, is_long)


@pytest.mark.models("t2t1", reason="Tailored to TT fonts and screen size")
def test_signmessage_pagination_trailing_newline(session: Session):
    message = "THIS\nMUST\nNOT\nBE\nPAGINATED\n"
    # The trailing newline must not cause a new paginated screen to appear.
    # The UI must be a single dialog without pagination.
    with session.test_ctx as client:
        client.set_expected_responses(
            [
                # expect address confirmation
                message_filters.ButtonRequest(code=messages.ButtonRequestType.Other),
                # expect a ButtonRequest for a single-page screen
                message_filters.ButtonRequest(pages=1),
                messages.MessageSignature,
            ]
        )
        btc.sign_message(
            session,
            coin_name="Bitcoin",
            n=parse_path("m/44h/0h/0h/0/0"),
            message=message,
        )


def test_signmessage_path_warning(session: Session):
    message = "This is an example of a signed message."

    with session.test_ctx as client:
        client.set_expected_responses(
            [
                # expect a path warning
                message_filters.ButtonRequest(
                    code=messages.ButtonRequestType.UnknownDerivationPath
                ),
                message_filters.ButtonRequest(code=messages.ButtonRequestType.Other),
                message_filters.ButtonRequest(code=messages.ButtonRequestType.Other),
                messages.MessageSignature,
            ]
        )
        if is_core(session):
            IF = InputFlowConfirmAllWarnings(session)
            client.set_input_flow(IF.get())
        btc.sign_message(
            session,
            coin_name="Bitcoin",
            n=parse_path("m/86h/0h/0h/0/0"),
            message=message,
            script_type=messages.InputScriptType.SPENDWITNESS,
        )


# BIP-48 message signing, see #7717. The whole permission surface, one
# trezorctl invocation per row:
#
#     trezorctl btc sign-message -n "<path>" -t <script type> "hello"

MESSAGE = "This is an example of a signed message."

# Not in the keychain, so refused outright rather than warned about.
FORBIDDEN = "forbidden"
# Signs, but shows the unknown derivation path screen first.
WARN = "warn"
# Signs with no warning.
SIGNS = "signs"


VECTORS_BIP48_MATRIX = (  # path, script_type, expected
    # 0h is the legacy-multisig level; message signing is single-key, so it
    # signs as p2pkh and trezorctl sends SPENDADDRESS rather than SPENDMULTISIG
    pytest.param("m/48h/0h/0h/0h", S.SPENDADDRESS, SIGNS, id="account_0h-address"),
    pytest.param(
        "m/48h/0h/0h/0h", S.SPENDP2SHWITNESS, FORBIDDEN, id="account_0h-p2shsegwit"
    ),
    pytest.param("m/48h/0h/0h/0h", S.SPENDWITNESS, FORBIDDEN, id="account_0h-segwit"),
    pytest.param("m/48h/0h/0h/0h/0/0", S.SPENDADDRESS, SIGNS, id="leaf_0h-address"),
    pytest.param(
        "m/48h/0h/0h/0h/0/0", S.SPENDP2SHWITNESS, WARN, id="leaf_0h-p2shsegwit"
    ),
    pytest.param("m/48h/0h/0h/0h/0/0", S.SPENDWITNESS, WARN, id="leaf_0h-segwit"),
    # 1h is the P2SH-segwit level
    pytest.param("m/48h/0h/0h/1h", S.SPENDADDRESS, FORBIDDEN, id="account_1h-address"),
    pytest.param(
        "m/48h/0h/0h/1h", S.SPENDP2SHWITNESS, SIGNS, id="account_1h-p2shsegwit"
    ),
    pytest.param("m/48h/0h/0h/1h", S.SPENDWITNESS, FORBIDDEN, id="account_1h-segwit"),
    pytest.param("m/48h/0h/0h/1h/0/0", S.SPENDADDRESS, WARN, id="leaf_1h-address"),
    pytest.param(
        "m/48h/0h/0h/1h/0/0", S.SPENDP2SHWITNESS, SIGNS, id="leaf_1h-p2shsegwit"
    ),
    pytest.param("m/48h/0h/0h/1h/0/0", S.SPENDWITNESS, WARN, id="leaf_1h-segwit"),
    # 2h is the native-segwit level -- the paths reported in #7717
    pytest.param("m/48h/0h/0h/2h", S.SPENDADDRESS, FORBIDDEN, id="account_2h-address"),
    pytest.param(
        "m/48h/0h/0h/2h", S.SPENDP2SHWITNESS, FORBIDDEN, id="account_2h-p2shsegwit"
    ),
    pytest.param("m/48h/0h/0h/2h", S.SPENDWITNESS, SIGNS, id="account_2h-segwit"),
    pytest.param("m/48h/0h/0h/2h/0/0", S.SPENDADDRESS, WARN, id="leaf_2h-address"),
    pytest.param(
        "m/48h/0h/0h/2h/0/0", S.SPENDP2SHWITNESS, WARN, id="leaf_2h-p2shsegwit"
    ),
    pytest.param("m/48h/0h/0h/2h/0/0", S.SPENDWITNESS, SIGNS, id="leaf_2h-segwit"),
)

LEGACY_LEVEL_EXPECTED = SIGNS


def _assert_sign_message(
    session: Session,
    path: str,
    script_type: messages.InputScriptType,
    expected: str,
):
    if expected == FORBIDDEN:
        with pytest.raises(TrezorFailure, match="Forbidden key path") as exc:
            btc.sign_message(
                session,
                coin_name="Bitcoin",
                n=parse_path(path),
                message=MESSAGE,
                script_type=script_type,
            )
        # DataError is what the issue's HWI transcript shows as code -13.
        assert exc.value.code is messages.FailureType.DataError
        return

    expected_responses = []
    if expected == WARN:
        expected_responses.append(
            message_filters.ButtonRequest(
                code=messages.ButtonRequestType.UnknownDerivationPath
            )
        )
    expected_responses += [
        message_filters.ButtonRequest(code=messages.ButtonRequestType.Other),
        message_filters.ButtonRequest(code=messages.ButtonRequestType.Other),
        messages.MessageSignature,
    ]

    with session.test_ctx as client:
        client.set_expected_responses(expected_responses)
        if is_core(session):
            IF = InputFlowConfirmAllWarnings(session)
            client.set_input_flow(IF.get())
        sig = btc.sign_message(
            session,
            coin_name="Bitcoin",
            n=parse_path(path),
            message=MESSAGE,
            script_type=script_type,
        )

    assert sig.signature


@pytest.mark.parametrize("path, script_type, expected", VECTORS_BIP48_MATRIX)
def test_signmessage_bip48_matrix(
    session: Session,
    path: str,
    script_type: messages.InputScriptType,
    expected: str,
):
    _assert_sign_message(session, path, script_type, expected)


# These follow from the ordinary path patterns, nothing BIP-48 specific.

VECTORS_SIGNMESSAGE_LENIENCY = (  # path, script_type, expected
    # The BIP-45 cosigner node: PATTERN_BIP45 is unhardened below m/45'
    pytest.param("m/45h", S.SPENDADDRESS, SIGNS, id="bip45_cosigner_node"),
    # ...and a leaf under it
    pytest.param("m/45h/0/0/0", S.SPENDADDRESS, SIGNS, id="bip45_leaf"),
    # Unchained, whose account level is hardened
    pytest.param("m/45h/0h/0h/1000000/0/0", S.SPENDADDRESS, SIGNS, id="unchained_leaf"),
    # An ordinary account node, where any wallet shares its xpub
    pytest.param("m/44h/0h/0h", S.SPENDADDRESS, SIGNS, id="bip44_account"),
    pytest.param("m/84h/0h/0h", S.SPENDWITNESS, SIGNS, id="bip84_account"),
    # The script type still has to match the purpose
    pytest.param("m/44h/0h/0h", S.SPENDWITNESS, FORBIDDEN, id="bip44_account-segwit"),
    # A pattern with no hardened component has no export point, so the root
    # stays withheld
    pytest.param("m", S.SPENDADDRESS, FORBIDDEN, id="root"),
)


@pytest.mark.parametrize("path, script_type, expected", VECTORS_SIGNMESSAGE_LENIENCY)
def test_signmessage_leniency(
    session: Session,
    path: str,
    script_type: messages.InputScriptType,
    expected: str,
):
    _assert_sign_message(session, path, script_type, expected)


def test_signmessage_bip48_legacy_level_signs_as_p2pkh(session: Session):
    # The path alone reads as SPENDMULTISIG, but there is no multisig message
    # signature, so trezorctl sends the single-key analogue.
    from trezorlib.cli.btc import guess_script_type_from_path

    address_n = parse_path("m/48h/0h/0h/0h/0/0")
    assert guess_script_type_from_path(address_n) is S.SPENDMULTISIG

    expected_responses = []
    if LEGACY_LEVEL_EXPECTED == WARN:
        expected_responses.append(
            message_filters.ButtonRequest(
                code=messages.ButtonRequestType.UnknownDerivationPath
            )
        )
    expected_responses += [
        message_filters.ButtonRequest(code=messages.ButtonRequestType.Other),
        message_filters.ButtonRequest(code=messages.ButtonRequestType.Other),
        messages.MessageSignature,
    ]

    with session.test_ctx as client:
        client.set_expected_responses(expected_responses)
        if is_core(session):
            IF = InputFlowConfirmAllWarnings(session)
            client.set_input_flow(IF.get())
        sig = btc.sign_message(
            session,
            coin_name="Bitcoin",
            n=address_n,
            message=MESSAGE,
            script_type=S.SPENDADDRESS,
        )

    assert sig.signature
    assert sig.address.startswith("1")


@pytest.mark.models("core")
def test_signmessage_slip25_still_requires_unlock_path(session: Session):
    # The account-node grant must not reach the coinjoin account.
    with pytest.raises(TrezorFailure, match="Forbidden key path"):
        btc.sign_message(
            session,
            coin_name="Bitcoin",
            n=parse_path("m/10025h/0h/0h/1h"),
            message=MESSAGE,
            script_type=S.SPENDTAPROOT,
        )
