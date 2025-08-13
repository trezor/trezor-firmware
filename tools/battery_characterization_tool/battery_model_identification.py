#!/usr/bin/env python3

import argparse
import sys
import tomllib
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from dataset.battery_dataset import BatteryDataset
from dataset.battery_profile import (
    cut_charging_phase,
    cut_discharging_phase,
    get_mean_temp,
)
from InquirerPy import inquirer
from InquirerPy.base import Choice
from models.battery_model import BatteryModel, export_battery_model_to_json
from models.identification import (
    estimate_ocv_curve,
    estimate_r_int,
    fit_ocv_curve,
    fit_r_int_curve,
    identify_ocv_curve,
    identify_r_int,
)
from utils.c_lib_generator import generate_battery_libraries
from utils.console_formatter import ConsoleFormatter

# Global console formatter instance
console = ConsoleFormatter()

BATTERY_MODEL_CONFIG_FILE_DIR = Path(__file__).parent / "models" / "battery_models"
DATASET_DIRECTORY = Path(__file__).parent / "dataset" / "datasets"
EXPORT_DIR = Path(__file__).parent / "exported_data"
DEFAULT_MAX_CHARGE_VOLTAGE = 3.9
DEFAULT_MAX_DISCHARGE_VOLTAGE = 3.0
DEFAULT_OCV_SAMPLES = 100


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Battery characterization tool for processing battery test data",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--dataset",
        type=str,
        default=None,
        help="Path to the dataset directory containing battery test data",
    )

    parser.add_argument(
        "--config-file",
        type=str,
        default=None,
        help="Path to battery model TOML configuration file",
    )

    parser.add_argument("--debug", action="store_true", help="Enable debug plots")

    parser.add_argument("--trace", action="store_true", help="Enable trace plots")

    return parser.parse_args()


def prompt_for_battery_model_config():
    """Prompt user to select a battery model config from BATTERY_MODEL_CONFIG_FILE_DIR
    .
        Returns:
            BatteryModel: The selected battery model object.
    """

    console.section("Battery Model Selection")

    toml_files = sorted(BATTERY_MODEL_CONFIG_FILE_DIR.glob("*.toml"))
    if not toml_files:
        console.error(f"No .toml files found in {BATTERY_MODEL_CONFIG_FILE_DIR}")
        raise FileNotFoundError("No battery model files found.")

    choices = [Choice(name=file.name, value=file) for file in toml_files]

    selected_file = inquirer.select(
        message="Select a battery model config to load :",
        choices=choices,
    ).execute()

    file_path = selected_file
    console.info(f"Selected file path: {file_path}")

    console.success(f"Selected battery model config file: {file_path.name}")

    return file_path


def prompt_for_dataset() -> BatteryDataset:
    """Prompt user to select a dataset from a DATASET_DIRECTORY and load it
        into a BatteryDataset object.
    Returns:
        BatteryDataset: The selected dataset object.
    """

    console.section("Dataset Selection")

    dataset_folders = [f.name for f in DATASET_DIRECTORY.iterdir() if f.is_dir()]

    if not dataset_folders:
        raise FileNotFoundError("ERROR: No dataset folders found in 'dataset/datasets'")

    choices = [Choice(name=name, value=name) for name in dataset_folders]

    selected_folder = inquirer.select(
        message="Select a dataset folder to load:",
        choices=choices,
    ).execute()

    dataset_path = DATASET_DIRECTORY / selected_folder

    console.success(f"Selected dataset: {dataset_path}")

    return dataset_path


def load_model_config(toml_path):

    try:
        with open(toml_path, "rb") as f:
            model_config = tomllib.load(f)
        console.success(f"Configuration loaded from: {toml_path.name}")
    except Exception as e:
        console.error(f"Failed to load config: {e}")
        sys.exit(1)

    return model_config


def create_battery_dataset(dataset_path) -> BatteryDataset:

    battery_dataset = BatteryDataset(dataset_path, load_data=True)
    battery_dataset.print_structure(max_depth=3)

    return battery_dataset


def run_r_int_identification(dataset, debug=False):
    """Takes all switching discharge profiles from the dataset and for every profile estimates the internal
    resistance. All estimations are then fitted with a rational function and its parametrs are returned.
    """
    console.subsection("Internal Resistance (R_int) Identification")

    r_int_points = []
    profiles = list(
        dataset.get_data_list(
            battery_ids=None,
            temperatures=None,
            battery_modes=["switching"],
            mode_phases=["discharging"],
        )
    )

    total_profiles = len(profiles)
    console.info(f"Found {total_profiles} switching discharge profiles to process")

    # Get all switching discharge profiles across all batteries and temperatures
    for idx, ld_profile in enumerate(profiles, 1):
        profile_data = ld_profile["data"]

        # Progress indicator
        console.progress(
            f"Processing: {ld_profile['battery_id']}.{ld_profile['timestamp_id']}.{ld_profile['temperature']}°C",
            step=idx,
            total=total_profiles,
        )

        # Estimate internal resistance on the switching discharge profile
        r_int_estim = identify_r_int(
            profile_data.time,
            profile_data.battery_current,
            profile_data.battery_voltage,
            profile_data.battery_temp,
            debug=debug,
            test_description=f"{ld_profile['battery_id']} {ld_profile['timestamp_id']} {ld_profile['temperature']}°C discharge",
        )

        # extract mean temperature from the analyzed profile
        mean_temp, _ = get_mean_temp(profile_data.battery_temp)
        r_int_points.append([mean_temp, r_int_estim])

    # Fit rational function to the collected data points
    r_int_vector = np.transpose(np.array(r_int_points))
    r_int_rf_params, _ = fit_r_int_curve(r_int_vector[1], r_int_vector[0], debug)

    # Display results
    console.success(f"Collected {len(r_int_points)} R_int estimations")
    console.info(f"Fitted rational function parameters: {r_int_rf_params}")

    return r_int_rf_params


def run_ocv_identification(dataset, r_int_rf_params, charging=False, debug=False):
    """Takes all linear discharge profiles from the dataset and for every profile extracts the open-circuit voltage"""
    mode_name = "Charging" if charging else "Discharging"
    console.subsection(f"OCV Identification - {mode_name} Profiles")

    ocv_ident_data = {}

    # Get all linear discharge/charge profiles from the dataset across all batteries and temperatures
    profiles = list(
        dataset.get_data_list(
            battery_ids=None,
            temperatures=None,
            battery_modes=["linear"],
            mode_phases=["discharging"] if not charging else ["charging"],
        )
    )

    total_profiles = len(profiles)
    console.info(
        f"Found {total_profiles} linear {mode_name.lower()} profiles to process"
    )

    for idx, ld_profile in enumerate(profiles, 1):
        # Progress indicator
        console.progress(
            f"{ld_profile['battery_id']}.{ld_profile['timestamp_id']}.{ld_profile['temperature']}°C",
            step=idx,
            total=total_profiles,
        )

        # Some of the dataset contain tails from relaxation phase, cut them off`
        if charging:
            profile_data = cut_charging_phase(ld_profile["data"])
        else:
            profile_data = cut_discharging_phase(ld_profile["data"])

        # extract internal resistance from the r_int curve
        real_bat_temp, _ = get_mean_temp(profile_data.battery_temp)
        r_int = estimate_r_int(real_bat_temp, r_int_rf_params)

        # Extract open-circuit voltage (OCV) curve from the linear discharge and charge profiles
        ocv_curve_discharge, total_capacity, effective_capacity = identify_ocv_curve(
            profile_data.time,
            profile_data.battery_voltage,
            profile_data.battery_current,
            r_int,
            max_curve_v=DEFAULT_MAX_CHARGE_VOLTAGE,
            min_curve_v=DEFAULT_MAX_DISCHARGE_VOLTAGE,
            num_of_samples=DEFAULT_OCV_SAMPLES,
            debug=debug,
            test_description=f"{ld_profile['battery_id']} {ld_profile['timestamp_id']} {ld_profile['temperature']}°C {mode_name.lower()}",
        )

        temp_key = ld_profile["temperature"]
        ocv_ident_data.setdefault(
            temp_key,
            {
                "ocv_curve_points": [],
                "total_capacity": [],
                "effective_capacity": [],
                "real_bat_temp": [],
            },
        )

        ocv_ident_data[temp_key]["ocv_curve_points"].append(ocv_curve_discharge)
        ocv_ident_data[temp_key]["total_capacity"].append(total_capacity)
        ocv_ident_data[temp_key]["effective_capacity"].append(effective_capacity)
        ocv_ident_data[temp_key]["real_bat_temp"].append(real_bat_temp)

    console.success(f"Processed {total_profiles} {mode_name.lower()} profiles")
    return ocv_ident_data


def extract_soc_and_rint_curves(
    dataset,
    filter_batteries,
    characterized_temperatures_deg,
    debug=False,
    trace=False,
):

    # characterized_temperatures_deg list has to come sorted, so the model data are in order and model may easily
    # interpolate between the values, this has to be the only place where to sort!
    characterized_temperatures_deg = sorted(
        characterized_temperatures_deg, key=lambda x: float(x)
    )

    filtered_dataset = dataset.filter(
        battery_ids=filter_batteries,
        temperatures=characterized_temperatures_deg,
        battery_modes=["switching", "linear"],
    )

    r_int_rf_params = run_r_int_identification(filtered_dataset, debug=trace)

    ocv_data_discharge = run_ocv_identification(
        filtered_dataset,
        r_int_rf_params,
        charging=False,
        debug=trace,
    )

    ocv_data_charge = run_ocv_identification(
        filtered_dataset,
        r_int_rf_params,
        charging=True,
        debug=trace,
    )

    # All ocv data for charge and discharge profiles are ready, fit the ocv
    # curves and assign them with real battery temperatures, then store them
    # in ocv_curves dict.
    ocv_curves = {}

    for temp in characterized_temperatures_deg:

        ocv_profiles_discharge = np.array(
            [
                np.concatenate(
                    [d[0] for d in ocv_data_discharge[temp]["ocv_curve_points"]]
                ),  # X values concatenated
                np.concatenate(
                    [d[1] for d in ocv_data_discharge[temp]["ocv_curve_points"]]
                ),  # Y values concatenated
            ]
        )

        dsg_ocv_params, dsg_ocv_params_complete = fit_ocv_curve(ocv_profiles_discharge)
        dsg_temp = np.mean(ocv_data_discharge[temp]["real_bat_temp"])
        dsg_ef_cap = np.mean(ocv_data_discharge[temp]["effective_capacity"])
        dsg_total_cap = np.mean(ocv_data_discharge[temp]["total_capacity"])

        ocv_profiles_charge = np.array(
            [
                np.concatenate(
                    [d[0] for d in ocv_data_charge[temp]["ocv_curve_points"]]
                ),  # X values concatenated
                np.concatenate(
                    [d[1] for d in ocv_data_charge[temp]["ocv_curve_points"]]
                ),  # Y values concatenated
            ]
        )

        chg_ocv_params, chg_ocv_params_complete = fit_ocv_curve(ocv_profiles_charge)
        chg_temp = np.mean(ocv_data_charge[temp]["real_bat_temp"])
        chg_ef_cap = np.mean(ocv_data_charge[temp]["effective_capacity"])
        chg_total_cap = np.mean(ocv_data_charge[temp]["total_capacity"])

        ocv_curves[temp] = {
            "ocv_dischg": dsg_ocv_params_complete,
            "ocv_dischg_nc": dsg_ocv_params,
            "bat_temp_dischg": dsg_temp,
            "total_capacity_dischg": dsg_total_cap,
            "effective_capacity_dischg": dsg_ef_cap,
            "ocv_chg": chg_ocv_params_complete,
            "ocv_chg_nc": chg_ocv_params,
            "bat_temp_chg": chg_temp,
            "total_capacity_chg": chg_total_cap,
            "effective_capacity_chg": chg_ef_cap,
        }

    if debug or trace:

        _, ax = plt.subplots(1, 1)
        temps = np.array([float(temp) for temp in characterized_temperatures_deg])

        ax.plot(
            temps,
            estimate_r_int(temps, r_int_rf_params),
            label="R_int (fitted rational function)",
        )
        ax.set_title("R_int Estimation (fitted rational function)")
        ax.set_xlabel("Temperature (°C)")
        ax.set_ylabel("R_int (mΩ)")
        ax.legend()

        _, ax = plt.subplots(1, 1)
        for ocv_curve in ocv_curves.values():

            soc_axis = np.linspace(0, 1, 100)

            ax.plot(
                soc_axis,
                estimate_ocv_curve(soc_axis, ocv_curve["ocv_dischg_nc"]),
                label=f"Discharge {ocv_curve['bat_temp_dischg']}°C",
            )
            ax.plot(
                soc_axis,
                estimate_ocv_curve(soc_axis, ocv_curve["ocv_chg_nc"]),
                label=f"Charge {ocv_curve['bat_temp_chg']}°C",
            )

        ax.set_title("OCV Curves")
        ax.set_xlabel("SoC")
        ax.set_ylabel("Voltage (V)")
        ax.legend()

        _, ax = plt.subplots(1, 1)
        for ocv_curve in ocv_curves.values():

            soc_axis = np.linspace(0, 1, 100)

            ax.plot(
                ocv_curve["bat_temp_dischg"],
                ocv_curve["total_capacity_dischg"],
                "o",
                label=f"Total Capacity Discharge {ocv_curve['bat_temp_dischg']}°C",
            )
            ax.plot(
                ocv_curve["bat_temp_chg"],
                ocv_curve["total_capacity_chg"],
                "o",
                label=f"Total Capacity Charge {ocv_curve['bat_temp_chg']}°C",
            )

        ax.set_title("Total Capacity")
        ax.set_xlabel("Temperature (°C)")
        ax.set_ylabel("Capacity (Ah)")
        ax.legend()

        plt.tight_layout()

    return ocv_curves, r_int_rf_params


def main():

    # Print header
    console.header(
        "BATTERY CHARACTERIZATION TOOL",
        "Advanced Battery Model Identification and Analysis",
        width=85,
    )

    # Parse command line arguments
    args = parse_arguments()

    # Handle config file selection
    if args.config_file:
        config_file_path = Path(args.config_file)

        if not config_file_path.suffix == ".toml":
            console.error("Config file must be a .toml file")
            sys.exit(1)

        if not config_file_path.exists():
            console.error(f"Config file '{config_file_path}' not found.")
            sys.exit(1)
    else:
        config_file_path = prompt_for_battery_model_config()

    # Load config
    console.section("CONFIGURATION SETUP")

    model_config = load_model_config(config_file_path)

    console.key_value_pairs(model_config, "Configuration Summary")
    console.success("Configuration loaded successfully")

    if args.dataset:
        dataset_path = Path(args.dataset)
        if not dataset_path.exists():
            console.error(f"Dataset path '{dataset_path}' does not exist.")
            sys.exit(1)
    else:
        # Prompt user to select a dataset folder
        dataset_path = prompt_for_dataset()

    # Dataset loading section
    console.section("DATASET LOADING")
    console.info("Loading battery dataset...")

    dataset = create_battery_dataset(dataset_path)
    console.success(f"Dataset loaded: {dataset}")

    # Main processing section
    console.section("BATTERY MODEL IDENTIFICATION")
    console.info("Starting battery characterization analysis...")

    ocv_curves, r_int_rf_params = extract_soc_and_rint_curves(
        dataset,
        filter_batteries=None,
        characterized_temperatures_deg=model_config["temperatures_to_process"],
        debug=args.debug,
        trace=args.trace,
    )

    console.success("Battery model identification completed")

    console.section("RESULTS SUMMARY")

    # Create a sample results table
    headers = ["Temperature", "Discharge capacity", "Charge capacity", "R_int"]

    rows = []
    for temp, data in ocv_curves.items():
        rows.append(
            [
                f"{temp}°C",
                f"{data['total_capacity_dischg'] * 1000:.2f} mAh",
                f"{data['total_capacity_chg'] * 1000:.2f} mAh",
                f"{estimate_r_int(float(temp), r_int_rf_params) * 1000:.2f} mΩ",
            ]
        )

    console.table(headers, rows, title="Battery Model Analysis Results")

    console.success("Analysis results table generated")

    console.section("Export battery model")

    # Prepare battery model data
    battery_model_data = {
        "r_int": r_int_rf_params,
        "ocv_curves": ocv_curves,
        "battery_vendor": model_config["battery_manufacturer"],
    }

    battery_model = BatteryModel(battery_model_data, dataset.get_dataset_hash())

    console.info(f"Battery model created with hash: {battery_model.model_hash}")

    export_battery_model_to_json(battery_model, EXPORT_DIR / "battery_models")

    console.success("Battery model JSON file created")

    console.section("Generate C library")

    generate_battery_libraries(
        battery_model_data,
        output_dir=EXPORT_DIR,
        battery_name=model_config["battery_manufacturer"],
    )

    console.success("C library files generated successfully")

    # Show completion summary
    console.footer()

    if args.debug or args.trace:
        # Show the plots if in debug mode
        plt.show()


if __name__ == "__main__":
    main()
