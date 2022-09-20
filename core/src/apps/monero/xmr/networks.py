from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.enums import MoneroNetworkType


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
    network_type: MoneroNetworkType = None,
    is_subaddr: bool = False,
    is_integrated: bool = False,
) -> bytes:
    """
    Network version bytes used for address construction
    """
    from trezor.enums import MoneroNetworkType

    if network_type is None:
        network_type = MoneroNetworkType.MAINNET

    if is_integrated and is_subaddr:
        raise ValueError("Subaddress cannot be integrated")

    c_net = None
    if network_type == MoneroNetworkType.MAINNET:
        c_net = MainNet
    elif network_type == MoneroNetworkType.TESTNET:
        c_net = TestNet
    elif network_type == MoneroNetworkType.STAGENET:
        c_net = StageNet
    else:
        raise ValueError(f"Unknown network type: {network_type}")

    prefix = c_net.PUBLIC_ADDRESS_BASE58_PREFIX
    if is_subaddr:
        prefix = c_net.PUBLIC_SUBADDRESS_BASE58_PREFIX
    elif is_integrated:
        prefix = c_net.PUBLIC_INTEGRATED_ADDRESS_BASE58_PREFIX

    return bytes([prefix])
