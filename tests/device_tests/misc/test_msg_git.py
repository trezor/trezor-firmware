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

import pytest

from trezorlib import messages
from trezorlib.debuglink import TrezorClientDebugLink as Client


@pytest.mark.setup_client()
def test_git_commit(client: Client):
    commit_hash = bytes.fromhex(
        "5fdba3602b41c19312862dc6c4aec0ca7aa5f45fe00ad310bbbb58bd139a48dc"
    )
    update = messages.GitCommitUpdate(commit_hash=commit_hash)
    client.call(update, messages.Success)

    commit, *trees, blob = [
        b"tree 7a3a25665e2743820a77a53956a56db312225b146c9f92ec821c98841acb79c6\nauthor Roman Zeyde <roman.zeyde@satoshilabs.com> 1746850908 +0300\ncommitter Roman Zeyde <roman.zeyde@satoshilabs.com> 1746850908 +0300\n\ninit\n",
        b"100644 FooBar\x003\xb0A\x82\xf3\x89\x7f\xe7\xba\xd7{\xfe\xcaS\xd2\xc9\x14\x9d\x8b]\xc4J\x8d\t\xab\xf8!%s\x14\xdb\x13",
        b"13Hbso8zgV5Wmqn3uA7h3QVtmPzs47wcJ7\n",
    ]
    msg = messages.GitVerify(commit=commit, trees=trees, blob=blob, path=["FooBar"])
    client.call(msg, messages.Success)


# In [1]: sp.check_output("git cat-file commit 5fdba3602b41c19312862dc6c4aec0ca7aa5f45fe00ad310bbbb58bd139a48dc", shell=True)
# Out[1]: b'tree 7a3a25665e2743820a77a53956a56db312225b146c9f92ec821c98841acb79c6\nauthor Roman Zeyde <roman.zeyde@satoshilabs.com> 1746850908 +0300\ncommitter Roman Zeyde <roman.zeyde@satoshilabs.com> 1746850908 +0300\n\ninit\n'

# In [2]: sp.check_output("git cat-file tree 7a3a25665e2743820a77a53956a56db312225b146c9f92ec821c98841acb79c6", shell=True)
# Out[2]: b'100644 FooBar\x003\xb0A\x82\xf3\x89\x7f\xe7\xba\xd7{\xfe\xcaS\xd2\xc9\x14\x9d\x8b]\xc4J\x8d\t\xab\xf8!%s\x14\xdb\x13'

# In [3]: sp.check_output("git cat-file blob 33b04182f3897fe7bad77bfeca53d2c9149d8b5dc44a8d09abf821257314db13", shell=True)
# Out[3]: b'13Hbso8zgV5Wmqn3uA7h3QVtmPzs47wcJ7\n'
