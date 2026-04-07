# hardware_ctl/relay_controller.py

import logging
import platform
import subprocess
import sys

# Import Deditec drives
from .deditec import DeditecBsWeu16


class RelayController:

    DEDITEC_PORT = 9912
    MAX_PIN = 16  # Max PIN index (1-16)

    def __init__(self, ip_address: str) -> None:
        """
        Initilize relay controller.

        Args:
            ip_address: Deditec board IP addres.
        """

        self.ip_address = ip_address
        self.port = self.DEDITEC_PORT

        # Ping the device to check connectivity
        if not self.check_ping(self.ip_address):
            logging.warning(
                "Ping to Deditec relay board failed. Network issue possible, but attempting TCP check."
            )

        self.deditec = DeditecBsWeu16(ip=self.ip_address, port=self.port)

        # Connect to deditec relay board
        if not self.deditec.connect():
            logging.error(
                f"Failed to connect to Deditec relay board at {self.ip_address}:{self.DEDITEC_PORT}."
            )
            sys.exit(1)

    def check_ping(self, ip: str) -> bool:
        """Ping the given IP address"""
        logging.info(f"Pinging {ip}...")
        system = platform.system().lower()
        if system == "windows":
            command = ["ping", "-n", "1", "-w", "1000", ip]
        else:  # Linux, macOS
            command = ["ping", "-c", "1", "-W", "1", ip]

        try:

            process = subprocess.Popen(
                command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            stdout, stderr = process.communicate(timeout=3)
            return_code = process.returncode

            logging.debug(f"Ping stdout:\n{stdout}")

            if stderr:
                logging.debug(f"Ping stderr:\n{stderr}")

            if return_code == 0:

                if (
                    "unreachable" in stdout.lower()
                    or "timed out" in stdout.lower()
                    or "ttl expired" in stdout.lower()
                ):
                    logging.error(
                        f"Ping to {ip} technically succeeded (code 0) but output indicates failure."
                    )
                    return False

                logging.info(f"Ping to {ip} successful.")
                return True
            else:

                logging.error(f"Ping to {ip} failed (return code: {return_code}).")
                return False

        except FileNotFoundError:
            logging.error(
                "Ping command not found. Install ping or check PATH. Skipping ping check."
            )
            return True

        except subprocess.TimeoutExpired:
            logging.error(f"Ping process to {ip} timed out.")
            return False

        except Exception as e:
            logging.error(f"Unknown error during ping check: {e}")
            return False

    def set_relay_off(self, pin: int) -> bool:

        if not self.deditec:
            logging.error("RelayController: Deditec not initialized.")
            return False

        return self.deditec.control_relay(pins_on=[], pins_off=[pin])

    def set_relay_on(self, pin: int) -> bool:

        if not self.deditec:
            logging.error("RelayController: Deditec not initialized.")
            return False

        return self.deditec.control_relay(pins_on=[pin], pins_off=[])

    def close(self) -> None:
        pass
