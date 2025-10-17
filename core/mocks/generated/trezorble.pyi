from typing import *
from buffer_types import *
MAX_BONDS: int


# rust/src/trezorhal/ble/micropython.rs
class BLEIF:
    """
    BLE interface wrapper.
    """
    RX_PACKET_LEN: int
    """Length of one BLE RX packet."""
    TX_PACKET_LEN: int
    """Length of one BLE TX packet."""

    def iface_num(self) -> int:
        """
        Returns the configured number of this interface.
        """

    def write(self, msg: AnyBytes) -> int:
        """
        Sends message over BLE
        """

    def read(self, buf: AnyBuffer, offset: int = 0) -> int:
        """
        Reads message using BLE (device).
        """
interface: BLEIF
"""BLE interface instance."""


# rust/src/trezorhal/ble/micropython.rs
def erase_bonds():
    """
    Erases all BLE bonds.
    Raises exception if BLE reports an error.
    """


# rust/src/trezorhal/ble/micropython.rs
def unpair(addr: AnyBytes | None):
    """
    Erases the bond for the given address or for current connection if addr is None.
    Raises exception if BLE driver reports an error.
    """


# rust/src/trezorhal/ble/micropython.rs
def start_comm():
    """
    Start communication with BLE chip.
    """


# rust/src/trezorhal/ble/micropython.rs
def start_advertising(whitelist: bool, name: str | None):
    """
    Start advertising.
    Raises exception if BLE driver reports an error.
    """


# rust/src/trezorhal/ble/micropython.rs
def set_name(name: str | None):
    """
    Set advertising name.
    """


# rust/src/trezorhal/ble/micropython.rs
def set_high_speed(enable: bool):
    """
    Set high speed connection.
    """


# rust/src/trezorhal/ble/micropython.rs
def switch_off():
    """
    Stop advertising and disconnect any connected devices.
    Raises exception if BLE driver reports an error.
    """


# rust/src/trezorhal/ble/micropython.rs
def disconnect():
    """
    Disconnect BLE.
    Raises exception if BLE driver reports an error.
    """


# rust/src/trezorhal/ble/micropython.rs
def peer_count() -> int:
    """
    Get peer count (number of bonded devices).
    """


# rust/src/trezorhal/ble/micropython.rs
def is_connected() -> bool:
    """
    True if a host is connected to us. May or may not be paired.
    """


# rust/src/trezorhal/ble/micropython.rs
def is_connectable() -> bool:
    """
    True if a central/host can connect.
    """


# rust/src/trezorhal/ble/micropython.rs
def is_pairing() -> bool:
    """
    True if BLE is in pairing mode, waiting for a pairing request.
    """


# rust/src/trezorhal/ble/micropython.rs
def is_pairing_requested() -> bool:
    """
    True if BLE pairing request was received.
    """


# rust/src/trezorhal/ble/micropython.rs
def is_started() -> bool:
    """
    True if BLE subsystem is started.
    """


# rust/src/trezorhal/ble/micropython.rs
def connection_flags() -> list[str]:
    """
    Returns current connection state as a list of string flags.
    """


# rust/src/trezorhal/ble/micropython.rs
def get_bonds() -> list[bytes]:
    """
    Returns a list of addr_bytes, representing the current bonds.
    addr_bytes: bytes of length 6
    """


# rust/src/trezorhal/ble/micropython.rs
def connected_addr() -> bytes | None:
    """
    If connected, returns addr_bytes, otherwise None.
    addr_bytes: bytes of length 6
    """


# rust/src/trezorhal/ble/micropython.rs
def allow_pairing(code: int):
    """
    Accept BLE pairing request. Code must match the one received with
    BLE_PAIRING_REQUEST event.
    Raises exception if BLE driver reports an error.
    """


# rust/src/trezorhal/ble/micropython.rs
def reject_pairing():
    """
    Reject BLE pairing request.
    Raises exception if BLE driver reports an error.
    """


# rust/src/trezorhal/ble/micropython.rs
def set_enabled(bool):
    """
    Enable/Disable BLE.
    """


# rust/src/trezorhal/ble/micropython.rs
def get_enabled() -> bool:
    """
    True if BLE is enabled.
    """
