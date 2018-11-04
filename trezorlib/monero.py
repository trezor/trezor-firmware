from . import messages as proto
from .tools import expect

# MAINNET = 0
# TESTNET = 1
# STAGENET = 2
# FAKECHAIN = 3


@expect(proto.MoneroAddress, field="address")
def get_address(client, n, show_display=False, network_type=0):
    return client.call(
        proto.MoneroGetAddress(
            address_n=n, show_display=show_display, network_type=network_type
        )
    )


@expect(proto.MoneroWatchKey)
def get_watch_key(client, n, network_type=0):
    return client.call(proto.MoneroGetWatchKey(address_n=n, network_type=network_type))
