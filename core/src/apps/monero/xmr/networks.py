class NetworkTypes:
    MAINNET = 0
    TESTNET = 1
    STAGENET = 2
    FAKECHAIN = 3


class MainNet:
    PUBLIC_ADDRESS_BASE58_PREFIX = 18
    PUBLIC_INTEGRATED_ADDRESS_BASE58_PREFIX = 19
    PUBLIC_SUBADDRESS_BASE58_PREFIX = 42


class TestNet:
    PUBLIC_ADDRESS_BASE58_PREFIX = 53
    PUBLIC_INTEGRATED_ADDRESS_BASE58_PREFIX = 54
    PUBLIC_SUBADDRESS_BASE58_PREFIX = 63


class StageNet:
    PUBLIC_ADDRESS_BASE58_PREFIX = 24
    PUBLIC_INTEGRATED_ADDRESS_BASE58_PREFIX = 25
    PUBLIC_SUBADDRESS_BASE58_PREFIX = 36


def net_version(
    network_type=NetworkTypes.MAINNET, is_subaddr=False, is_integrated=False
):
    """
    Network version bytes used for address construction
    """
    if is_integrated and is_subaddr:
        raise ValueError("Subaddress cannot be integrated")

    c_net = None
    if network_type is None or network_type == NetworkTypes.MAINNET:
        c_net = MainNet
    elif network_type == NetworkTypes.TESTNET:
        c_net = TestNet
    elif network_type == NetworkTypes.STAGENET:
        c_net = StageNet
    else:
        raise ValueError("Unknown network type: %s" % network_type)

    prefix = c_net.PUBLIC_ADDRESS_BASE58_PREFIX
    if is_subaddr:
        prefix = c_net.PUBLIC_SUBADDRESS_BASE58_PREFIX
    elif is_integrated:
        prefix = c_net.PUBLIC_INTEGRATED_ADDRESS_BASE58_PREFIX

    return bytes([prefix])
