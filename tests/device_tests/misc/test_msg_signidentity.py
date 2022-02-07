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

from trezorlib import messages, misc
from trezorlib.debuglink import TrezorClientDebugLink as Client

from ...common import MNEMONIC12


@pytest.mark.setup_client(mnemonic=MNEMONIC12)
def test_sign(client: Client):
    hidden = bytes.fromhex(
        "cd8552569d6e4509266ef137584d1e62c7579b5b8ed69bbafa4b864c6521e7c2"
    )
    visual = "2015-03-23 17:39:22"

    # URI  : https://satoshi@bitcoin.org/login
    # hash : d0e2389d4c8394a9f3e32de01104bf6e8db2d9e2bb0905d60fffa5a18fd696db
    # path : m/2147483661/2637750992/2845082444/3761103859/4005495825
    identity = messages.IdentityType(
        proto="https",
        user="satoshi",
        host="bitcoin.org",
        port="",
        path="/login",
        index=0,
    )
    sig = misc.sign_identity(client, identity, hidden, visual)
    assert sig.address == "17F17smBTX9VTZA9Mj8LM5QGYNZnmziCjL"
    assert (
        sig.public_key.hex()
        == "023a472219ad3327b07c18273717bb3a40b39b743756bf287fbd5fa9d263237f45"
    )
    assert (
        sig.signature.hex()
        == "20f2d1a42d08c3a362be49275c3ffeeaa415fc040971985548b9f910812237bb41770bf2c8d488428799fbb7e52c11f1a3404011375e4080e077e0e42ab7a5ba02"
    )

    # URI  : ftp://satoshi@bitcoin.org:2323/pub
    # hash : 79a6b53831c6ff224fb283587adc4ebae8fb0d734734a46c876838f52dff53f3
    # path : m/2147483661/3098912377/2734671409/3632509519/3125730426
    identity = messages.IdentityType(
        proto="ftp",
        user="satoshi",
        host="bitcoin.org",
        port="2323",
        path="/pub",
        index=3,
    )
    sig = misc.sign_identity(client, identity, hidden, visual)
    assert sig.address == "1KAr6r5qF2kADL8bAaRQBjGKYEGxn9WrbS"
    assert (
        sig.public_key.hex()
        == "0266cf12d2ba381c5fd797da0d64f59c07a6f1b034ad276cca6bf2729e92b20d9c"
    )
    assert (
        sig.signature.hex()
        == "20bbd12dc657d534fc0f7e40186e22c447e0866a016f654f380adffa9a84e9faf412a1bb0ae908296537838cf91145e77da08681c63d07b7dca40728b9e6cb17cf"
    )

    # URI  : ssh://satoshi@bitcoin.org
    # hash : 5fa612f558a1a3b1fb7f010b2ea0a25cb02520a0ffa202ce74a92fc6145da5f3
    # path : m/2147483661/4111640159/2980290904/2332131323/3701645358
    identity = messages.IdentityType(
        proto="ssh", user="satoshi", host="bitcoin.org", port="", path="", index=47
    )
    sig = misc.sign_identity(
        client, identity, hidden, visual, ecdsa_curve_name="nist256p1"
    )
    assert sig.address is None
    assert (
        sig.public_key.hex()
        == "0373f21a3da3d0e96fc2189f81dd826658c3d76b2d55bd1da349bc6c3573b13ae4"
    )
    assert (
        sig.signature.hex()
        == "005122cebabb852cdd32103b602662afa88e54c0c0c1b38d7099c64dcd49efe908288114e66ed2d8c82f23a70b769a4db723173ec53840c08aafb840d3f09a18d3"
    )

    # URI  : ssh://satoshi@bitcoin.org
    # hash : 5fa612f558a1a3b1fb7f010b2ea0a25cb02520a0ffa202ce74a92fc6145da5f3
    # path : m/2147483661/4111640159/2980290904/2332131323/3701645358
    identity = messages.IdentityType(
        proto="ssh", user="satoshi", host="bitcoin.org", port="", path="", index=47
    )
    sig = misc.sign_identity(
        client, identity, hidden, visual, ecdsa_curve_name="ed25519"
    )
    assert sig.address is None
    assert (
        sig.public_key.hex()
        == "000fac2a491e0f5b871dc48288a4cae551bac5cb0ed19df0764d6e721ec5fade18"
    )
    assert (
        sig.signature.hex()
        == "00f05e5085e666429de397c70a081932654369619c0bd2a6579ea6c1ef2af112ef79998d6c862a16b932d44b1ac1b83c8cbcd0fbda228274fde9e0d0ca6e9cb709"
    )

    # URI  : gpg://satoshi@bitcoin.org
    identity = messages.IdentityType(
        proto="gpg", user="satoshi", host="bitcoin.org", port="", path=""
    )
    sig = misc.sign_identity(
        client, identity, hidden, visual, ecdsa_curve_name="ed25519"
    )
    assert sig.address is None
    assert (
        sig.public_key.hex()
        == "00d18cdf4dbdbb50ef1fdba1ae0539451f3354a366d6a35313712ab82f16d4cd9e"
    )
    assert (
        sig.signature.hex()
        == "00f47f1a09a2875b971811ebbece19c3004c3ecbe84e65666dc8c36cc2fc002544af8a3f545375ebe53d73b41c700df2f9020256c31bb774a7eb03ed9819226407"
    )

    # URI  : signify://satoshi@bitcoin.org
    identity = messages.IdentityType(
        proto="signify", user="satoshi", host="bitcoin.org", port="", path=""
    )
    sig = misc.sign_identity(
        client, identity, hidden, visual, ecdsa_curve_name="ed25519"
    )
    assert sig.address is None
    assert (
        sig.public_key.hex()
        == "0038c0f42c0e47b233e837763098f029fd01009b74fdf4b0d60db114fb0f4f8b17"
    )
    assert (
        sig.signature.hex()
        == "009bb30a7a894e6cdd86e2b75803745e93bd5294b979f9e00ce9dc870642c7f6ad7322af4c54d401ea793494e8a5fdf2bf8b88c6e875094512bd67b94f9188000d"
    )
