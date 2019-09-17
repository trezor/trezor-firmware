# This file is part of the Trezor project.
#
# Copyright (C) 2019 SatoshiLabs and contributors
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


from . import messages as proto
from .tools import expect


@expect(proto.WebAuthnCredentials, field="credentials")
def list_credentials(client):
    return client.call(proto.WebAuthnListResidentCredentials())


@expect(proto.Success, field="message")
def add_credential(client, credential_id):
    return client.call(proto.WebAuthnAddResidentCredential(credential_id))


@expect(proto.Success, field="message")
def remove_credential(client, index):
    return client.call(proto.WebAuthnRemoveResidentCredential(index))
