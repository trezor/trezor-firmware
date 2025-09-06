from dataclasses import dataclass
from pathlib import Path

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


from typing import Union, List
from pathlib import Path
import numpy as np
import pandas as pd

def load_measured_data(
    data_file_paths: Union[Path, List[Path]], 
    extern_temp_file_path: Path = None
) -> BatteryAnalysisData:
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
            print(f"⚠️ Skipping {file_path.name} — not enough time data (len={len(t)})")
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

