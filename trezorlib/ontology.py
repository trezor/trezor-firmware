# This file is part of the Trezor project.
#
# Copyright (C) 2012-2018 SatoshiLabs and contributors
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

from . import messages
from .tools import expect

#
# Ontology functions
#


@expect(messages.OntologyAddress, field="address")
def get_address(client, address_n, show_display=False):
    return client.call(
        messages.OntologyGetAddress(address_n=address_n, show_display=show_display)
    )


@expect(messages.OntologyPublicKey)
def get_public_key(client, address_n, show_display=False):
    return client.call(
        messages.OntologyGetPublicKey(address_n=address_n, show_display=show_display)
    )


@expect(messages.OntologySignedTransfer)
def sign_transfer(client, address_n, t, tr):
    return client.call(
        messages.OntologySignTransfer(address_n=address_n, transaction=t, transfer=tr)
    )


@expect(messages.OntologySignedWithdrawOng)
def sign_withdrawal(client, address_n, t, w):
    return client.call(
        messages.OntologySignWithdrawOng(
            address_n=address_n, transaction=t, withdraw_ong=w
        )
    )


@expect(messages.OntologySignedOntIdRegister)
def sign_register(client, address_n, t, r):
    return client.call(
        messages.OntologySignOntIdRegister(
            address_n=address_n, transaction=t, ont_id_register=r
        )
    )


@expect(messages.OntologySignedOntIdAddAttributes)
def sign_add_attr(client, address_n, t, a):
    return client.call(
        messages.OntologySignOntIdAddAttributes(
            address_n=address_n, transaction=t, ont_id_add_attributes=a
        )
    )
