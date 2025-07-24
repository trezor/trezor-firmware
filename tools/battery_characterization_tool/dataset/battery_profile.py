from dataclasses import dataclass
from pathlib import Path
from typing import List, Union

import numpy as np
import pandas as pd


@dataclass
class BatteryAnalysisData:
    time: np.ndarray
    power_state: np.ndarray
    usb: np.ndarray
    wlc: np.ndarray
    battery_voltage: np.ndarray
    battery_current: np.ndarray
    battery_temp: np.ndarray
    battery_soc: np.ndarray
    battery_soc_latched: np.ndarray
    pmic_die_temp: np.ndarray
    wlc_voltage: np.ndarray
    wlc_current: np.ndarray
    wlc_die_temp: np.ndarray
    system_voltage: np.ndarray
    ext_temp_time: np.ndarray = None  # Optional time vector for external temperature
    ext_temp: np.ndarray = None  # Optional external temperature data

    # Legacy attribute fallback support
    def __getattr__(self, name):
        legacy_map = {
            "ibat": "battery_current",
            "vbat": "battery_voltage",
            "temp": "battery_temp",
            "soc": "battery_soc",
            "ntc_temp": "battery_temp",
        }
        if name in legacy_map:
            return getattr(self, legacy_map[name])
        raise AttributeError(
            f"'{type(self).__name__}' object has no attribute '{name}'"
        )


def load_battery_profile(
    data_file_paths: Union[Path, List[Path]], extern_temp_file_path: Path = None
) -> BatteryAnalysisData:
    """
    Load battery profile data from one or more CSV files and return as a BatteryAnalysisData object.
    if multiple files are provided, they are concatenated into a single dataset

    Args:
        data_file_paths: Path(s) to the CSV file(s) containing battery profile data.
        extern_temp_file_path: Optional path to an external temperature CSV file.

    Returns:
        BatteryAnalysisData: An object containing the loaded battery profile data.
    """

    if isinstance(data_file_paths, Path):
        data_file_paths = [data_file_paths]

    # Lists to hold data
    time_list = []
    power_state_list = []
    usb_list = []
    wlc_list = []
    battery_voltage_list = []
    battery_current_list = []
    battery_temp_list = []
    battery_soc_list = []
    battery_soc_latched_list = []
    pmic_die_temp_list = []
    wlc_voltage_list = []
    wlc_current_list = []
    wlc_die_temp_list = []
    system_voltage_list = []

    time_offset = 0

    for file_path in data_file_paths:
        profile_data = pd.read_csv(file_path)

        # Handle corrupted or missing columns early
        if "time" not in profile_data.columns:
            raise ValueError(f"Missing 'time' column in file: {file_path.name}")

        # Convert time to numpy array
        t = profile_data["time"].to_numpy()

        if len(t) < 2:
            print(f"SKIPPING: {file_path.name} — not enough time data (len={len(t)})")
            continue  # skip this file

        # Normalize and apply offset to maintain continuous time
        t = t - t[0] + time_offset
        time_offset = t[-1] + (t[1] - t[0])  # Next file starts just after this one ends

        # Append adjusted time and all other columns
        time_list.append(t)
        power_state_list.append(profile_data["power_state"].to_numpy())
        usb_list.append(profile_data["usb"].to_numpy())
        wlc_list.append(profile_data["wlc"].to_numpy())
        battery_voltage_list.append(profile_data["battery_voltage"].to_numpy())
        battery_current_list.append(profile_data["battery_current"].to_numpy())
        battery_temp_list.append(profile_data["battery_temp"].to_numpy())
        battery_soc_list.append(profile_data["battery_soc"].to_numpy())
        battery_soc_latched_list.append(profile_data["battery_soc_latched"].to_numpy())
        pmic_die_temp_list.append(profile_data["pmic_die_temp"].to_numpy())
        wlc_voltage_list.append(profile_data["wlc_voltage"].to_numpy())
        wlc_current_list.append(profile_data["wlc_current"].to_numpy())
        wlc_die_temp_list.append(profile_data["wlc_die_temp"].to_numpy())
        system_voltage_list.append(profile_data["system_voltage"].to_numpy())

    # If no valid data was found, raise error before concatenation
    if not time_list:
        raise ValueError("No valid data found in provided file(s).")

    # Concatenate all data
    time_vector = np.concatenate(time_list)
    power_state_vector = np.concatenate(power_state_list)
    usb_vector = np.concatenate(usb_list)
    wlc_vector = np.concatenate(wlc_list)
    battery_voltage_vector = np.concatenate(battery_voltage_list)
    battery_current_vector = np.concatenate(battery_current_list)
    battery_temp_vector = np.concatenate(battery_temp_list)
    battery_soc_vector = np.concatenate(battery_soc_list)
    battery_soc_latched_vector = np.concatenate(battery_soc_latched_list)
    pmic_die_temp_vector = np.concatenate(pmic_die_temp_list)
    wlc_voltage_vector = np.concatenate(wlc_voltage_list)
    wlc_current_vector = np.concatenate(wlc_current_list)
    wlc_die_temp_vector = np.concatenate(wlc_die_temp_list)
    system_voltage_vector = np.concatenate(system_voltage_list)

    # Load external temp
    if extern_temp_file_path is not None:
        ext_temp_data = pd.read_csv(extern_temp_file_path)
        ext_temp_time_vector = ext_temp_data["time"].to_numpy()
        ext_temp_vector = ext_temp_data["temperature"].to_numpy()
    else:
        ext_temp_time_vector = None
        ext_temp_vector = None

    return BatteryAnalysisData(
        time=time_vector,
        power_state=power_state_vector,
        usb=usb_vector,
        wlc=wlc_vector,
        battery_voltage=battery_voltage_vector,
        battery_current=battery_current_vector,
        battery_temp=battery_temp_vector,
        battery_soc=battery_soc_vector,
        battery_soc_latched=battery_soc_latched_vector,
        pmic_die_temp=pmic_die_temp_vector,
        wlc_voltage=wlc_voltage_vector,
        wlc_current=wlc_current_vector,
        wlc_die_temp=wlc_die_temp_vector,
        system_voltage=system_voltage_vector,
        ext_temp_time=ext_temp_time_vector,
        ext_temp=ext_temp_vector,
    )


def cut_charging_phase(data):
    """
    Isolate the first continuous charging phase from the given dataset and return it as a
    np.array. Only returns the first continuous set of indices where ibat < 0.
    """

    # Find all indices where current is negative (charging)
    # np.where returns a tuple, we want the first (and only) array of indices
    where_result = np.where(data.battery_current < 0)
    all_charge_indices = where_result[0]

    if len(all_charge_indices) == 0:
        raise ValueError("No charging phase found in the data (no negative current)")

    # Find the first continuous set of indices
    # Look for breaks in continuity (where difference > 1)
    diff = np.diff(all_charge_indices)
    break_points = np.where(diff > 1)[0]

    if len(break_points) == 0:
        # All indices are continuous
        charge_indices = all_charge_indices
    else:
        # Take only the first continuous segment
        first_break = break_points[0]
        charge_indices = all_charge_indices[: first_break + 1]

    if len(break_points) > 0:
        print(
            f"Note: Skipped {len(break_points)} additional charging segments to ensure continuity"
        )

    charge_data = BatteryAnalysisData(
        time=data.time[charge_indices],
        power_state=data.power_state[charge_indices],
        usb=data.usb[charge_indices],
        wlc=data.wlc[charge_indices],
        battery_voltage=data.battery_voltage[charge_indices],
        battery_current=data.battery_current[charge_indices],
        battery_temp=data.battery_temp[charge_indices],
        battery_soc=data.battery_soc[charge_indices],
        battery_soc_latched=data.battery_soc_latched[charge_indices],
        pmic_die_temp=data.pmic_die_temp[charge_indices],
        wlc_voltage=data.wlc_voltage[charge_indices],
        wlc_current=data.wlc_current[charge_indices],
        wlc_die_temp=data.wlc_die_temp[charge_indices],
        system_voltage=data.system_voltage[charge_indices],
        ext_temp_time=(
            data.ext_temp_time[charge_indices]
            if data.ext_temp_time is not None
            else None
        ),
        ext_temp=data.ext_temp[charge_indices] if data.ext_temp is not None else None,
    )

    # Offset time vector to start at 0
    charge_data.time = charge_data.time - charge_data.time[0]

    return charge_data


def cut_discharging_phase(data):
    """
    Isolate the first continuous discharging phase from the given dataset and return it as a
    np.array. Only returns the first continuous set of indices where ibat > 0.
    """

    # Find all indices where current is positive (discharging)
    where_result = np.where(data.battery_current > 0)
    all_discharge_indices = where_result[0]

    if len(all_discharge_indices) == 0:
        raise ValueError("No discharging phase found in the data (no positive current)")

    # Find the first continuous set of indices
    diff = np.diff(all_discharge_indices)
    break_points = np.where(diff > 1)[0]

    if len(break_points) == 0:
        discharge_indices = all_discharge_indices
    else:
        first_break = break_points[0]
        discharge_indices = all_discharge_indices[: first_break + 1]

    discharge_data = BatteryAnalysisData(
        time=data.time[discharge_indices],
        power_state=data.power_state[discharge_indices],
        usb=data.usb[discharge_indices],
        wlc=data.wlc[discharge_indices],
        battery_voltage=data.battery_voltage[discharge_indices],
        battery_current=data.battery_current[discharge_indices],
        battery_temp=data.battery_temp[discharge_indices],
        battery_soc=data.battery_soc[discharge_indices],
        battery_soc_latched=data.battery_soc_latched[discharge_indices],
        pmic_die_temp=data.pmic_die_temp[discharge_indices],
        wlc_voltage=data.wlc_voltage[discharge_indices],
        wlc_current=data.wlc_current[discharge_indices],
        wlc_die_temp=data.wlc_die_temp[discharge_indices],
        system_voltage=data.system_voltage[discharge_indices],
        ext_temp_time=(
            data.ext_temp_time[discharge_indices]
            if data.ext_temp_time is not None
            else None
        ),
        ext_temp=(
            data.ext_temp[discharge_indices] if data.ext_temp is not None else None
        ),
    )

    discharge_data.time = discharge_data.time - discharge_data.time[0]

    return discharge_data


def get_mean_temp(temp):
    mean = sum(temp) / len(temp)
    variance = (1 / mean) * np.sum((temp - mean) ** 2)
    return mean, variance


def time_to_minutes(time, offset=None):
    if offset is None:
        return (time - time[0]) / 60000
    else:
        return (time - offset) / 60000
