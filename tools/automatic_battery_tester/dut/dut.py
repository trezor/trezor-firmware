import serial
import time
import logging
import hashlib

from dataclasses import dataclass, field
from typing import List
from pathlib import Path
from hardware_ctl.relay_controller import RelayController

BAUDRATE_DEFAULT = 115200
BYTESIZE_DEFAULT = 8
PARITY_DEFAULT   = serial.PARITY_NONE
CMD_TIMEOUT      = 10

@dataclass
class DutReportData:
    time: float = 0.0
    power_state: str = ""
    usb: str = ""
    wlc: str = ""
    battery_voltage: float = 0.0
    battery_current: float = 0.0
    battery_temp: float = 0.0
    battery_soc: int = 0
    battery_soc_latched: int = 0
    pmic_die_temp: float = 0.0
    wlc_voltage: float = 0.0
    wlc_current: float = 0.0
    wlc_die_temp: float = 0.0
    system_voltage: float = 0.0

@dataclass
class DutProdtestResponse:
    timestamp: float | None = None
    cmd: str | None = None
    trace: list = field(default_factory=list)
    data_entries: list = field(default_factory=list)
    OK: bool = False


class Dut():

    def __init__(self, name, cpu_id, usb_port, relay_port, relay_ctl, verbose=False):

        self.name = name
        self.relay_ctl = relay_ctl
        self.verbose = verbose
        self.relay_port = relay_port

        # Power up the device with relay controller
        self.power_up()

        # Wait for device to boot up
        time.sleep(3)

        self.vcp = serial.Serial(port=usb_port,
                                baudrate=BAUDRATE_DEFAULT,
                                bytesize=BYTESIZE_DEFAULT,
                                parity=PARITY_DEFAULT)

        # Connect serial port
        if(not self.vcp.is_open):
            self.init_error()
            raise RuntimeError(f"Failed to open serial port {usb_port} for DUT {name}")

        self.entry_interactive_mode()
        self.enable_charging()

        time.sleep(2) # Give some time to process te commands

        if not self.ping():
            self.init_error()
            raise RuntimeError(f"DUT {self.name} did not respond to ping command")

        self.cpu_id = self.get_cpuid()
        if self.cpu_id is None:
            self.init_error()
            raise RuntimeError(f"DUT {self.name} failed to retrieve CPU ID")

        logging.debug(f"DUT {self.name} initialized with CPU ID: {self.cpu_id}")

        self.cpu_id_hash = self.generate_id_hash(self.cpu_id)

        if(self.cpu_id != cpu_id):
            self.init_error()
            raise RuntimeError(f"DUT {self.name} CPU ID mismatch: expected {cpu_id}, got {self.cpu_id}")

        logging.debug(f"DUT {self.name} ID hash: {self.cpu_id_hash}")

        # device should start charging
        report = self.read_report()
        if not (report.usb == "USB_connected"):
            self.init_error()
            raise RuntimeError(f"{self.name} USB not connected. Check VCP and relay ports")

        self.display_ok()
        self.disable_charging()
        self.power_down()

    def init_error(self):
        self.display_error()
        self.disable_charging()
        self.power_down()

    def display_error(self):
        self.display_bars("R")
        time.sleep(3)

    def display_ok(self):
        self.display_bars("G")
        time.sleep(3)

    def __del__(self):
        self.vcp.close()
        self.vcp = None

    def get_cpu_id_hash(self):
        return self.cpu_id_hash

    def get_relay_port(self):
        return self.relay_port

    def generate_id_hash(self, cpu_id):
        """
        Generate a unique ID hash for the DUT based on its CPU ID.
        :param cpu_id: The CPU ID of the DUT.
        :return: A unique ID hash string.
        """
        if cpu_id is None:
            raise ValueError("CPU ID cannot be None.")

        device_id_bytes = bytes.fromhex(cpu_id)
        digest = hashlib.sha256(device_id_bytes).digest()
        return digest[:2].hex()

    def set_verbose(self, verbose):
        self.verbose = verbose

    def get_verbose(self):
        return self.verbose

    def entry_interactive_mode(self):
        # Enter interactive mode
        self.send_command(".", skip_response=True)

    def power_up(self):
        """
        Power up the DUT by activating the relay.
        """
        if self.relay_port is None:
            raise ValueError("Relay port not set for DUT.")
        self.relay_ctl.set_relay_on(self.relay_port)

    def power_down(self):
        """
        Power down the DUT by deactivating the relay.
        """
        if self.relay_port is None:
            raise ValueError("Relay port not set for DUT.")
        self.relay_ctl.set_relay_off(self.relay_port)

    def display_bars(self, value: str):
        """
        Display bars on the DUT's screen.
        :param value: A string representing the bars to display (e.g., "G" for green).
        :return: True if the command was successful, False otherwise.
        """
        response = self.send_command("display-bars", value)
        return response.OK

    def ping(self):
        """
        Send a ping command to the DUT and wait for a response.
        Returns True if the DUT responds with "OK", False otherwise.
        """
        response = self.send_command("ping")
        return response.OK

    def enable_charging(self):

        response = self.send_command("pm-charge-enable")
        return response.OK

    def disable_charging(self):

        response = self.send_command("pm-charge-disable")
        return response.OK

    def set_soc_limit(self, soc_limit: int):

        """
        Set the state of charge (SoC) limit for the DUT.
        :param soc_limit: The SoC limit to set (0-100).
        :return: True if the command was successful, False otherwise.
        """
        if not (0 <= soc_limit <= 100):
            raise ValueError("SoC limit must be between 0 and 100.")

        response = self.send_command("pm-set-soc-limit", soc_limit)
        return response.OK

    def set_backlight(self, value: int):

        if not (0 <= value <= 255):
            raise ValueError("Backlight value must be between 0 and 255.")

        response = self.send_command("display-set-backlight", value)

        return response.OK

    def get_cpuid(self):

        response = self.send_command("get-cpuid")
        if not response.OK:
            return None

        if len(response.data_entries) == 0:
            # No cpuid in data entries
            return None

        return response.data_entries[0][0]

    def parse_report(self, response: DutProdtestResponse) -> DutReportData:

        data = DutReportData()
        data.time = response.timestamp
        data.power_state = response.data_entries[0][0]
        data.usb = response.data_entries[0][1]
        data.wlc = response.data_entries[0][2] if response.data_entries else ""
        data.battery_voltage = float(response.data_entries[0][3])
        data.battery_current = float(response.data_entries[0][4])
        data.battery_temp = float(response.data_entries[0][5])
        data.battery_soc = int(float(response.data_entries[0][6]))
        data.battery_soc_latched = int(float(response.data_entries[0][7]))
        data.pmic_die_temp = float(response.data_entries[0][8])
        data.wlc_voltage = float(response.data_entries[0][9])
        data.wlc_current = float(response.data_entries[0][10])
        data.wlc_die_temp = float(response.data_entries[0][11])
        data.system_voltage = float(response.data_entries[0][12])

        return data

    def read_report(self) -> DutReportData:

        """
        Read the PM report from the DUT.
        Returns a ProdtestResponse object containing the report data.
        """
        response = self.send_command("pm-report")
        if not response.OK:
            logging.error(f"Failed to read PM report from {self.name}.")
            return None

        return self.parse_report(response)


    def send_command(self, cmd, *args, skip_response=False):

        if(self.vcp is None):
            raise "VPC not initalized"

        response = DutProdtestResponse()
        # assert(len == 0)

        # Assamble command
        response.cmd = cmd
        if(args):
            response.cmd = response.cmd + ' ' + ' '.join(str(k) for k in args)
        response.cmd = response.cmd + '\n'

        response.timestamp = time.time()

        # Flush serial
        self.vcp.flush()

        self._log_output(response.cmd.rstrip('\r\n'))
        self.vcp.write(response.cmd.encode())

        if(skip_response):
            return response

        while(True):

            line = self.vcp.readline().decode()
            self._log_input(line.strip('\r\n'))

            # Capture traces
            if(line[:1] == "#"):
                response.trace.append(line[2:])

            # Capture data
            if(line[:8] == "PROGRESS"):
                line = line.replace("\r\n", "")
                response.data_entries.append((line[9:].split(" ")))

            # Terminate
            if("OK" in line):

                response.OK = True

                # Check if there is any data comming along with OK
                line = line.replace("\r\n", "")
                response.data_entries.append((line[3:].split(" ")))

                break

            if("ERROR" in line):
                break

        return response

    def log_data(self, output_directory: Path, test_time_id, test_scenario,
                 test_phase, temp):

        # Log file name format:
        # > <device_id_hash>.<time_identifier>.<test_scenario>.<test><temperarture>.csv
        # Example: a8bf.2506091307.linear.charge.25_deg.csv

        file_path = output_directory / f"{self.cpu_id_hash}.{test_time_id}.{test_scenario}.{test_phase}.{temp}.csv"

        report = None
        try:
            report = self.send_command("pm-report")
        except Exception as e:
            logging.error(f"Failed to read PM report from {self.name}, skip log: {e}")
            return

        if not file_path.exists():
            # creat a file header
            with open(file_path, 'w') as f:
                f.write("time,power_state,usb,wlc,battery_voltage,battery_current,"
                        "battery_temp,battery_soc,battery_soc_latched,pmic_die_temp,"
                        "wlc_voltage,wlc_current,wlc_die_temp,system_voltage\n")

        with open(file_path, 'a') as f:
            f.write(str(report.timestamp) + "," +",".join(report.data_entries[0]) + "\n")

    def _log_output(self, message):
        if(self.verbose):
            prefix = f"\033[95m[{self.name}]\033[0m"
            logging.debug(prefix + " > " + message)

    def _log_input(self, message):
        if(self.verbose):
            prefix = f"\033[95m[{self.name}]\033[0m"
            logging.debug(prefix + " < " + message)

    def close(self):
        """
        Close the DUT's serial port and clean up resources.
        """
        if self.vcp is not None and self.vcp.is_open:
            try:
                self.vcp.close()
            except Exception as e:
                logging.warning(f"Failed to close VCP for {self.name}: {e}")
        self.vcp = None
        self.name = None
        self.relay_ctl = None
        self.relay_port = None

    def __del__(self):
        try:
            if hasattr(self, "vcp") and self.vcp is not None and self.vcp.is_open:
                self.close()
        except Exception as e:
            logging.warning(f"Error during DUT cleanup: {e}")
