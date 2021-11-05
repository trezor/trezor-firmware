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


import pytest

from trezorlib import btc, messages
from trezorlib.debuglink import message_filters
from trezorlib.tools import parse_path

S = messages.InputScriptType


def case(id, *args, altcoin=False):
    if altcoin:
        marks = pytest.mark.altcoin
    else:
        marks = ()
    return pytest.param(*args, id=id, marks=marks)


MESSAGE_NFKD = u"Pr\u030ci\u0301s\u030cerne\u030c z\u030clut\u030couc\u030cky\u0301 ku\u030an\u030c u\u0301pe\u030cl d\u030ca\u0301belske\u0301 o\u0301dy za\u0301ker\u030cny\u0301 uc\u030cen\u030c be\u030cz\u030ci\u0301 pode\u0301l zo\u0301ny u\u0301lu\u030a"
MESSAGE_NFC = u"P\u0159\xed\u0161ern\u011b \u017elu\u0165ou\u010dk\xfd k\u016f\u0148 \xfap\u011bl \u010f\xe1belsk\xe9 \xf3dy z\xe1ke\u0159n\xfd u\u010de\u0148 b\u011b\u017e\xed pod\xe9l z\xf3ny \xfal\u016f"
NFKD_NFC_SIGNATURE = "2046a0b46e81492f82e0412c73701b9740e6462c603575ee2d36c7d7b4c20f0f33763ca8cb3027ea8e1ce5e83fda8b6746fea8f5c82655d78fd419e7c766a5e17a"

VECTORS = (  # case name, coin_name, path, script_type, address, message, signature
    # ==== Bitcoin script types ====
    case(
        "p2pkh",
        "Bitcoin",
        "44h/0h/0h/0/0",
        S.SPENDADDRESS,
        False,
        "1JAd7XCBzGudGpJQSDSfpmJhiygtLQWaGL",
        "This is an example of a signed message.",
        "20fd8f2f7db5238fcdd077d5204c3e6949c261d700269cefc1d9d2dcef6b95023630ee617f6c8acf9eb40c8edd704c9ca74ea4afc393f43f35b4e8958324cbdd1c",
    ),
    case(
        "segwit-p2sh",
        "Bitcoin",
        "49h/0h/0h/0/0",
        S.SPENDP2SHWITNESS,
        False,
        "3L6TyTisPBmrDAj6RoKmDzNnj4eQi54gD2",
        "This is an example of a signed message.",
        "23744de4516fac5c140808015664516a32fead94de89775cec7e24dbc24fe133075ac09301c4cc8e197bea4b6481661d5b8e9bf19d8b7b8a382ecdb53c2ee0750d",
    ),
    case(
        "segwit-native",
        "Bitcoin",
        "84h/0h/0h/0/0",
        S.SPENDWITNESS,
        False,
        "bc1qannfxke2tfd4l7vhepehpvt05y83v3qsf6nfkk",
        "This is an example of a signed message.",
        "28b55d7600d9e9a7e2a49155ddf3cfdb8e796c207faab833010fa41fb7828889bc47cf62348a7aaa0923c0832a589fab541e8f12eb54fb711c90e2307f0f66b194",
    ),
    case(
        "p2pkh",
        "Bitcoin",
        "44h/0h/0h/0/0",
        S.SPENDADDRESS,
        True,
        "1JAd7XCBzGudGpJQSDSfpmJhiygtLQWaGL",
        "This is an example of a signed message.",
        "20fd8f2f7db5238fcdd077d5204c3e6949c261d700269cefc1d9d2dcef6b95023630ee617f6c8acf9eb40c8edd704c9ca74ea4afc393f43f35b4e8958324cbdd1c",
    ),
    case(
        "segwit-p2sh",
        "Bitcoin",
        "49h/0h/0h/0/0",
        S.SPENDP2SHWITNESS,
        True,
        "3L6TyTisPBmrDAj6RoKmDzNnj4eQi54gD2",
        "This is an example of a signed message.",
        "1f744de4516fac5c140808015664516a32fead94de89775cec7e24dbc24fe133075ac09301c4cc8e197bea4b6481661d5b8e9bf19d8b7b8a382ecdb53c2ee0750d",
    ),
    case(
        "segwit-native",
        "Bitcoin",
        "84h/0h/0h/0/0",
        S.SPENDWITNESS,
        True,
        "bc1qannfxke2tfd4l7vhepehpvt05y83v3qsf6nfkk",
        "This is an example of a signed message.",
        "20b55d7600d9e9a7e2a49155ddf3cfdb8e796c207faab833010fa41fb7828889bc47cf62348a7aaa0923c0832a589fab541e8f12eb54fb711c90e2307f0f66b194",
    ),
    # ==== Bitcoin with long message ====
    case(
        "p2pkh long message",
        "Bitcoin",
        "44h/0h/0h/0/0",
        S.SPENDADDRESS,
        False,
        "1JAd7XCBzGudGpJQSDSfpmJhiygtLQWaGL",
        "VeryLongMessage!" * 64,
        "200a46476ceb84d06ef5784828026f922c8815f57aac837b8c013007ca8a8460db63ef917dbebaebd108b1c814bbeea6db1f2b2241a958e53fe715cc86b199d9c3",
    ),
    case(
        "segwit-p2sh long message",
        "Bitcoin",
        "49h/0h/0h/0/0",
        S.SPENDP2SHWITNESS,
        False,
        "3L6TyTisPBmrDAj6RoKmDzNnj4eQi54gD2",
        "VeryLongMessage!" * 64,
        "236eadee380684f70749c52141c8aa7c3b6afd84d0e5f38cfa71823f3b1105a5f34e23834a5bb6f239ff28ad87f409f44e4ce6269754adc00388b19507a5d9386f",
    ),
    case(
        "segwit-native long message",
        "Bitcoin",
        "84h/0h/0h/0/0",
        S.SPENDWITNESS,
        False,
        "bc1qannfxke2tfd4l7vhepehpvt05y83v3qsf6nfkk",
        "VeryLongMessage!" * 64,
        "28c6f86e255eaa768c447d635d91da01631ac54af223c2c182d4fa3676cfecae4a199ad33a74fe04fb46c39432acb8d83de74da90f5f01123b3b7d8bc252bc7f71",
    ),
    # ==== NFKD vs NFC message - signatures must be identical ====
    case(
        "NFKD message",
        "Bitcoin",
        "44h/0h/0h/0/1",
        S.SPENDADDRESS,
        False,
        "1GWFxtwWmNVqotUPXLcKVL2mUKpshuJYo",
        MESSAGE_NFKD,
        NFKD_NFC_SIGNATURE,
    ),
    case(
        "NFC message",
        "Bitcoin",
        "44h/0h/0h/0/1",
        S.SPENDADDRESS,
        False,
        "1GWFxtwWmNVqotUPXLcKVL2mUKpshuJYo",
        MESSAGE_NFC,
        NFKD_NFC_SIGNATURE,
    ),
    # ==== Testnet script types ====
    case(
        "p2pkh",
        "Testnet",
        "44h/1h/0h/0/0",
        S.SPENDADDRESS,
        False,
        "mvbu1Gdy8SUjTenqerxUaZyYjmveZvt33q",
        "This is an example of a signed message.",
        "2030cd7f116c0481d1936cfef48137fd23ee56aaf00787bfa08a94837466ec9909390c3efacfc56bae5782f1db4cf49ae05f242b5f62a47f871ec46bf1a3253e7f",
    ),
    case(
        "segwit-p2sh",
        "Testnet",
        "49h/1h/0h/0/0",
        S.SPENDP2SHWITNESS,
        False,
        "2N4Q5FhU2497BryFfUgbqkAJE87aKHUhXMp",
        "This is an example of a signed message.",
        "23ef39fd388c3425d6aaa04274dcd5c7dd4c283a411b616443474fbcde5dd966050d91bc7c57e9578f28efdd84c9a9bcba415f93c5727b5d3f2bf3de46d7084896",
    ),
    case(
        "segwit-native",
        "Testnet",
        "84h/1h/0h/0/0",
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
        "44h/145h/0h/0/0",
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
        "44h/17h/0h/0/0",
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
        "49h/17h/0h/0/0",
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
        "84h/17h/0h/0/0",
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
        "44h/42h/0h/0/0",
        S.SPENDADDRESS,
        False,
        "DsZtHtXHwvNR3nWf1PqfxrEdnRJisKEyzp1",
        "This is an example of a signed message.",
        "206b1f8ba47ef9eaf87aa900e41ab1e97f67e8c09292faa4acf825228d074c4b774484046dcb1d9bbf0603045dbfb328c3e1b0c09c5ae133e89e604a67a1fc6cca",
        altcoin=True,
    ),
    case(
        "decred-empty",
        "Decred",
        "44h/42h/0h/0/0",
        S.SPENDADDRESS,
        False,
        "DsZtHtXHwvNR3nWf1PqfxrEdnRJisKEyzp1",
        "",
        "1fd2d57490b44a0361c7809768cad032d41ba1d4b7a297f935fc65ae05f71de7ea0c6c6fd265cc5154f1fa4acd7006b6a00ddd67fb7333c1594aff9120b3ba8024",
        altcoin=True,
    ),
)


@pytest.mark.parametrize(
    "coin_name, path, script_type, no_script_type, address, message, signature", VECTORS
)
def test_signmessage(
    client, coin_name, path, script_type, no_script_type, address, message, signature
):
    sig = btc.sign_message(
        client,
        coin_name=coin_name,
        n=parse_path(path),
        script_type=script_type,
        no_script_type=no_script_type,
        message=message,
    )
    assert sig.address == address
    assert sig.signature.hex() == signature


MESSAGE_LENGTHS = (
    pytest.param("This is a very long message. " * 16, id="normal_text"),
    pytest.param("ThisIsAMessageWithoutSpaces" * 16, id="no_spaces"),
    pytest.param("ThisIsAMessageWithLongWords " * 16, id="long_words"),
    pytest.param("This\nmessage\nhas\nnewlines\nafter\nevery\nword", id="newlines"),
    pytest.param("Příšerně žluťoučký kůň úpěl ďábelské ódy. " * 16, id="utf_text"),
    pytest.param("PříšerněŽluťoučkýKůňÚpělĎábelskéÓdy" * 16, id="utf_nospace"),
    pytest.param("1\n2\n3\n4\n5\n6", id="single_line_over"),
)


@pytest.mark.skip_t1
@pytest.mark.parametrize("message", MESSAGE_LENGTHS)
def test_signmessage_pagination(client, message):
    message_read = ""

    def input_flow():
        # collect screen contents into `message_read`.
        # Join lines that are separated by a single "-" string, space-separate lines otherwise.
        nonlocal message_read

        # confirm address
        br = yield
        layout = client.debug.wait_layout()
        client.debug.press_yes()

        # start assuming there was a word break; this avoids prepending space at start
        word_break = True
        br = yield
        for i in range(br.pages):
            layout = client.debug.wait_layout()
            for line in layout.lines[1:]:
                if line == "-":
                    # next line will be attached without space
                    word_break = True
                elif word_break:
                    # attach without space, reset word_break
                    message_read += line
                    word_break = False
                else:
                    # attach with space
                    message_read += " " + line

            if i < br.pages - 1:
                client.debug.swipe_up()

        client.debug.press_yes()

    with client:
        client.set_input_flow(input_flow)
        client.debug.watch_layout(True)
        btc.sign_message(
            client,
            coin_name="Bitcoin",
            n=parse_path("m/44h/0h/0h/0/0"),
            message=message,
        )
    assert message.replace("\n", " ") == message_read


@pytest.mark.skip_t1
def test_signmessage_pagination_trailing_newline(client):
    message = "THIS\nMUST\nNOT\nBE\nPAGINATED\n"
    # The trailing newline must not cause a new paginated screen to appear.
    # The UI must be a single dialog without pagination.
    with client:
        client.set_expected_responses(
            [
                # expect address confirmation
                message_filters.ButtonRequest(code=messages.ButtonRequestType.Other),
                # expect a ButtonRequest that does not have pagination set
                message_filters.ButtonRequest(pages=None),
                messages.MessageSignature,
            ]
        )
        btc.sign_message(
            client,
            coin_name="Bitcoin",
            n=parse_path("m/44h/0h/0h/0/0"),
            message=message,
        )
