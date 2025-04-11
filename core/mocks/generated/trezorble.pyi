from typing import *


# rust/src/trezorhal/ble/micropython.rs
class BleInterface:
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

    def write(self, msg: bytes) -> int:
        """
        Sends message over BLE
        """

    def read(self, buf: bytearray, offset: int = 0) -> int:
        """
        Reads message using BLE (device).
        """
interface: BleInterface
"""BLE interface instance."""


# rust/src/trezorhal/ble/micropython.rs
def erase_bonds():
    """
    Erases all BLE bonds.
    Raises exception if BLE reports an error.
    """


# rust/src/trezorhal/ble/micropython.rs
def unpair():
    """
    Erases bond for current connection, if any.
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
def stop_advertising():
    """
    Stop advertising.
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
def connection_flags() -> list[str]:
    """
    Returns current connection state as a list of string flags.
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
