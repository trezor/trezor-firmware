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
from trezorlib.debuglink import DebugSession as Session
from trezorlib.exceptions import Cancelled, TrezorFailure
from trezorlib.tools import parse_path

from ... import bip32
from ...input_flows import InputFlowShowXpubQRCode

VECTORS_BITCOIN = (  # coin_name, xpub_magic, path, xpub
    (
        "Bitcoin",
        0x0488B21E,
        parse_path("m/44h/0h/0h"),
        "xpub6BiVtCpG9fQPxnPmHXG8PhtzQdWC2Su4qWu6XW9tpWFYhxydCLJGrWBJZ5H6qTAHdPQ7pQhtpjiYZVZARo14qHiay2fvrX996oEP42u8wZy",
    ),
    (
        "Bitcoin",
        0x0488B21E,
        parse_path("m/44h/0h/10h"),
        "xpub6BiVtCpG9fQQR6cSuFeDaSvCDgNvNme499JUGX4RHDiZVWwZy9NwNieWKXHLe8XRbdrEmY87aqztBCbRJkXWV7VJB96XBT5cpkqYMHwvLWB",
    ),
    (
        "Bitcoin",
        0x0488B21E,
        parse_path("m/44h/0h/0h/0/0"),
        "xpub6FVDRC1jiWNTuT3embehwSZ1buxRDyZGbTakVCkBr6w2LwpERmYqXyvtrLeJX9hqzLaucS3qJXGekeFsSVCELkbgepp7FVGeH5BYekEgT9x",
    ),
    (
        "Bitcoin",
        0x0488B21E,
        parse_path("m/44h/0h/10h/1/100"),
        "xpub6GhTNegKCjTqjYS4HNkPhXHXHNZV2cPC38N7HbpUKexXXuTkjKPnijqKTB7yXidP4JtTUWTuWPTt6P55xi91NPgUp51BnqYzYdNhho4y5j8",
    ),
    (
        "Testnet",
        0x043587CF,
        parse_path("m/44h/1h/0h"),
        "tpubDDKn3FtHc74CaRrRbi1WFdJNaaenZkDWqq9NsEhcafnDZ4VuKeuLG2aKHm5SuwuLgAhRkkfHqcCxpnVNSrs5kJYZXwa6Ud431VnevzzzK3U",
    ),
    (
        "Testnet",
        0x043587CF,
        parse_path("m/44h/1h/0h/0/0"),
        "tpubDGwNSs8z8jZU2EcUiubR4frGvKqddvLBqCDNknnWhmoUd6EHrRWrqXmDaWBNddWzM5Yqh4e4TUYFK9hGCEnSrMKgV6cthRhArfZpwzihdw7",
    ),
    (  # PSBT master fingerprint retrieval
        "Bitcoin",
        0x0488B21E,
        parse_path("m/0h"),
        "xpub68Zyu13qjcQvJXTsnmhH2h2TyPiXAama5bTU8u9iRXyYtS9X9yWvSKij6YGt7JJ2nr5rSGi4KLUW5Z8bTKHqXhbLwqb7smG3Y8j2wy4rmf3",
    ),
    pytest.param(
        "Litecoin",
        0x019DA462,
        parse_path("m/44h/2h/0h"),
        "Ltub2Y8PyEMWQVgiX4L4gVzU8PakBTQ2WBxFdS6tJARQeasUUfXmBut2jGShnQyD3jgyBf7mmvs5jPNgmgXad5J6M8a8FiZK78dbT21fYtTAC9a",
        marks=pytest.mark.altcoin,
    ),
    pytest.param(
        "Litecoin",
        0x019DA462,
        parse_path("m/44h/2h/10h"),
        "Ltub2Y8PyEMWQVgiy8Zio1XrKWkGL6ZmCZB9W5ShbvbzZ14irCrAb62YEoMafTAM5a2A6x6XNcyDdCNW7NVgES9jtQqyUZcBUFTimS7VVJ8tbpE",
        marks=pytest.mark.altcoin,
    ),
    pytest.param(
        "Litecoin",
        0x019DA462,
        parse_path("m/44h/2h/0h/0/0"),
        "Ltub2dTvwC4v7GNeR6UEaywQ6j72wHi4dwRo3oDDzvXAwb4CrXVQEUTbxC4hEfULiKByiUMEmYLhuMo1YMYmBBjKJ8kyk9ia5gZaVNWq5rVLom4",
        marks=pytest.mark.altcoin,
    ),
    pytest.param(
        "Litecoin",
        0x019DA462,
        parse_path("m/44h/2h/10h/1/100"),
        "Ltub2dcb6Nghj3kwaC2g3TtPgFzMSm7LXfe4mijFYsvEtxXu18vicTB4kYc9z6jGVMpdYhMScNhVY1naQYALnM2x4fvaGzAAGgcuZ89nFyyLhiK",
        marks=pytest.mark.altcoin,
    ),
)

VECTORS_INVALID = (  # coin_name, path
    ("Bitcoin", parse_path("m/44h/1h/0h")),  # Testnet path on Bitcoin
    ("Testnet", parse_path("m/44h/0h/0h")),  # Bitcoin path on Testnet
    ("Bitcoin", parse_path("m/40h/0h/0h")),  # Unknown purpose
    ("Bitcoin", parse_path("m/13h/0h/0h")),  # SLIP-13 path
    # Bitcoin path on Litecoin
    pytest.param("Litecoin", parse_path("m/44h/0h/0h"), marks=pytest.mark.altcoin),
    # Segwit path on Bitcoin Cash
    pytest.param("Bcash", parse_path("m/84h/145h/0h"), marks=pytest.mark.altcoin),
)


@pytest.mark.parametrize("coin_name, xpub_magic, path, xpub", VECTORS_BITCOIN)
def test_get_public_node(session: Session, coin_name, xpub_magic, path, xpub):
    res = btc.get_public_node(session, path, coin_name=coin_name)
    assert res.xpub == xpub
    assert bip32.serialize(res.node, xpub_magic) == xpub


@pytest.mark.parametrize("coin_name, xpub_magic, path, xpub", VECTORS_BITCOIN)
def test_get_public_node_cancel_show(
    session: Session, coin_name, xpub_magic, path, xpub
):
    def input_flow():
        yield
        session.cancel()

    with pytest.raises(Cancelled), session.test_ctx as client:
        client.set_input_flow(input_flow)
        btc.get_public_node(session, path, coin_name=coin_name, show_display=True)


@pytest.mark.models("core")
@pytest.mark.parametrize("coin_name, xpub_magic, path, xpub", VECTORS_BITCOIN)
def test_get_public_node_show(session: Session, coin_name, xpub_magic, path, xpub):
    with session.test_ctx as client:
        IF = InputFlowShowXpubQRCode(session)
        client.set_input_flow(IF.get())
        res = btc.get_public_node(session, path, coin_name=coin_name, show_display=True)
        assert res.xpub == xpub
        assert bip32.serialize(res.node, xpub_magic) == xpub


@pytest.mark.xfail(reason="Currently path validation on get_public_node is disabled.")
@pytest.mark.parametrize("coin_name, path", VECTORS_INVALID)
def test_invalid_path(session: Session, coin_name, path):
    with pytest.raises(TrezorFailure, match="Forbidden key path"):
        btc.get_public_node(session, path, coin_name=coin_name)


VECTORS_MULTISIG = (  # path, script_type, xpub
    # BIP-45 and Casa purpose-level sharing root
    (
        parse_path("m/45h"),
        messages.InputScriptType.SPENDADDRESS,
        "xpub68Zyu13qjcQxGzRBCqdFghtKtQppWvKoaZiVUdNKutNRuBQpL2rtpFYrEL8kDMKymKZdGLquD76mMhLeaAyRwKPv6FMVrFseXQG2nTkfejB",
    ),
    (
        parse_path("m/45h"),
        messages.InputScriptType.SPENDP2SHWITNESS,
        "ypub6TQFCfiktHxS8HcJ3CQstnyq4NyGTYKJVgEiG2GDHtkJxHE3ah2TSKCzFY6LDFyuAxgS1pSTfmTKEyxDHsPSjZ5Wxb3vSAh8o8KgB2xfRj2",
    ),
    # Casa account level
    (
        parse_path("m/45h/0/0"),
        messages.InputScriptType.SPENDP2SHWITNESS,
        "ypub6WcontRG1iDDFhyB6bYdWAjSLV46JpWYtw2YZiudcDhatMRtL3TZLmqXhn2GZt9LKcaLrKxZ7Rh1cQDH6Yp27PMsALg9xCnMH7GvB6JUqRF",
    ),
    # Unchained account level
    (
        parse_path("m/45h/0h/0h"),
        messages.InputScriptType.SPENDADDRESS,
        "xpub6DL6rwpkGKGqmrGguSjWpukvK9WS6gagmAYsAPtkmaL1w3VhuKs9KDQ4jqYRAFRrmSvXRRbibM4sG4XBNbEDTRyFaQBaW86W7ihbJ9z2jU1",
    ),
    # BIP-48 script-type level
    (
        parse_path("m/48h/0h/0h/1h"),
        messages.InputScriptType.SPENDP2SHWITNESS,
        "ypub6ZWXbQHqxcWqqGcJG77eBGLCR2jnGbCwDhoePVEWDVkzgite1fhb2qCWgVUysKWKm7sGfo2jSw7FJrvSQMD6y8urRWQUBpvf2dsuZU2HF7U",
    ),
    (
        parse_path("m/48h/0h/0h/2h"),
        messages.InputScriptType.SPENDWITNESS,
        "zpub6tLnu4xm7J4KkNhNgjZQgZruWzJWBmjYFrvVT84YUNjghsvHPBPeFmjqyrcmDztrp5De8ynKfWwJtgdhG7c5TuuXLSbqZy5aenhmvJJ8Kxs",
    ),
)


@pytest.mark.models("core")
@pytest.mark.parametrize("path, script_type, xpub", VECTORS_MULTISIG)
def test_get_public_node_multisig_no_warning(session: Session, path, script_type, xpub):
    # Sharing roots and account levels of supported multisig schemes are shown
    # without the unknown derivation path warning.
    with session.test_ctx as client:
        IF = InputFlowShowXpubQRCode(session)
        client.set_input_flow(IF.get())
        client.set_expected_responses(
            [
                messages.ButtonRequest(code=messages.ButtonRequestType.PublicKey),
                messages.PublicKey,
            ]
        )
        res = btc.get_public_node(
            session,
            path,
            coin_name="Bitcoin",
            script_type=script_type,
            show_display=True,
        )
        assert res.xpub == xpub


@pytest.mark.models("core")
def test_get_public_node_multisig_warning(session: Session):
    # A path between the export points of a multisig scheme still shows the
    # unknown derivation path warning.
    with session.test_ctx as client:
        IF = InputFlowShowXpubQRCode(session)
        client.set_input_flow(IF.get())
        client.set_expected_responses(
            [
                messages.ButtonRequest(
                    code=messages.ButtonRequestType.UnknownDerivationPath
                ),
                messages.ButtonRequest(code=messages.ButtonRequestType.PublicKey),
                messages.PublicKey,
            ]
        )
        btc.get_public_node(
            session,
            parse_path("m/45h/0"),
            coin_name="Bitcoin",
            script_type=messages.InputScriptType.SPENDP2SHWITNESS,
            show_display=True,
        )


@pytest.mark.models("legacy")
@pytest.mark.parametrize("coin_name, xpub_magic, path, xpub", VECTORS_BITCOIN)
def test_get_public_node_show_legacy(
    session: Session, coin_name, xpub_magic, path, xpub
):
    def input_flow():
        yield
        session.debug.press_no()  # show QR code
        yield
        session.debug.press_no()  # back to text
        yield
        session.debug.press_no()  # show QR code
        yield
        session.debug.press_yes()  # next xpub page
        yield
        session.debug.press_no()  # show QR code again
        yield
        session.debug.press_no()  # back to text
        yield
        session.debug.press_yes()  # finish the flow
        yield

    with session.test_ctx as client:
        # test XPUB display flow (without showing QR code)
        res = btc.get_public_node(session, path, coin_name=coin_name, show_display=True)
        assert res.xpub == xpub
        assert bip32.serialize(res.node, xpub_magic) == xpub

        # test XPUB QR code display using the input flow above
        client.set_input_flow(input_flow)
        res = btc.get_public_node(session, path, coin_name=coin_name, show_display=True)
        assert res.xpub == xpub
        assert bip32.serialize(res.node, xpub_magic) == xpub


def test_slip25_path(session: Session):
    # Ensure that CoinJoin XPUBs are inaccessible without user authorization.
    with pytest.raises(TrezorFailure, match="Forbidden key path"):
        btc.get_public_node(
            session,
            parse_path("m/10025h/0h/0h/1h"),
            script_type=messages.InputScriptType.SPENDTAPROOT,
        )


VECTORS_SCRIPT_TYPES = (  # script_type, xpub, xpub_ignored_magic
    (
        None,
        "xpub6BiVtCp7ozsRo7kaoYNrCNAVJwPYTQHjoXFD3YS797S55Y42sm2raxPrXQWAJodn7aXnHJdhz433ZJDhyUztHW55WatHeoYUVqui8cYNX8y",
        "xpub6BiVtCp7ozsRo7kaoYNrCNAVJwPYTQHjoXFD3YS797S55Y42sm2raxPrXQWAJodn7aXnHJdhz433ZJDhyUztHW55WatHeoYUVqui8cYNX8y",
    ),
    (
        messages.InputScriptType.SPENDADDRESS,
        "xpub6BiVtCp7ozsRo7kaoYNrCNAVJwPYTQHjoXFD3YS797S55Y42sm2raxPrXQWAJodn7aXnHJdhz433ZJDhyUztHW55WatHeoYUVqui8cYNX8y",
        "xpub6BiVtCp7ozsRo7kaoYNrCNAVJwPYTQHjoXFD3YS797S55Y42sm2raxPrXQWAJodn7aXnHJdhz433ZJDhyUztHW55WatHeoYUVqui8cYNX8y",
    ),
    (
        messages.InputScriptType.SPENDP2SHWITNESS,
        "ypub6WYmBsV2xgQueQwhduAUQTFzUuXzQ2HEidmRpwKzX7ox8dsG8RCRD23zYcTkJiHhXDeb2nEGSiPbSaqGhBQu5jkgNvaiEiMxmZyMXEvfNco",
        "xpub6BiVtCp7ozsRo7kaoYNrCNAVJwPYTQHjoXFD3YS797S55Y42sm2raxPrXQWAJodn7aXnHJdhz433ZJDhyUztHW55WatHeoYUVqui8cYNX8y",
    ),
    (
        messages.InputScriptType.SPENDWITNESS,
        "zpub6qP2VY9x7MxPVi8pUFx6cYMVesgSLeGjdkHecLDsu8BqBjgVP5Myq5i8ZpRLJcwcvrmPnFppuNk9KsSqQspusySHFGH8pdBT3J2zujqcVuz",
        "xpub6BiVtCp7ozsRo7kaoYNrCNAVJwPYTQHjoXFD3YS797S55Y42sm2raxPrXQWAJodn7aXnHJdhz433ZJDhyUztHW55WatHeoYUVqui8cYNX8y",
    ),
)


@pytest.mark.parametrize("script_type, xpub, xpub_ignored_magic", VECTORS_SCRIPT_TYPES)
def test_script_type(session: Session, script_type, xpub, xpub_ignored_magic):
    path = parse_path("m/44h/0h/0")
    res = btc.get_public_node(
        session, path, coin_name="Bitcoin", script_type=script_type
    )
    assert res.xpub == xpub
    res = btc.get_public_node(
        session,
        path,
        coin_name="Bitcoin",
        script_type=script_type,
        ignore_xpub_magic=True,
    )
    assert res.xpub == xpub_ignored_magic
