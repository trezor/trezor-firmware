from typing import TYPE_CHECKING, List

from . import messages
from .tools import expect

if TYPE_CHECKING:
    from .client import TrezorClient
    from .protobuf import MessageType


@expect(messages.SolanaPublicKey)
def get_public_key(
    client: "TrezorClient",
    address_n: List[int],
) -> "MessageType":
    return client.call(messages.SolanaGetPublicKey(address_n=address_n))
