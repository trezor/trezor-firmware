
import pandas as pd
import numpy as np
from pathlib import Path
from dataclasses import dataclass

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

def load_measured_data(data_file_path: Path,
                       extern_temp_file_path:Path = None) -> BatteryAnalysisData:

    profile_data = pd.read_csv(data_file_path)

    # Extract data from the DataFrame
    time_vector           = profile_data["time"].to_numpy()
    power_state_vector    = profile_data["power_state"].to_numpy()
    usb_vector            = profile_data["usb"].to_numpy()
    wlc_vector            = profile_data["wlc"].to_numpy()
    battery_voltage_vector = profile_data["battery_voltage"].to_numpy()
    battery_current_vector = profile_data["battery_current"].to_numpy()
    battery_temp_vector   = profile_data["battery_temp"].to_numpy()
    battery_soc_vector    = profile_data["battery_soc"].to_numpy()
    battery_soc_latched_vector = profile_data["battery_soc_latched"].to_numpy()
    pmic_die_temp_vector  = profile_data["pmic_die_temp"].to_numpy()
    wlc_voltage_vector    = profile_data["wlc_voltage"].to_numpy()
    wlc_current_vector    = profile_data["wlc_current"].to_numpy()
    wlc_die_temp_vector   = profile_data["wlc_die_temp"].to_numpy()
    system_voltage_vector = profile_data["system_voltage"].to_numpy()

    if extern_temp_file_path is not None:
        # Load external temperature data if provided
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
        ext_temp=ext_temp_vector
    )