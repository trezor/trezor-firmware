import logging
import signal
import socket
from typing import Any, List

from typing_extensions import Self

IP = "192.168.1.10"  # default static IP address
PORT = 9912
PIN_COUNT = 16  # Total number of pins on the Deditec BS-WEU-16 board


class DeditecBsWeu16:

    def __init__(self, ip: str = IP, port: int = PORT, timeout_seconds: int = 3):

        self.ip = ip
        self.port = port
        self.timeout_seconds = max(1, timeout_seconds)
        self.socket: socket.socket | None = None
        self.pins_on_latched = []

        logging.debug(f"DeditecBsWeu16: instance created on {self.ip}:{self.port}")

    def connect(self) -> bool:
        if self.socket is not None:
            logging.warning(
                "DeditecBsWeu16: connect called, but socket already exists. Closing first."
            )
            self.close_connection()

        logging.debug(
            f"DeditecBsWeu16: connecting to device at {self.ip}:{self.port}..."
        )
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.timeout_seconds)
            self.socket.connect((self.ip, self.port))
            logging.debug("DeditecBsWeu16: connection established")
            return True
        except socket.timeout:
            logging.error(
                f"DeditecBsWeu16: connection timed out ({self.timeout_seconds}s)"
            )
            self.socket = None
            return False
        except Exception as e:
            logging.exception(f"DeditecBsWeu16: connection error >  {e}")
            self.socket = None
            return False

    def send_command(self, command: bytes):

        if self.socket is None:
            logging.error("DeditecBsWeu16: send_command called but not connected.")
            return False

        logging.debug(f"DeditecBsWeu16: sending command: {command!r}")
        try:
            self.socket.sendall(command)
            data = self.socket.recv(64)
            logging.debug(
                f"DeditecBsWeu16: received confirmation data (len={len(data)}): {data!r}"
            )
            return True
        except socket.timeout:
            logging.error(
                f"DeditecBsWeu16: socket timeout during send/recv ({self.timeout_seconds}s)"
            )
            return False
        except Exception as e:
            logging.exception(
                f"DeditecBsWeu16: error sending command or receiving confirmation: {e}"
            )
            return False

    def control_relay(self, pins_on: List[int], pins_off: List[int]) -> bool:
        """Turns on all pins specified in pins_on list and turns off all pins specified in pins_off list.
        Returns True if successful, False otherwise.
        """

        if not self.socket:
            logging.error("DeditecBsWeu16: Relay not connected.")
            return False

        for pin in pins_on:
            if not 1 <= pin <= PIN_COUNT:
                logging.error(f"DeditecBsWeu16: Invalid pin number {pin} in pins_on.")
                return False

        for pin in pins_off:
            if not 1 <= pin <= PIN_COUNT:
                logging.error(f"DeditecBsWeu16: Invalid pin number {pin} in pins_off.")
                return False

        # Update the list of
        self.pins_on_latched = list(set(self.pins_on_latched + pins_on) - set(pins_off))
        command = self.assabmle_command(self.pins_on_latched)

        if not self.send_command(command):
            logging.error("DeditecBsWeu16: Failed to send command to Deditec device.")
            return False

        logging.info(
            f"DeditecBsWeu16: Changed relay setup. Pins ON: {self.pins_on_latched}"
        )

        return True

    def assabmle_command(self, pins: List[int]) -> bytes:
        """Assembles the command to turn on specified pins on the Deditec BS-WEU-16 board."""
        command_prefix = b"\x63\x9a\x01\x01\x00\x0b\x57\x57\x00\x00"

        pin_mask_value = 0
        for pin in set(pins):  # Ensure uniqueness
            if isinstance(pin, int) and 1 <= pin <= PIN_COUNT:
                pin_mask_value += 2 ** (pin - 1)
            else:
                logging.warning(
                    f"DeditecBsWeu16: Invalid pin number provided to assabmle_command: {pin}. Ignoring."
                )

        command = command_prefix + pin_mask_value.to_bytes(2, byteorder="big")
        return command

    def close_connection(self) -> None:
        if self.socket:
            logging.debug("DeditecBsWeu16: closing connection")
            try:
                self.socket.close()
            except Exception as e:
                logging.error(f"DeditecBsWeu16: error closing socket: {e}")
            finally:
                self.socket = None
        else:
            logging.debug("Deditec:: close_connection called but already closed.")

    def __enter__(self) -> Self:

        try:
            signal.alarm(self.timeout_seconds + 1)
        except ValueError:
            logging.warning(
                "Cannot set SIGALRM handler (not on Unix main thread?), relying on socket timeout."
            )
            pass

        if not self.connect():
            signal.alarm(0)
            raise ConnectionError(
                f"Failed to connect to Deditec device at {self.ip}:{self.port}"
            )

        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:

        try:
            signal.alarm(0)
        except ValueError:
            pass
        self.close_connection()

        if exc_type:
            logging.error(
                f"Deditec:: An error occurred during 'with' block: {exc_type.__name__}: {exc_val}"
            )
        return False
