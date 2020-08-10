MAINNET = 1
TESTNET = 0


def is_mainnet(network_id: int) -> bool:
    """
    In the future there might be 15 mainnet IDs and
    still only one testnet ID. Therefore it is safer
    to check that it is not a testnet id. Also, if
    the mainnet id was to change, this would still work.
    """
    return network_id != TESTNET
