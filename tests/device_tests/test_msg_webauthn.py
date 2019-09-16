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

from trezorlib import webauthn
from trezorlib.exceptions import Cancelled, TrezorFailure

from ..common import MNEMONIC12

CRED1 = bytes.fromhex(
    "f1d00200f8221312f7898e31ea5ec30409527c2b0bde0b9dfdd7eaab4424173f"
    "bf75ab67627fff60974460d903d7d96bb9e974c169a01b2c38cf2305da304169"
    "d4e28f59053a2564bebb3eb3f06c2182f1ea4a2f7cebd8f92a930a76f3b45334"
    "1e3f3285a575a54bcba9cf8a088dbfe24e8e691a5926160174e03aa941828f49"
    "e42b47804d"
)

CRED2 = bytes.fromhex(
    "f1d00200eb3b566f4ea0a219552b2efd2c76e1ffc2e641d3bf91ec92d47a4ed4"
    "d78cf42845248c4e982a503618bac0cecfb0fa91fa10821df1efe1d59ac8314e"
    "b57eb7f32a1a605f91e8692daf1a679b55ab1acadfded5e0c7fd1365e2801759"
    "bd3a4450dd5589586ab072da79"
)

CRED3 = bytes.fromhex(
    "f1d00200ebee50034eb7affb555602eed0812b63d158b57a4188523ad064a719"
    "febf477c52cfcc7ded8d7a7a83af52287ed1ecee9f74f62b7e55ad8e814c062e"
    "009bb3b3391dfec79dc93053b0279eca7207358a0962865da55668b2509de773"
    "8c819dbeead9997778319ac1f1c7318fd6"
)

CREDS = [
    bytes.fromhex(
        "f1d0020029a297837485bf2b43f2a8cc53b759a03201cf6902cf25794a375214"
        "aea1357cee1e2fa9188e8fb74e5b5501767ca740cd1f0c745bb72afd"
    ),
    bytes.fromhex(
        "f1d00200ce4e44a4d5076b7d3037ca039894738183f18b0ef5edfa84b59ba4e9"
        "2e9ce5fe02ddd6cd397c459636dfb45af740d268bd67610578581cc1"
    ),
    bytes.fromhex(
        "f1d00200776ac8476ac5a621c135e9ab3d5c5c1d836843eddad88f94ff044989"
        "cc941f5971bd3df1a3008e12ad16a11753cdfe113d023784a29bbbe0"
    ),
    bytes.fromhex(
        "f1d00200f4bf428bc3ea21a64691bc1cfb3ae14d4ed29621777856ea81b8936e"
        "51293fb8b073ab1c03fe7016b01f9e2bcac796f3c3c33515ffbf88c2"
    ),
    bytes.fromhex(
        "f1d0020055e4d0a8b06951564f71dd601287929b396013d1b1cfd1ab237a6e1d"
        "b53b7f562465ed53b3fc8ba7f0b5e05498fd13badfaac358694e76f2"
    ),
    bytes.fromhex(
        "f1d00200ea2b8789416aa55dac3e8446da76a9fba3f52722329bf4820480faf1"
        "ed35f2eb8577a0e3bbcecd6177d1a4c21faafc3411281ebbc2a8f100"
    ),
    bytes.fromhex(
        "f1d0020043e37bb7c62fd11b6d446da96741123b38ab9123d695537357373970"
        "8d0e7aaff1ed90306da2779c23fde88c68cd37171c871af4f6c6cc08"
    ),
    bytes.fromhex(
        "f1d00200309ced39cf016b1ae284cd63e48310dd73e14f5f3af681fcfd84e121"
        "6cbab4b1d00f505445b839bca1909521e4ba06209fd161bb98eb2b7d"
    ),
    bytes.fromhex(
        "f1d00200c19e3a3e2ce982419b52487e84ceb42a92bbda1c029b1bb3e832ffa7"
        "0321c22edfb6163ee5ec2be03b1b291f451667a6020a720c41653745"
    ),
    bytes.fromhex(
        "f1d0020046ce52d1ed50a900687d6ba20863cc9c0cd6ee9fb72129a0f63eb598"
        "dcd3cd79c449d251240e2098f4b29e4cfa28ab7b45b77f045589312d"
    ),
    bytes.fromhex(
        "f1d002004f92099262dbedc059237e3aff412204131dad9cbad98147322b00ed"
        "988cd7f7b2ea2f34b0388b3efa1246477d058e4d94773a38355bc2e7"
    ),
    bytes.fromhex(
        "f1d00200ac93867d1bfbe6a6be75d943354f280e32fafce204bcee65db097666"
        "e805b80d38f4f3094f334fb310d4f5cc80ccef603fdd6ba320b4eb73"
    ),
    bytes.fromhex(
        "f1d002006d5d6efbe81fe81927029727409d0f242a4da827947ec55e118cd65c"
        "e6f0d1ae4c7ac578f3682806b5e0e5bfaaf7d0416960ece3fc219516"
    ),
    bytes.fromhex(
        "f1d00200e231eba4d9875231644ff1e38c83be7ce3508401b6184320a2ea3dc2"
        "6092f807aba192c6fc5e7286dfc0e5ccc4738d6d8c8a1a440140b47a"
    ),
    bytes.fromhex(
        "f1d002008841311e477753cbfa4b21779d4c04e7c5532f956f2c6995b99e1392"
        "1143b64b4099c98b4b1c012ef06c1bfa673f192fec193f05cf26c0cc"
    ),
]


@pytest.mark.skip_t1
@pytest.mark.altcoin
class TestMsgWebAuthn:
    @pytest.mark.setup_client(mnemonic=MNEMONIC12)
    def test_add_remove(self, client):
        # Remove index 0 should fail.
        with pytest.raises(TrezorFailure):
            webauthn.remove_credential(client, 0)

        # List should be empty.
        assert webauthn.list_credentials(client) == []

        # Add valid credential #1.
        webauthn.add_credential(client, CRED1)

        # Check that the credential was added and parameters are correct.
        creds = webauthn.list_credentials(client)
        assert len(creds) == 1
        assert creds[0].rp_id == "example.com"
        assert creds[0].rp_name == "Example"
        assert creds[0].user_id == bytes.fromhex(
            "3082019330820138A0030201023082019330820138A003020102308201933082"
        )
        assert creds[0].user_name == "johnpsmith@example.com"
        assert creds[0].user_display_name == "John P. Smith"
        assert creds[0].creation_time == 3
        assert creds[0].hmac_secret is True

        # Add valid credential #2, which has same rpId and userId as credential #1.
        webauthn.add_credential(client, CRED2)

        # Check that the credential #2 replaced credential #1 and parameters are correct.
        creds = webauthn.list_credentials(client)
        assert len(creds) == 1
        assert creds[0].rp_id == "example.com"
        assert creds[0].rp_name is None
        assert creds[0].user_id == bytes.fromhex(
            "3082019330820138A0030201023082019330820138A003020102308201933082"
        )
        assert creds[0].user_name == "johnpsmith@example.com"
        assert creds[0].user_display_name is None
        assert creds[0].creation_time == 2
        assert creds[0].hmac_secret is True

        # Adding an invalid credential should appear as if user cancelled.
        with pytest.raises(Cancelled):
            webauthn.add_credential(client, CRED1[:-2])

        # Check that the credential was not added.
        creds = webauthn.list_credentials(client)
        assert len(creds) == 1

        # Add valid credential, which has same userId as #2, but different rpId.
        webauthn.add_credential(client, CRED3)

        # Check that the credential was added.
        creds = webauthn.list_credentials(client)
        assert len(creds) == 2

        # Fill up with 14 more valid credentials.
        for cred in CREDS[:14]:
            webauthn.add_credential(client, cred)

        # Adding one more valid credential to full storage should fail.
        with pytest.raises(TrezorFailure):
            webauthn.add_credential(client, CREDS[14])

        # Remove index 16 should fail.
        with pytest.raises(TrezorFailure):
            webauthn.remove_credential(client, 16)

        # Remove index 2.
        webauthn.remove_credential(client, 2)

        # Check that the credential was removed.
        creds = webauthn.list_credentials(client)
        assert len(creds) == 15

        # Adding another valid credential should succeed now.
        webauthn.add_credential(client, CREDS[14])

        # Check that the credential was added.
        creds = webauthn.list_credentials(client)
        assert len(creds) == 16
