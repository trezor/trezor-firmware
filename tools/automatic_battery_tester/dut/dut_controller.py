from __future__ import annotations

import logging
import sys
from dataclasses import dataclass
from pathlib import Path

from hardware_ctl.relay_controller import RelayController

from .dut import Dut


@dataclass
class ProdtestPmReport:
    """pm-report command response data structure"""

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

    @classmethod
    def from_string_list(cls, data: list[str]) -> "ProdtestPmReport":
        """Parse a list of strings into a ProdtestPmReport instance."""
        try:
            return cls(
                power_state=str(data[0]),
                usb=str(data[1]),
                wlc=str(data[2]),
                battery_voltage=float(data[3]),
                battery_current=float(data[4]),
                battery_temp=float(data[5]),
                battery_soc=int(float(data[6])),
                battery_soc_latched=int(float(data[7])),
                pmic_die_temp=float(data[8]),
                wlc_voltage=float(data[9]),
                wlc_current=float(data[10]),
                wlc_die_temp=float(data[11]),
                system_voltage=float(data[12]),
            )
        except (IndexError, ValueError, TypeError) as e:
            logging.error(f"Failed to parse pm-report data: {data} ({e})")
            return cls()


class DutController:
    """
    Device-under-test (DUT) controller.
    provides direct simultaneous control of configured DUTs
    """

    def __init__(
        self, duts: list[dict], relay_ctl: RelayController, verbose: bool = False
    ) -> None:

        self.duts = []
        self.relay_ctl = relay_ctl

        # Power off all DUTs before self test
        for d in duts:
            self.relay_ctl.set_relay_off(d["relay_port"])

        for d in duts:

            try:
                dut = Dut(
                    name=d["name"],
                    cpu_id=d["cpu_id"],
                    usb_port=d["usb_port"],
                    relay_port=d["relay_port"],
                    relay_ctl=self.relay_ctl,
                    verbose=verbose,
                )
                self.duts.append(dut)
                logging.info(f"Initialized {d['name']} on port {d['usb_port']}")
                logging.info(f" -- cpu_id hash : {dut.get_cpu_id_hash()}")
                logging.info(f" -- relay port  : {dut.get_relay_port()}")

            except Exception as e:
                logging.critical(
                    f"Failed to initialize DUT {d['name']} on port {d['usb_port']}: {e}"
                )
                sys.exit(1)

        if len(self.duts) == 0:
            logging.error("No DUTs initialized. Cannot proceed.")
            raise RuntimeError("No DUTs initialized. Check port configuration.")

    def power_up_all(self) -> None:

        for d in self.duts:
            d.power_up()

    def power_down_all(self) -> None:

        for d in self.duts:
            d.power_down()

    def enable_charging(self) -> None:
        """
        Enable charging on all DUTs.
        """
        for d in self.duts:
            try:
                d.enable_charging()
            except Exception as e:
                logging.error(f"Failed to enable charging on {d.name}: {e}")

    def disable_charging(self) -> None:
        """
        Disable charging on all DUTs.
        """
        for d in self.duts:
            try:
                d.disable_charging()
            except Exception as e:
                logging.error(f"Failed to disable charging on {d.name}: {e}")

    def set_soc_limit(self, soc_limit: int) -> None:
        """
        Set the state of charge (SoC) limit for all DUTs.
        :param soc_limit: The SoC limit to set (0-100).
        """
        for d in self.duts:
            try:
                d.set_soc_limit(soc_limit)
            except Exception as e:
                logging.error(f"Failed to set SoC limit on {d.name}: {e}")

    def all_duts_charged(self) -> bool:

        all_dut_charged = True

        for d in self.duts:

            # Read power report
            data = d.read_report()

            if data.battery_voltage >= 3.3 and abs(data.battery_current) < 0.1:
                # Charging completed
                d.disable_charging()
            else:
                all_dut_charged = False

        return all_dut_charged

    def all_duts_discharged(self) -> bool:

        all_dut_dischargerd = True

        for d in self.duts:

            # Read power report
            data = d.read_report()

            # Device start to shutdown, turn the power on.
            if data.power_state == "3":

                # Attach power
                d.disable_charging()
                d.power_up()

            elif data.usb == "USB_connected":
                # USB is connected, device already finish the discharge cycle
                continue
            else:
                # Discharging not completed
                all_dut_dischargerd = False

        return all_dut_dischargerd

    def any_dut_charged(self) -> bool:

        for d in self.duts:
            # Read power report
            data = d.read_report()

            if data.battery_voltage >= 3.3 and abs(data.battery_current) < 0.1:
                # Charging completed
                return True

        return False

    def any_dut_discharged(self) -> bool:

        for d in self.duts:
            # Read power report
            data = d.read_report()

            if data.power_state == "3":
                # Device start to shutdown, turn the power on.
                d.disable_charging()
                d.power_up()
                return True
            elif data.usb == "USB_connected":
                # USB is connected, device already finish the discharge cycle
                return True

        return False

    def set_backlight(self, value: int) -> None:

        for d in self.duts:
            try:
                d.set_backlight(value)
            except Exception as e:
                logging.error(f"Failed to set backlight on {d.name}: {e}")

    def log_data(
        self,
        output_directory: Path,
        test_time_id: str,
        test_scenario: str,
        test_phase: str,
        temp: float | int,
    ) -> None:

        # Log file name format:
        # > <device_id_hash>.<time_identifier>.<test_scenario>.<temperarture>.csv
        # Example: a8bf.2506091307.linear.charge.25_deg.csv

        for d in self.duts:
            d.log_data(output_directory, test_time_id, test_scenario, test_phase, temp)

    def close(self) -> None:
        for d in self.duts:
            try:
                d.close()
            except Exception as e:
                logging.error(f"Failed to close DUT {d.name}: {e}")

    def __del__(self) -> None:
        self.close()
