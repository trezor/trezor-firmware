import sys
from pathlib import Path

import matplotlib.pyplot as plt
from InquirerPy import inquirer
from InquirerPy.base import Choice
from utils import load_measured_data

default_dataset_dir = Path("../single_capture_test_results")

battery_thermal_limit = 45.0  # Celsius
case_thermal_limit = 41.0  # Celsius


def select_waveforms(dataset_directory=default_dataset_dir):
    """
    Select waveforms from a given dataset directory.

    Args:
        dataset_directory (Path): The directory containing the dataset.

    Returns:
        list: A list of selected waveforms.
    """

    if not dataset_directory.exists():
        print(f"Dataset directory {dataset_directory} does not exist.")
        return []

    # glob all .csv files in the directory
    all_csv_files = list(dataset_directory.glob("*.csv"))
    if not all_csv_files:
        print(f"No CSV files found in {dataset_directory}.")
        return []

    external_temp_files = list(dataset_directory.glob("external_temp.*.csv"))

    # Filter out external temperature files
    waveform_files = [f for f in all_csv_files if f not in external_temp_files]

    choices = []
    for waveform_file in waveform_files:
        time_id = waveform_file.stem.split(".")[1]

        ch = Choice(
            name=f"{waveform_file.name}",
            value={"waveform": waveform_file, "external_temp": None},
        )

        for temp_file in external_temp_files:
            if time_id in temp_file.stem:
                ch.name += " (ext. temp available)"
                ch.value["external_temp"] = temp_file
                break

        choices.append(ch)

    try:
        selected = inquirer.fuzzy(
            message="Select one or more waveforms:",
            choices=choices,
            multiselect=True,
            instruction="(Use <tab> to select, <enter> to confirm)",
        ).execute()

    except KeyboardInterrupt:
        print("Selection cancelled by user.")
        sys.exit(0)

    except Exception as e:
        print(f"An error occurred during selection: {e}")
        sys.exit(1)

    return selected


def colored_region_plot(axis, time_vector, data_vector, mask, color="red", alpha=0.5):

    start = None
    in_region = False
    for i, val in enumerate(mask):
        if val and not in_region:
            start = i
            in_region = True
        elif not val and in_region:
            axis.plot(
                time_vector[start : i - 1],
                data_vector[start : i - 1],
                color=color,
                alpha=alpha,
            )
            in_region = False

    if in_region:
        axis.plot(
            time_vector[start : (i - 1)],
            data_vector[start : i - 1],
            color=color,
            alpha=alpha,
        )


def colored_region_box(axis, time_vector, mask, color="orange", alpha=0.5):

    start = None
    in_region = False
    for i, val in enumerate(mask):
        if val and not in_region:
            start = i
            in_region = True
        elif not val and in_region:
            axis.axvspan(
                time_vector[start], time_vector[i - 1], color=color, alpha=alpha
            )
            in_region = False

    if in_region:
        axis.axvspan(time_vector[start], time_vector[-1], color=color, alpha=alpha)


def sec_to_min(time_vector):
    return (time_vector - time_vector[0]) / 60.0


def plot_temperature_profile(waveform_name, profile_data):

    fig, ax = plt.subplots(2)
    fig.canvas.manager.set_window_title(waveform_name)

    ax[0].plot(
        sec_to_min(profile_data.time),
        profile_data.battery_temp,
        color="green",
        label="battery temeperature",
    )
    ax[0].axhline(y=battery_thermal_limit, color="green", linestyle="--")

    ax[0].plot(
        sec_to_min(profile_data.time),
        profile_data.pmic_die_temp,
        color="orange",
        label="pmic die temperature",
    )

    colored_region_plot(
        ax[0],
        sec_to_min(profile_data.time),
        profile_data.battery_temp,
        profile_data.battery_temp > battery_thermal_limit,
        color="red",
        alpha=1,
    )

    if profile_data.ext_temp is not None:
        ax[0].plot(
            sec_to_min(profile_data.ext_temp_time),
            profile_data.ext_temp,
            color="blue",
            label="case temperature",
            linestyle="--",
        )
        ax[0].axhline(y=case_thermal_limit, color="blue", linestyle="--")

        colored_region_plot(
            ax[0],
            sec_to_min(profile_data.ext_temp_time),
            profile_data.ext_temp,
            profile_data.ext_temp > case_thermal_limit,
            color="red",
            alpha=1,
        )

    ax[0].set_xlabel("Time (min)")
    ax[0].set_ylabel("Temperature (C)")
    ax[0].set_title("Temperature Profile: " + waveform_name)
    ax[0].set_xlim(
        left=sec_to_min(profile_data.time)[0], right=sec_to_min(profile_data.time)[-1]
    )

    ax[0].legend()
    ax[0].grid(True)

    def min_to_hr(x):
        return x / 60.0

    def hr_to_min(x):
        return x * 60.0

    secax = ax[0].secondary_xaxis("top", functions=(min_to_hr, hr_to_min))
    secax.set_xlabel("Time (hours)")

    # Change background color according to charging state
    usb_charging_mask = (profile_data.usb == "USB_connected") & (
        abs(profile_data.battery_current) > 0
    )
    wlc_charging_mask = (
        (profile_data.wlc == "WLC_connected")
        & ~usb_charging_mask
        & (abs(profile_data.battery_current) > 0)
    )
    colored_region_box(
        ax[0], sec_to_min(profile_data.time), usb_charging_mask, color="blue", alpha=0.2
    )
    colored_region_box(
        ax[0],
        sec_to_min(profile_data.time),
        wlc_charging_mask,
        color="green",
        alpha=0.2,
    )

    ax[1].plot(
        sec_to_min(profile_data.time),
        profile_data.battery_current,
        color="purple",
        label="battery current",
    )
    ax[1].set_xlabel("Time (min)")
    ax[1].set_ylabel("Current (mA)")
    ax[1].set_xlim(
        left=sec_to_min(profile_data.time)[0], right=sec_to_min(profile_data.time)[-1]
    )
    ax[1].grid(True)
    ax[1].legend()

    colored_region_box(
        ax[1], sec_to_min(profile_data.time), usb_charging_mask, color="blue", alpha=0.2
    )
    colored_region_box(
        ax[1],
        sec_to_min(profile_data.time),
        wlc_charging_mask,
        color="green",
        alpha=0.2,
    )


def main():

    selected_waveforms = select_waveforms()

    for waveform in selected_waveforms:

        # Load data from files
        profile_data = load_measured_data(
            data_file_path=waveform["waveform"],
            extern_temp_file_path=waveform["external_temp"],
        )

        plot_temperature_profile(waveform["waveform"].name, profile_data)

    # Plot graphs
    plt.show()


if __name__ == "__main__":
    main()
