# hardware_ctl/relay_controller.py

import logging
import time
import platform
import subprocess
import sys
from typing import List, Optional, Set
from pathlib import Path

libs_path = Path(__file__).parent.parent / "libs"
if str(libs_path) not in sys.path:
    sys.path.insert(0, str(libs_path))

# Import Deditec drives
try:

    from .deditec_driver.deditec_1_16_on import Deditec_1_16_on
    from .deditec_driver.helpers import (get_pins_on, save_new_pins_on,
                         get_new_pins_on, turn_on_pins_command)

except ImportError as e:
    logging.error(f"ERROR: Failed to import Deditec modules")

class RelayController:

    DEDITEC_PORT = 9912
    MAX_PIN = 16 # Max PIN index (1-16)

    def __init__(self, ip_address: str):
        """
        Initilize relay controller.

        Args:
            ip_address: Deditec board IP addres.
        """

        self.ip_address = ip_address
        self.port = self.DEDITEC_PORT

        logging.info(f"Initializing Relay Controller for Deditec at {self.ip_address}:{self.DEDITEC_PORT}")

        # Ping the device to check connectivity
        if not self.check_ping(self.ip_address):
            logging.warning("Ping to Deditec relay board failed. Network issue possible, but attempting TCP check.")

        if not self._check_deditec_connection(self.ip_address, self.port):
            logging.error("CRITICAL: Failed to establish TCP connection with Deditec relay board.")

    def _check_deditec_connection(self, ip: str, port: int, timeout: int = 2) -> bool:

        logging.info(f"Checking Deditec connection to {ip}:{port} (timeout={timeout}s)...")

        try:
            with Deditec_1_16_on(ip=ip, port=port, timeout_seconds=timeout) as tester:
                logging.info("Deditec connection established successfuly.")
                return True
        except ConnectionError as e: logging.error(f"Deditec connection failed: {e}"); return False
        except TimeoutError: logging.error(f"Deditec connection timed out."); return False
        except Exception as e: logging.error(f"Unexpected error during Deditec connection check: {e}"); return False


    def check_ping(self, ip: str) -> bool:

        """ Ping the given IP address """
        logging.info(f"Pinging {ip}...")
        system = platform.system().lower()
        if system == "windows":
            command = ["ping", "-n", "1", "-w", "1000", ip] # Timeout 1000ms
        else: # Linux, macOS
            command = ["ping", "-c", "1", "-W", "1", ip] # Timeout 1s

        try:

            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = process.communicate(timeout=3) # Celkový timeout procesu
            return_code = process.returncode

            logging.debug(f"Ping stdout:\n{stdout}")

            if stderr: logging.debug(f"Ping stderr:\n{stderr}")

            if return_code == 0:

                 # Doplňková kontrola (může být závislá na jazyku systému)
                if "unreachable" in stdout.lower() or "timed out" in stdout.lower() or "ttl expired" in stdout.lower():
                     logging.error(f"Ping to {ip} technically succeeded (code 0) but output indicates failure.")
                     return False

                logging.info(f"Ping to {ip} successful.")
                return True
            else:

                logging.error(f"Ping to {ip} failed (return code: {return_code}).")
                return False

        except FileNotFoundError:
            logging.error("Ping command not found. Install ping or check PATH. Skipping ping check.")
            return True

        except subprocess.TimeoutExpired:
            logging.error(f"Ping process to {ip} timed out.")
            return False

        except Exception as e:
            logging.error(f"Unknown error during ping check: {e}")
            return False

    def _execute_relay_command(self, pins_to_turn_on: List[int], pins_to_turn_off: List[int]) -> bool:

        try:
            # 1. Zjistit nový celkový stav
            new_pins_state = get_new_pins_on(pins_to_turn_on, pins_to_turn_off, all_off=False)
            logging.debug(f"Calculating new relay state: Request ON={pins_to_turn_on}, Request OFF={pins_to_turn_off} -> New total ON state: {new_pins_state}")

            # 2. Připravit command
            command_bytes = turn_on_pins_command(new_pins_state)
            logging.debug(f"Generated command bytes: {command_bytes!r}")

            # 3. Odeslat command
            logging.debug(f"Connecting to Deditec at {self.ip_address}:{self.port} to send command...")
            with Deditec_1_16_on(ip=self.ip_address, port=self.port, timeout_seconds=3) as controller: # Timeout pro spojení
                response = controller.send_command(command_bytes) # Použije timeout socketu definovaný v Deditec_1_16_on

            # 4. Zkontrolovat a uložit
            if response == 0:
                logging.debug("Command sent successfully. Saving new state to cache.")
                save_new_pins_on(new_pins_state)
                logging.debug(f"Relay state updated. Currently ON: {get_pins_on()}") # Zobrazit aktuální stav z cache
                return True
            else:
                logging.error(f"Deditec device returned unexpected response code: {response}")
                return False

        except ConnectionError as e: logging.error(f"Failed to connect to Deditec at {self.ip_address}: {e}"); return False
        except TimeoutError: logging.error(f"Timeout communicating with Deditec at {self.ip_address}"); return False
        except Exception as e: logging.exception(f"An unexpected error occurred during relay operation: {e}"); return False

    def set_relay_off(self, pin: int) -> bool:
        return self._execute_relay_command(pins_to_turn_on=[],
                                           pins_to_turn_off=[pin])

    def set_relay_on(self, pin: int) -> bool:
        return self._execute_relay_command(pins_to_turn_on=[pin],
                                           pins_to_turn_off=[])

    def turn_all_relays_off(self) -> bool:
         """Turn off all relays."""
         logging.info("Turning all relays OFF.")
         # Vytvoříme seznam všech pinů (1 až MAX_PIN)
         all_pins = list(range(1, self.MAX_PIN + 1))
         return self._execute_relay_command(pins_to_turn_on=[], pins_to_turn_off=all_pins)

    def close(self):
         pass
