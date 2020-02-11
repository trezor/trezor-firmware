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


@expect(messages.OntologyPublicKey, field="public_key")
def get_public_key(client, address_n, show_display=False):
    return client.call(
        messages.OntologyGetPublicKey(address_n=address_n, show_display=show_display)
    )


@expect(messages.OntologySignedTx, field="signature")
def sign(client, address_n, t, msg):
    if isinstance(msg, messages.OntologyTransfer):
        return client.call(
            messages.OntologySignTx(address_n=address_n, transaction=t, transfer=msg)
        )
    elif isinstance(msg, messages.OntologyWithdrawOng):
        return client.call(
            messages.OntologySignTx(
                address_n=address_n, transaction=t, withdraw_ong=msg
            )
        )
    elif isinstance(msg, messages.OntologyOntIdRegister):
        return client.call(
            messages.OntologySignTx(
                address_n=address_n, transaction=t, ont_id_register=msg
            )
        )
    elif isinstance(msg, messages.OntologyOntIdAddAttributes):
        return client.call(
            messages.OntologySignTx(
                address_n=address_n, transaction=t, ont_id_add_attributes=msg
            )
        )
