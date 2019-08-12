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

from trezorlib import ckd_public


def test_ckd_public():
    xpub1 = "xpub661MyMwAqRbcEnKbXcCqD2GT1di5zQxVqoHPAgHNe8dv5JP8gWmDproS6kFHJnLZd23tWevhdn4urGJ6b264DfTGKr8zjmYDjyDTi9U7iyT"
    node1 = ckd_public.deserialize(xpub1)
    node2 = ckd_public.public_ckd(node1, [0])
    node3 = ckd_public.public_ckd(node1, [0, 0])
    xpub2 = ckd_public.serialize(node2)
    xpub3 = ckd_public.serialize(node3)
    assert (
        xpub2
        == "xpub67ymn1YTdE2iSGXitxUEZeUdHF2FsejJATroeAxVMtzTAK9o3vjmFLrE7TqE1X76iobkVc3p8h3gNzNRTwPeQGYW3CCmYCG8n5ThVkXaQzs"
    )
    assert (
        xpub3
        == "xpub6BD2MwdEg5PJPqiGetL9DJs7oDo6zP3XwAABX2vAQb5eLpY3QhHGUEm25V4nkQhnFMsqEVfTwtax2gKz8EFrt1PnBN6xQjE9jGmWDR6modu"
    )
