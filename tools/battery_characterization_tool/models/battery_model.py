import hashlib
import json
import os
from pathlib import Path

import numpy as np


class BatteryModel:

    def __init__(self, battery_model_data, file_name_hash, override_hash=None):
        self.battery_model_data = battery_model_data

        # Keep original keys as they are (could be float or string)
        self.temp_keys_list = list(self.battery_model_data["ocv_curves"].keys())
        self.temp_keys_f_list = [float(key) for key in self.temp_keys_list]

        # Create separate temperature key lists for charging and discharging
        self.temp_keys_chg_list = []
        self.temp_keys_dischg_list = []

        for temp_key in self.temp_keys_list:
            ocv_data = self.battery_model_data["ocv_curves"][temp_key]
            if "bat_temp_chg" in ocv_data:
                self.temp_keys_chg_list.append(ocv_data["bat_temp_chg"])
            if "bat_temp_dischg" in ocv_data:
                self.temp_keys_dischg_list.append(ocv_data["bat_temp_dischg"])

        self.soc_breakpoint_1 = 0.25
        self.soc_breakpoint_2 = 0.8

        if override_hash is not None:
            self.model_hash = override_hash
        else:
            self.model_hash = self._generate_hash(file_name_hash)

        print(f"Battery model + file names hash: {self.model_hash}")
        print(
            f"Charge temperature range: {min(self.temp_keys_chg_list):.1f}°C to {max(self.temp_keys_chg_list):.1f}°C"
        )
        print(
            f"Discharge temperature range: {min(self.temp_keys_dischg_list):.1f}°C to {max(self.temp_keys_dischg_list):.1f}°C"
        )

    def _find_temp_curves(self, target_temp, discharge_mode):
        """
        Find the temperature curve keys that bracket the target temperature.
        Returns (lower_key, upper_key, lower_temp, upper_temp) for interpolation.
        """
        # Choose the appropriate temperature list based on mode
        if discharge_mode:
            temp_list = self.temp_keys_dischg_list
        else:
            temp_list = self.temp_keys_chg_list

        # Clamp temperature to available range
        target_temp = max(min(target_temp, max(temp_list)), min(temp_list))

        # Find the curves that bracket this temperature
        for i, temp_key in enumerate(self.temp_keys_list):
            ocv_data = self.battery_model_data["ocv_curves"][temp_key]
            actual_temp = (
                ocv_data["bat_temp_dischg"]
                if discharge_mode
                else ocv_data["bat_temp_chg"]
            )

            if actual_temp >= target_temp:
                if i == 0:
                    # Use first curve for both points
                    return temp_key, temp_key, actual_temp, actual_temp
                else:
                    # Find previous curve
                    prev_key = self.temp_keys_list[i - 1]
                    prev_data = self.battery_model_data["ocv_curves"][prev_key]
                    prev_temp = (
                        prev_data["bat_temp_dischg"]
                        if discharge_mode
                        else prev_data["bat_temp_chg"]
                    )
                    return prev_key, temp_key, prev_temp, actual_temp

        # If we get here, use the last curve
        last_key = self.temp_keys_list[-1]
        last_data = self.battery_model_data["ocv_curves"][last_key]
        last_temp = (
            last_data["bat_temp_dischg"]
            if discharge_mode
            else last_data["bat_temp_chg"]
        )
        return last_key, last_key, last_temp, last_temp

    def _generate_hash(self, file_name_hash):

        def convert_np(obj):
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            raise TypeError(
                f"Object of type {obj.__class__.__name__} is not JSON serializable"
            )

        def recursive_sort(obj):
            if isinstance(obj, dict):
                return {k: recursive_sort(v) for k, v in sorted(obj.items())}
            elif isinstance(obj, list):
                return sorted(recursive_sort(x) for x in obj)
            else:
                return obj

        def round_floats(obj, precision=8):
            if isinstance(obj, dict):
                return {k: round_floats(v, precision) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [round_floats(x, precision) for x in obj]
            elif isinstance(obj, float):
                return round(obj, precision)
            else:
                return obj

        # Clean data for stable serialization
        clean_data = round_floats(recursive_sort(self.battery_model_data))

        # Use pretty-printing with indentation for consistent hashing
        data_str = json.dumps(clean_data, sort_keys=True, default=convert_np, indent=2)
        data_hash = hashlib.sha256(data_str.encode("utf-8")).hexdigest()

        combined = f"{data_hash}|{file_name_hash}"
        final_hash = hashlib.sha256(combined.encode("utf-8")).hexdigest()
        return final_hash[:8]

    def get_hash(self):
        """
        Returns the hash of the battery model data.
        This is used to identify the model uniquely.
        """
        return self.model_hash

    @classmethod
    def from_json(cls, json_dict, model_hash):
        """Used when loading an existing model from disk."""
        return cls(json_dict, file_name_hash=model_hash, override_hash=model_hash)

    # ========== Public methods for battery model ==========

    def _meas_to_ocv(self, voltage_V, current_mA, temp_deg):
        ocv_V = voltage_V + ((current_mA / 1000) * self._rint(temp_deg))
        return ocv_V

    def _rint(self, temp_deg):

        temp_deg = max(
            min(temp_deg, self.temp_keys_f_list[-1]), self.temp_keys_f_list[0]
        )

        [a, b, c, d] = self.battery_model_data["r_int"]
        return (a + b * temp_deg) / (c + d * temp_deg)

    def _total_capacity(self, temp_deg, discharging_mode):
        """
        Get total capacity at given temperature and mode, using actual temperature keys.
        """
        key1, key2, temp1, temp2 = self._find_temp_curves(temp_deg, discharging_mode)

        ocv_curves = self.battery_model_data["ocv_curves"]

        if discharging_mode:
            capacity1 = ocv_curves[key1]["total_capacity_dischg"]
            capacity2 = ocv_curves[key2]["total_capacity_dischg"]
        else:
            capacity1 = ocv_curves[key1]["total_capacity_chg"]
            capacity2 = ocv_curves[key2]["total_capacity_chg"]

        if temp1 == temp2:
            return capacity1
        else:
            return self._linear_interpolation(
                capacity1, capacity2, temp1, temp2, temp_deg
            )

    def _linear_interpolation(self, y1, y2, x1, x2, x):
        """
        Linear interpolation between two points and given x between them.
        (x1,y1) - First known point on the line
        (x2,y2) - Secodnf known point on the line
        x - Interpolated value, following rule have to apply (x1 < x < x2)
        """
        a = (y2 - y1) / (x2 - x1)
        b = y2 - a * x2
        return a * x + b

    def _interpolate_ocv_at_temp(self, soc, temp, discharge_mode):
        """
        Interpolate OCV at given temperature using actual temperature keys for charge/discharge.
        """
        key1, key2, temp1, temp2 = self._find_temp_curves(temp, discharge_mode)

        voc1 = self._ocv(
            self.battery_model_data["ocv_curves"][key1], soc, discharge_mode
        )
        voc2 = self._ocv(
            self.battery_model_data["ocv_curves"][key2], soc, discharge_mode
        )

        if temp1 == temp2:
            return voc1
        else:
            return self._linear_interpolation(voc1, voc2, temp1, temp2, temp)

    def _interpolate_soc_at_temp(self, ocv, temp, discharge_mode):
        """
        Interpolate SOC at given temperature using actual temperature keys for charge/discharge.
        """
        key1, key2, temp1, temp2 = self._find_temp_curves(temp, discharge_mode)

        ocv_curves = self.battery_model_data["ocv_curves"]

        soc1 = self._soc(ocv_curves[key1], ocv, discharge_mode)
        soc2 = self._soc(ocv_curves[key2], ocv, discharge_mode)

        if temp1 == temp2:
            return soc1
        else:
            return self._linear_interpolation(soc1, soc2, temp1, temp2, temp)

    def _intrepolate_ocv_slope_at_temp(self, soc, temp, discharge_mode):
        """
        Calculate the slope of the SOC curve at a given SOC and temperature.
        The slope is calculated as the derivative of the SOC function.
        The derivative is piecewise defined, so we need to check which
        segment the SOC falls into and calculate the slope accordingly.
        """
        key1, key2, temp1, temp2 = self._find_temp_curves(temp, discharge_mode)

        ocv_curves = self.battery_model_data["ocv_curves"]

        slope1 = self._ocv_slope(ocv_curves[key1], soc, discharge_mode)
        slope2 = self._ocv_slope(ocv_curves[key2], soc, discharge_mode)

        if temp1 == temp2:
            return slope1
        else:
            return self._linear_interpolation(slope1, slope2, temp1, temp2, temp)

    def _ocv(self, ocv_curve, soc, discharge_mode):
        """
        Calculate OCV from SOC using the appropriate curve for charge/discharge mode.
        """
        soc = max(min(soc, 1), 0)

        if discharge_mode:
            [m, b, a1, b1, c1, d1, a3, b3, c3, d3] = ocv_curve["ocv_dischg"]
        else:
            [m, b, a1, b1, c1, d1, a3, b3, c3, d3] = ocv_curve["ocv_chg"]

        if soc < self.soc_breakpoint_1:
            # First segment (rational)
            return (a1 + b1 * soc) / (c1 + d1 * soc)
        elif self.soc_breakpoint_1 <= soc <= self.soc_breakpoint_2:
            # Middle segment (linear)
            return m * soc + b
        elif soc > self.soc_breakpoint_2:
            # Third segment (rational)
            return (a3 + b3 * soc) / (c3 + d3 * soc)

        raise ValueError("SOC is out of range")

    def _ocv_slope(self, ocv_curve, soc, discharge_mode):
        """
        Calculate the slope of the OCV curve at a given SOC.
        The slope is calculated as the derivative of the OCV function.
        The derivative is piecewise defined, so we need to check which
        segment the SOC falls into and calculate the slope accordingly.
        """

        if discharge_mode:
            [m, _, a1, b1, c1, d1, a3, b3, c3, d3] = ocv_curve["ocv_dischg"]
        else:
            [m, _, a1, b1, c1, d1, a3, b3, c3, d3] = ocv_curve["ocv_chg"]

        if soc < self.soc_breakpoint_1:
            # First segment (rational)
            return (b1 * c1 - a1 * d1) / ((c1 + d1 * soc) ** 2)
        elif self.soc_breakpoint_1 <= soc <= self.soc_breakpoint_2:
            # Middle segment (linear)
            return m
        elif soc > self.soc_breakpoint_2:
            # Third segment (rational)
            return (b3 * c3 - a3 * d3) / ((c3 + d3 * soc) ** 2)
        raise ValueError("SOC is out of range")

    def _soc(self, ocv_curve, ocv, discharge_mode):

        ocv_breakpoint_1 = self._ocv(ocv_curve, self.soc_breakpoint_1, discharge_mode)
        ocv_breakpoint_2 = self._ocv(ocv_curve, self.soc_breakpoint_2, discharge_mode)

        if discharge_mode:
            [m, b, a1, b1, c1, d1, a3, b3, c3, d3] = ocv_curve["ocv_dischg"]
        else:
            [m, b, a1, b1, c1, d1, a3, b3, c3, d3] = ocv_curve["ocv_chg"]

        if ocv < ocv_breakpoint_1:
            # First segment (rational)
            return (a1 - c1 * ocv) / (d1 * ocv - b1)
        elif ocv_breakpoint_1 <= ocv <= ocv_breakpoint_2:
            # Middle segment (linear)
            return (ocv - b) / m
        elif ocv > ocv_breakpoint_2:
            # Third segment (rational)
            return (a3 - c3 * ocv) / (d3 * ocv - b3)

        raise ValueError("OCV is out of range")


# ========FUNCTIONS FOR JSON SERIALIZATION==========


def round_floats(obj, precision=8):
    if isinstance(obj, dict):
        return {k: round_floats(v, precision) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [round_floats(x, precision) for x in obj]
    elif isinstance(obj, float):
        return round(obj, precision)
    else:
        return obj


def recursive_sort(obj):
    if isinstance(obj, dict):
        return {k: recursive_sort(v) for k, v in sorted(obj.items())}
    elif isinstance(obj, list):
        return [recursive_sort(x) for x in obj]  # DO NOT SORT LISTS
    else:
        return obj


def convert_np(obj):
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")


def prepare_for_serialization(data):
    """Sort, round, and convert numpy for consistent hashing/serialization."""
    return round_floats(data)


def export_battery_model_to_json(battery_model, directory):
    """
    Saves the BatteryModel to a JSON file named <model_hash>.json in the specified directory,
    using rounded data for integrity.
    """
    os.makedirs(directory, exist_ok=True)
    file_name = f"{battery_model.battery_model_data['battery_vendor']}_{battery_model.model_hash}.json"
    file_path = os.path.join(directory, file_name)

    clean_data = prepare_for_serialization(battery_model.battery_model_data)

    with open(file_path, "w") as f:
        json.dump(clean_data, f, indent=2, default=convert_np)

    return battery_model.model_hash


def load_battery_model_from_hash(model_file_path):
    """
    Loads a BatteryModel from the specified JSON file path.
    Extracts the hash from the filename and prepares the loaded data
    identically to preserve hash integrity.
    """

    file_path = Path(model_file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"No battery model file found at: {model_file_path}")

    # Extract hash from filename (format: <vendor>_<hash>.json)
    filename = file_path.stem  # Remove .json extension
    if "_" in filename:
        # Split by last underscore to get hash
        parts = filename.rsplit("_", 1)
        if len(parts) == 2:
            model_hash = parts[1]
        else:
            # Fallback: use entire filename as hash
            model_hash = filename
    else:
        # Fallback: use entire filename as hash
        model_hash = filename

    with open(file_path, "r") as f:
        battery_model_data = json.load(f)

    # Prepare data to ensure the same hash calculation (if needed)
    battery_model_data = prepare_for_serialization(battery_model_data)

    # Create BatteryModel instance with the extracted hash
    return BatteryModel.from_json(battery_model_data, model_hash)
