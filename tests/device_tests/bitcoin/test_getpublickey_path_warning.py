# This file is part of the Trezor project.
#
# Copyright (C) 2012-2025 SatoshiLabs and contributors
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

"""Warning-screen behaviour of GetPublicKey(show_display=True).

Each vector pins whether the derivation-path warning appears. The existing
xpub tests cannot observe it: InputFlowShowXpubQRCode dismisses the warning
screen, so they pass either way. Here the ButtonRequest sequence is asserted.
"""

import pytest

from trezorlib import btc, messages
from trezorlib.debuglink import DebugSession as Session
from trezorlib.exceptions import TrezorFailure
from trezorlib.tools import parse_path

from ...input_flows import InputFlowShowXpubQRCode

B = messages.ButtonRequestType
IST = messages.InputScriptType

WARN = True
SILENT = False


def _v(
    coin: str,
    path: str,
    script_type: messages.InputScriptType,
    warns: bool,
    xpub: str,
    descriptor: str | None,
):
    return pytest.param(
        coin,
        path,
        script_type,
        warns,
        xpub,
        descriptor,
        marks=[pytest.mark.altcoin] if coin != "Bitcoin" else [],
        id=f"{coin}-{path}-{script_type.name}-{'warn' if warns else 'silent'}",
    )


VECTORS = (
    # Sharing points: the pattern's deepest hardened component, or its account
    # component when everything below that is unhardened. Only these are silent;
    # every row further down still warns.
    _v(
        "Bitcoin",
        "m/45h",
        IST.SPENDADDRESS,
        SILENT,
        "xpub68Zyu13qjcQxGzRBCqdFghtKtQppWvKoaZiVUdNKutNRuBQpL2rtpFYrEL8kDMKymKZdGLquD76mMhLeaAyRwKPv6FMVrFseXQG2nTkfejB",
        "pkh([5c9e228d/45h]xpub68Zyu13qjcQxGzRBCqdFghtKtQppWvKoaZiVUdNKutNRuBQpL2rtpFYrEL8kDMKymKZdGLquD76mMhLeaAyRwKPv6FMVrFseXQG2nTkfejB/<0;1>/*)#lycajv0u",
    ),
    # single-key magic on a multisig node, pinned as current behaviour
    _v(
        "Bitcoin",
        "m/45h",
        IST.SPENDP2SHWITNESS,
        SILENT,
        "ypub6TQFCfiktHxS8HcJ3CQstnyq4NyGTYKJVgEiG2GDHtkJxHE3ah2TSKCzFY6LDFyuAxgS1pSTfmTKEyxDHsPSjZ5Wxb3vSAh8o8KgB2xfRj2",
        "sh(wpkh([5c9e228d/45h]xpub68Zyu13qjcQxGzRBCqdFghtKtQppWvKoaZiVUdNKutNRuBQpL2rtpFYrEL8kDMKymKZdGLquD76mMhLeaAyRwKPv6FMVrFseXQG2nTkfejB/<0;1>/*))#z8drs9hx",
    ),
    # single-key magic on a multisig node, pinned as current behaviour
    _v(
        "Bitcoin",
        "m/45h/0/0",
        IST.SPENDP2SHWITNESS,
        SILENT,
        "ypub6WcontRG1iDDFhyB6bYdWAjSLV46JpWYtw2YZiudcDhatMRtL3TZLmqXhn2GZt9LKcaLrKxZ7Rh1cQDH6Yp27PMsALg9xCnMH7GvB6JUqRF",
        "sh(wpkh([5c9e228d/45h/0/0]xpub6BnYVDkLs2fjQQn4GEm1J5dwAWueNCX3ypWKnL1kEDKhqFcf5PHziiBPga4gZyVQuyTY6rMzemLTj7biNrQ1K9gGHzyjNHxs1PDGnVfU4oE/<0;1>/*))#70phf2xj",
    ),
    _v(
        "Bitcoin",
        "m/45h/0h/0h",
        IST.SPENDADDRESS,
        SILENT,
        "xpub6DL6rwpkGKGqmrGguSjWpukvK9WS6gagmAYsAPtkmaL1w3VhuKs9KDQ4jqYRAFRrmSvXRRbibM4sG4XBNbEDTRyFaQBaW86W7ihbJ9z2jU1",
        "pkh([5c9e228d/45h/0h/0h]xpub6DL6rwpkGKGqmrGguSjWpukvK9WS6gagmAYsAPtkmaL1w3VhuKs9KDQ4jqYRAFRrmSvXRRbibM4sG4XBNbEDTRyFaQBaW86W7ihbJ9z2jU1/<0;1>/*)#swe7m32m",
    ),
    # identical to the SPENDADDRESS row above: SPENDMULTISIG also yields the legacy magic
    _v(
        "Bitcoin",
        "m/45h/0h/0h",
        IST.SPENDMULTISIG,
        SILENT,
        "xpub6DL6rwpkGKGqmrGguSjWpukvK9WS6gagmAYsAPtkmaL1w3VhuKs9KDQ4jqYRAFRrmSvXRRbibM4sG4XBNbEDTRyFaQBaW86W7ihbJ9z2jU1",
        None,
    ),
    _v(
        "Bitcoin",
        "m/48h/0h/0h/0h",
        IST.SPENDADDRESS,
        SILENT,
        "xpub6EgGHjcvovyMw8xyoJw9ZRUfjGLS1KUmbjVqMKSNfM6E8hq4EbQ3CpBxfGCPsdxzXtCFuKCxYarzY1TYCG1cmPwq9ep548cM9Ws9rB8V8E8",
        "pkh([5c9e228d/48h/0h/0h/0h]xpub6EgGHjcvovyMw8xyoJw9ZRUfjGLS1KUmbjVqMKSNfM6E8hq4EbQ3CpBxfGCPsdxzXtCFuKCxYarzY1TYCG1cmPwq9ep548cM9Ws9rB8V8E8/<0;1>/*)#l0nv557v",
    ),
    # single-key magic on a multisig node, pinned as current behaviour
    _v(
        "Bitcoin",
        "m/48h/0h/0h/1h",
        IST.SPENDP2SHWITNESS,
        SILENT,
        "ypub6ZWXbQHqxcWqqGcJG77eBGLCR2jnGbCwDhoePVEWDVkzgite1fhb2qCWgVUysKWKm7sGfo2jSw7FJrvSQMD6y8urRWQUBpvf2dsuZU2HF7U",
        "sh(wpkh([5c9e228d/48h/0h/0h/1h]xpub6EgGHjcvovyMyyRBRkL1yBEhF4bLKyDSJbHRc6LcqVP7dd5Qm1Y2QmYNfHXPsQrQMUkTvKSAzGkhRaJsgeo6AuEFZAi3bv7AkupGAt826Mt/<0;1>/*))#pv2vycur",
    ),
    # single-key magic on a multisig node, pinned as current behaviour
    _v(
        "Bitcoin",
        "m/48h/0h/0h/2h",
        IST.SPENDWITNESS,
        SILENT,
        "zpub6tLnu4xm7J4KkNhNgjZQgZruWzJWBmjYFrvVT84YUNjghsvHPBPeFmjqyrcmDztrp5De8ynKfWwJtgdhG7c5TuuXLSbqZy5aenhmvJJ8Kxs",
        "wpkh([5c9e228d/48h/0h/0h/2h]xpub6EgGHjcvovyN3nK921zAGPfuB41cJXkYRdt3tLGmiMyvbgHpss4X1eRZwShbEBb1znz2e2bCkCED87QZpin3sSYKbmCzQ9Sc7LaV98ngdeX/<0;1>/*)#u6cru3mz",
    ),
    _v(
        "Bitcoin",
        "m/3h/100h",
        IST.SPENDADDRESS,
        SILENT,
        "xpub6AJoQXBXx3YbgRDPVpNHC4zovwFpzrx2n4dQ91ZXdKSPV7T9ZfAtYH5D5H4JiVQsgJu561KNyP8bcYdxeQK2o2UZLUscGHfS9GDCTKqNCBA",
        "pkh([5c9e228d/3h/100h]xpub6AJoQXBXx3YbgRDPVpNHC4zovwFpzrx2n4dQ91ZXdKSPV7T9ZfAtYH5D5H4JiVQsgJu561KNyP8bcYdxeQK2o2UZLUscGHfS9GDCTKqNCBA/<0;1>/*)#33anhj2p",
    ),
    # PATTERN_CASA_UNHARDENED has no hardened component, so it is skipped and keeps warning
    _v(
        "Bitcoin",
        "m/49/0/0",
        IST.SPENDP2SHWITNESS,
        WARN,
        "ypub6WdM7wc6rBffy8jULHk4BRmhHxt7pvjVPQFCwqhdyaHHNH3ZDeGNLwkAcJwAQKXFvQnK9ik7KKh8HmgNFCAKVPCuFJ5eitzxEGFBqqJ3Njd",
        "sh(wpkh([5c9e228d/49/0/0]xpub6Bo5pGwBhW8C7qYMVvxRyLgC7zjftJjzUHizASokbZuQKBEKxz6oit62b6yaQQsLWmfWQF9YrfLaQV4oXVkJh9XJNxPE8zBTxYBYTEibk9W/<0;1>/*))#22n4lqa9",
    ),
    # Named account types.
    _v(
        "Bitcoin",
        "m/44h/0h/0h",
        IST.SPENDADDRESS,
        SILENT,
        "xpub6BiVtCpG9fQPxnPmHXG8PhtzQdWC2Su4qWu6XW9tpWFYhxydCLJGrWBJZ5H6qTAHdPQ7pQhtpjiYZVZARo14qHiay2fvrX996oEP42u8wZy",
        "pkh([5c9e228d/44h/0h/0h]xpub6BiVtCpG9fQPxnPmHXG8PhtzQdWC2Su4qWu6XW9tpWFYhxydCLJGrWBJZ5H6qTAHdPQ7pQhtpjiYZVZARo14qHiay2fvrX996oEP42u8wZy/<0;1>/*)#m2cjewq5",
    ),
    _v(
        "Bitcoin",
        "m/49h/0h/0h",
        IST.SPENDP2SHWITNESS,
        SILENT,
        "ypub6XKbB5DSkq8Royg8isNtGktj6bmEfGJXDs83Ad5CZ5tpDV8QofwSWQFTWP2Pv24vNdrPhquehL7vRMvSTj2GpKv6UaTQCBKZALm6RJAmxG6",
        "sh(wpkh([5c9e228d/49h/0h/0h]xpub6CVKsQYXc9awxgV1tWbG4foDvdcnieK2JkbpPEBKB5WwAPKBZ1mstLbKVB4ov7QzxzjaxNK6EfmNY5Jsk2cG26EVcEkycGW4tchT2dyUhrx/<0;1>/*))#38fl96mv",
    ),
    _v(
        "Bitcoin",
        "m/84h/0h/0h",
        IST.SPENDWITNESS,
        SILENT,
        "zpub6rszzdAK6RuafeRwyN8z1cgWcXCuKbLmjjfnrW4fWKtcoXQ8787214pNJjnBG5UATyghuNzjn6Lfp5k5xymrLFJnCy46bMYJPyZsbpFGagT",
        "wpkh([5c9e228d/84h/0h/0h]xpub6DDUPHpUo4pcy43iJeZjbSVWGav1SMMmuWdMHiGtkK8rhKmfbomtkwW6GKs1GGAKehT6QRocrmda3WWxXawpjmwaUHfFRXuKrXSapdckEYF/<0;1>/*)#u9auedf8",
    ),
    _v(
        "Bitcoin",
        "m/86h/0h/0h",
        IST.SPENDTAPROOT,
        SILENT,
        "xpub6Bw885JisRbcKmowfBvMmCxaFHodKn1VpmRmctmJJoM8D4DzyP4qJv8ZdD9V9r3SSGjmK2KJEDnvLH6f1Q4HrobEvnCeKydNvf1eir3RHZk",
        "tr([5c9e228d/86h/0h/0h]xpub6Bw885JisRbcKmowfBvMmCxaFHodKn1VpmRmctmJJoM8D4DzyP4qJv8ZdD9V9r3SSGjmK2KJEDnvLH6f1Q4HrobEvnCeKydNvf1eir3RHZk/<0;1>/*)#9thz2a5h",
    ),
    # Paths that are not sharing points of any accepted pattern.
    # m was GreenAddress A's real export point -- it asked for the root and
    # derived /[1,4]/address_index host-side -- but it is withheld: the warning
    # cannot be scoped to one requester, and the root xpub also yields every
    # PATTERN_CASA_UNHARDENED address.
    _v(
        "Bitcoin",
        "m",
        IST.SPENDADDRESS,
        WARN,
        "xpub661MyMwAqRbcFLgDU7wpcEVubSF7NkswwmXBUkDiGUW6uopeUMys4AqKXNgpfZKRTLnpKQgffd6a2c3J8JxLkF1AQN17Pm9QYHEqEfo1Rsx",
        "pkh([5c9e228d]xpub661MyMwAqRbcFLgDU7wpcEVubSF7NkswwmXBUkDiGUW6uopeUMys4AqKXNgpfZKRTLnpKQgffd6a2c3J8JxLkF1AQN17Pm9QYHEqEfo1Rsx/<0;1>/*)#dnavhhem",
    ),
    # withheld under every script type that offers the pattern
    _v(
        "Bitcoin",
        "m",
        IST.SPENDWITNESS,
        WARN,
        "zpub6jftahH18ngZww4T8qX52QguwNY1FzrwmzZd3Y1V2VFs21T6ygJzJJ9bZnbzfNdGGd2RpMsnawofoBGRZhnNLiNN93PxZanP5jN81oAxB9F",
        "wpkh([5c9e228d]xpub661MyMwAqRbcFLgDU7wpcEVubSF7NkswwmXBUkDiGUW6uopeUMys4AqKXNgpfZKRTLnpKQgffd6a2c3J8JxLkF1AQN17Pm9QYHEqEfo1Rsx/<0;1>/*)#lhj6nf2n",
    ),
    # no GreenAddress pattern under taproot, so m is unreachable there for a
    # second, independent reason
    _v(
        "Bitcoin",
        "m",
        IST.SPENDTAPROOT,
        WARN,
        "xpub661MyMwAqRbcFLgDU7wpcEVubSF7NkswwmXBUkDiGUW6uopeUMys4AqKXNgpfZKRTLnpKQgffd6a2c3J8JxLkF1AQN17Pm9QYHEqEfo1Rsx",
        "tr([5c9e228d]xpub661MyMwAqRbcFLgDU7wpcEVubSF7NkswwmXBUkDiGUW6uopeUMys4AqKXNgpfZKRTLnpKQgffd6a2c3J8JxLkF1AQN17Pm9QYHEqEfo1Rsx/<0;1>/*)#dkydvxvr",
    ),
    # the GreenAddress patterns are Bitcoin-only, so m is not a candidate here
    _v(
        "Litecoin",
        "m",
        IST.SPENDADDRESS,
        WARN,
        "Ltub2SSUS19CirucVhxA4bwpU6c8gEZg8YQ653jAJpxpdyLoeBTT8NUbspKktFCrKxig3ZCPuY5DWejx8hQR3D3nbAnahVta4SuT2n1B98jhD6V",
        "pkh([5c9e228d]Ltub2SSUS19CirucVhxA4bwpU6c8gEZg8YQ653jAJpxpdyLoeBTT8NUbspKktFCrKxig3ZCPuY5DWejx8hQR3D3nbAnahVta4SuT2n1B98jhD6V/<0;1>/*)#v2dhyqlf",
    ),
    # /1 and /4 are the branches the host derived itself; neither was ever an
    # export point
    _v(
        "Bitcoin",
        "m/1",
        IST.SPENDADDRESS,
        WARN,
        "xpub68Zyu13hPwsxBtfEm1Hvt65VQhq8DoP7K7fBEE72SAZgCLob3D9dGFwr6N3a9toJtbE4u9A9mYp4qeog18YnnfKQBvkGUwk63mxVUC1wwT1",
        "pkh([5c9e228d/1]xpub68Zyu13hPwsxBtfEm1Hvt65VQhq8DoP7K7fBEE72SAZgCLob3D9dGFwr6N3a9toJtbE4u9A9mYp4qeog18YnnfKQBvkGUwk63mxVUC1wwT1/<0;1>/*)#zu0lct5x",
    ),
    _v(
        "Bitcoin",
        "m/4",
        IST.SPENDADDRESS,
        WARN,
        "xpub68Zyu13hPwsxKQc7hKGDqY8gyWcoXbWyoCWViPnrRSy13PhkkBpR65eEBKvf4aPNw7XHSZDj3YiCEnY9gxotCaayrBkEDz7KEUUmjCGv8Vq",
        "pkh([5c9e228d/4]xpub68Zyu13hPwsxKQc7hKGDqY8gyWcoXbWyoCWViPnrRSy13PhkkBpR65eEBKvf4aPNw7XHSZDj3YiCEnY9gxotCaayrBkEDz7KEUUmjCGv8Vq/<0;1>/*)#zxgcwgqn",
    ),
    # between the two Casa sharing points
    _v(
        "Bitcoin",
        "m/45h/0",
        IST.SPENDP2SHWITNESS,
        WARN,
        "ypub6UdB56hawsvhNDnuHavi1CreCifHwpFJMGfE1g43bBbAfgEAMA7QqKFp6XRrGhdG2xr6oHHyiiXqHfcP4iACPj4vcX6bfdqWH6gZaVGvGqX",
        "sh(wpkh([5c9e228d/45h/0]xpub69numS2foCPDWvbnTE95o7m92kWr1CFoSA91EHAADBDHcaQw6VwrDFbg5KUGGnyLdKjJ3ohRG4BHQNzpM1kBbVPKkBQB5j221NcvByaWDz2/<0;1>/*))#tf29j65x",
    ),
    # one level above the BIP-48 sharing point
    _v(
        "Bitcoin",
        "m/48h/0h/0h",
        IST.SPENDWITNESS,
        WARN,
        "zpub6sBU1cMwhbY1XAzdGWzP6wRMyFDMB6Y56Y4Sn3GD95MZ7rNV7JySveNaa1LWKYERmrxwcPkUkePQZVqW1MpsEFd8GuAgWjigjXNyypbsc4H",
        "wpkh([5c9e228d/48h/0h/0h]xpub6DWwQH27QET3pacPboR8gmEMdJvTHrZ5GK21DFUSP4bo1ek2bzeKgX4JXbRLKivaxajL7SZMqKgJnvcNZxzqdnFvYDmqLv5iC5FhChUAZmQ/<0;1>/*)#3w8zs5hk",
    ),
    # one level below the BIP-44 sharing point
    _v(
        "Bitcoin",
        "m/44h/0h/0h/0",
        IST.SPENDADDRESS,
        WARN,
        "xpub6Ex8WCdj1KH5mK9r99QKENUmhpjEPgYm1dJmKY2nxx16tSAiQCVYjHfymFdzfpYDAHGtWYTif7WkUKLMULRJFPeV1hvEbeXqrM11K85yPjp",
        "pkh([5c9e228d/44h/0h/0h/0]xpub6Ex8WCdj1KH5mK9r99QKENUmhpjEPgYm1dJmKY2nxx16tSAiQCVYjHfymFdzfpYDAHGtWYTif7WkUKLMULRJFPeV1hvEbeXqrM11K85yPjp/<0;1>/*)#pgm48q4h",
    ),
    # script type mismatch
    _v(
        "Bitcoin",
        "m/44h/0h/0h",
        IST.SPENDP2SHWITNESS,
        WARN,
        "ypub6WYmBsVBJLwsp5at7t3kbnzVabedy4tZkdRKJu3nCWdRm4nrSzTqUZqSaHEgqMpD32WvZtJTHQ56SnAj9VR5dXQBqNNMSRxdNXJ2SdMZnge",
        "sh(wpkh([5c9e228d/44h/0h/0h]xpub6BiVtCpG9fQPxnPmHXG8PhtzQdWC2Su4qWu6XW9tpWFYhxydCLJGrWBJZ5H6qTAHdPQ7pQhtpjiYZVZARo14qHiay2fvrX996oEP42u8wZy/<0;1>/*))#q6xqqg55",
    ),
    # coin type mismatch
    _v(
        "Bitcoin",
        "m/44h/1h/0h",
        IST.SPENDADDRESS,
        WARN,
        "xpub6Cx9X24btq6kJdfa9X2R3hy1FTZ8aMiTJCZ5WgeUEm2KomqCFS4F7auV3izfPSx6tGAX9B9RJWNv8bzm411qrs6GULpno6PoRYCFAy3k7qf",
        "pkh([5c9e228d/44h/1h/0h]xpub6Cx9X24btq6kJdfa9X2R3hy1FTZ8aMiTJCZ5WgeUEm2KomqCFS4F7auV3izfPSx6tGAX9B9RJWNv8bzm411qrs6GULpno6PoRYCFAy3k7qf/<0;1>/*)#4sqz9ncx",
    ),
    # Coin gating above coin_type.
    # single-key magic on a multisig node, pinned as current behaviour
    _v(
        "Litecoin",
        "m/45h",
        IST.SPENDP2SHWITNESS,
        SILENT,
        "Mtub2oqMfJvnmjGSNetEdgQskf649BHqDKqScxSh671KfPb1gerrEhXCFxhRcQcMsfP9mB61bwq1Wo6hM5KLCmUtaUrwFiwP6rTBHd625aPjec2",
        "sh(wpkh([5c9e228d/45h]Ltub2V16MeFsd3ixXMh7oKdFYZzYyD9PGhqwhqvUJi7SHPD8dZ3cz3Mddu3HbCemskjEMXyCrUET48k9TnhmV54snFBLPPExWwdh1u2Ngw7xFqj/<0;1>/*))#yvy7scl5",
    ),
    # same key as the row above, yet warned: BIP-45 needs slip44==0 or a fork id and the
    # Unchained patterns need BITCOIN_NAMES, so on Litecoin only P2SH-segwit matches
    _v(
        "Litecoin",
        "m/45h",
        IST.SPENDADDRESS,
        WARN,
        "Ltub2V16MeFsd3ixXMh7oKdFYZzYyD9PGhqwhqvUJi7SHPD8dZ3cz3Mddu3HbCemskjEMXyCrUET48k9TnhmV54snFBLPPExWwdh1u2Ngw7xFqj",
        "pkh([5c9e228d/45h]Ltub2V16MeFsd3ixXMh7oKdFYZzYyD9PGhqwhqvUJi7SHPD8dZ3cz3Mddu3HbCemskjEMXyCrUET48k9TnhmV54snFBLPPExWwdh1u2Ngw7xFqj/<0;1>/*)#zvt0vpha",
    ),
)


@pytest.mark.models("core")
@pytest.mark.parametrize(
    "coin_name, path, script_type, warns, xpub, descriptor", VECTORS
)
def test_path_warning(
    session: Session,
    coin_name: str,
    path: str,
    script_type: messages.InputScriptType,
    warns: bool,
    xpub: str,
    descriptor: str | None,
):
    expected = []
    if warns:
        expected.append(messages.ButtonRequest(code=B.UnknownDerivationPath))
    expected += [
        messages.ButtonRequest(code=B.PublicKey),
        messages.PublicKey,
    ]

    with session.test_ctx as client:
        IF = InputFlowShowXpubQRCode(session)
        client.set_input_flow(IF.get())
        client.set_expected_responses(expected)
        res = btc.get_public_node(
            session,
            parse_path(path),
            coin_name=coin_name,
            script_type=script_type,
            show_display=True,
        )

    # Pinned so a display-only change cannot move a derivation unnoticed.
    assert res.xpub == xpub
    # descriptor is built from script_type alone, so a multisig leg reads as
    # single-key. Pinned as current behaviour: a correct multisig descriptor
    # needs every cosigner, so the eventual fix is to omit it.
    assert res.descriptor == descriptor


@pytest.mark.models("core")
def test_slip25_still_requires_unlock_path(session: Session):
    """SLIP-25 must stay behind UnlockPath, warning logic notwithstanding.

    PATTERN_SLIP25_TAPROOT is in the taproot branch of the pattern table, so a
    widened pattern match could plausibly expose the coinjoin account node. The
    check in get_public_key rejects it before any warning logic runs.
    """
    with pytest.raises(TrezorFailure, match="Forbidden key path"):
        btc.get_public_node(
            session,
            parse_path("m/10025h/0h/0h/1h"),
            coin_name="Bitcoin",
            script_type=messages.InputScriptType.SPENDTAPROOT,
            show_display=True,
        )
