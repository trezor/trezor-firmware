
from micropython import const

_NEM_NETWORK_MAINNET = const(0x68)
_NEM_NETWORK_TESTNET = const(0x98)
_NEM_NETWORK_MIJIN = const(0x60)


def nem_validate_network(network):
    if network in (_NEM_NETWORK_MAINNET, _NEM_NETWORK_TESTNET, _NEM_NETWORK_MIJIN):
        return network
    if network is None:
        return _NEM_NETWORK_MAINNET
    raise ValueError('Invalid NEM network')
