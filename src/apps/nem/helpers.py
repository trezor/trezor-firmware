
from micropython import const

NEM_NETWORK_MAINNET = const(0x68)
NEM_NETWORK_TESTNET = const(0x98)
NEM_NETWORK_MIJIN = const(0x60)
NEM_CURVE = 'ed25519-keccak'


def nem_validate_network(network):
    if network in (NEM_NETWORK_MAINNET, NEM_NETWORK_TESTNET, NEM_NETWORK_MIJIN):
        return network
    if network is None:
        return NEM_NETWORK_MAINNET
    raise ValueError('Invalid NEM network')
