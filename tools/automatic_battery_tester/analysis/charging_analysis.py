import sys
from pathlib import Path
from collections import defaultdict
import matplotlib.pyplot as plt
from InquirerPy import inquirer
from InquirerPy.base import Choice
from utils import load_measured_data

default_dataset_dir = Path("../test_results")
# default_dataset_dir = Path("../single_capture_test_results")

battery_thermal_limit = 45.0  # Celsius
case_thermal_limit = 41.0  # Celsius


def select_mode():
    return inquirer.select(
        message="Select mode:",
        choices=[
            "Select individual waveform files",
            "Select groups by timestamp (combine batteries in one graph)",
        ],
    ).execute()


def select_waveforms(dataset_directory=default_dataset_dir):
    """
    Original waveform selection unchanged.
    """
    if not dataset_directory.exists():
        print(f"Dataset directory {dataset_directory} does not exist.")
        return []

    all_csv_files = list(dataset_directory.glob("*.csv"))
    if not all_csv_files:
        print(f"No CSV files found in {dataset_directory}.")
        return []

    external_temp_files = list(dataset_directory.glob("external_temp.*.csv"))
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


def select_waveform_groups_by_timestamp(dataset_directory=default_dataset_dir):
    """
    Select groups by timestamp, show battery count and mode per group.
    Only filter by battery phase (no mode selection).
    """
    if not dataset_directory.exists():
        print(f"Dataset directory {dataset_directory} does not exist.")
        return []

    all_csv_files = list(dataset_directory.glob("*.csv"))
    if not all_csv_files:
        print(f"No CSV files found in {dataset_directory}.")
        return []

    # Step 1: Build file_groups by timestamp
    file_groups = {}
    for file in all_csv_files:
        parts = file.stem.split(".")
        if len(parts) < 5:
            continue  # Malformed filename

        battery_id = parts[0]
        time_id = parts[1]
        mode = parts[2]
        phase = parts[3]
        temp = f"{float(parts[4]):.2f}"  # Normalize to '30.00' format

        if time_id not in file_groups:
            file_groups[time_id] = {
                "files": [],
                "external_temp": None,
                "battery_ids": set(),
                "modes": set(),
                "temp": set(),
            }

        if "external_temp" in file.name:
            file_groups[time_id]["external_temp"] = file
        else:
            file_groups[time_id]["files"].append(
                {
                    "battery_id": battery_id,
                    "file": file,
                    "mode": mode,
                    "phase": phase,
                    "temp": temp,
                }
            )
            file_groups[time_id]["battery_ids"].add(battery_id)
            file_groups[time_id]["modes"].add(mode)
            file_groups[time_id]["temp"].add(temp)

    # Sort timestamps descending (most recent first)
    sorted_time_ids = sorted(file_groups.keys(), reverse=True)

    timestamp_choices = []
    for time_id in sorted_time_ids:
        group = file_groups[time_id]
        num_batteries = len(group["battery_ids"])
        mode_str = next(iter(group["modes"])) if len(group["modes"]) == 1 else "Mixed"
        count = len(group["files"])

        # ✅ FIX: compute temperature label properly
        print(f"Temps in group {time_id}: {group['temp']}")
        temp_values = group["temp"]
        if len(temp_values) == 1:
            temp_str = next(iter(temp_values))
        else:
            temp_str = "Mixed"

        # ✅ Build the label string once
        label = f"{time_id} ({num_batteries} batteries, mode: {mode_str}, {count} test{'s' if count != 1 else ''} (Temp: {temp_str}))"

        if group["external_temp"]:
            label += " (ext. temp available)"

        # ✅ Append the final choice
        timestamp_choices.append(
            Choice(
                name=label,
                value={
                    "time_id": time_id,
                    "files": group["files"],
                    "external_temp": group["external_temp"],
                },
            )
        )

    try:
        selected_groups = inquirer.fuzzy(
            message="Select one or more timestamp groups:",
            choices=timestamp_choices,
            multiselect=True,
            instruction="(Use <tab> to select, <enter> to confirm)",
        ).execute()

    except KeyboardInterrupt:
        print("Selection cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"An error occurred during selection: {e}")
        sys.exit(1)

    # Step 3: Ask for battery phase
    phase = inquirer.select(
        message="Select battery phase:",
        choices=[
            "All",
            "charging",
            "charged_relaxing",
            "discharging",
            "discharging_relaxing",
        ],
    ).execute()

    # Step 4: Filter selected groups by battery phase only
    battery_file_groups = defaultdict(lambda: defaultdict(list))

    for group in selected_groups:
        for entry in group["files"]:
            if phase == "All" or entry["phase"] == phase:
                battery_file_groups[group["time_id"]][entry["battery_id"]].append(
                    entry["file"]
                )

    filtered_results = []

    PHASE_ORDER = {
        "not_started": 0,
        "charging": 1,
        "charged_relaxing": 2,
        "random_wonder": 3,
        "discharging": 4,
        "discharged_relaxing": 5,
        "done": 6,
    }

    for time_id, battery_dict in battery_file_groups.items():
        files_dict = {}
        for battery_id, files in battery_dict.items():
            sorted_files = sorted(
                files, key=lambda f: PHASE_ORDER.get(f.stem.split(".")[3], 999)
            )
            files_dict[battery_id] = sorted_files
        filtered_results.append(
            {
                "time_id": time_id,
                "files": files_dict,
                "external_temp": file_groups[time_id]["external_temp"],
            }
        )

    if not filtered_results:
        print(f"\nNo files found matching phase '{phase}'.")
        sys.exit(1)

    return filtered_results


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
    """
    Your original single waveform plot unchanged.
    """
    fig, ax = plt.subplots(2)
    fig.canvas.manager.set_window_title(waveform_name)

    ax[0].plot(
        sec_to_min(profile_data.time),
        profile_data.battery_voltage,
        color="blue",
        label="Battery Voltage (V)",
    )
    ax[0].set_ylabel("Battery Voltage (V)")
    v_min = profile_data.battery_voltage.min()
    v_max = profile_data.battery_voltage.max()
    ax[0].set_ylim(
        bottom=v_min - 0.1 * (v_max - v_min), top=v_max + 0.1 * (v_max - v_min)
    )
    ax[0].axhline(y=battery_thermal_limit, color="green", linestyle="--")

    ax0_sec = ax[0].twinx()
    ax0_sec.plot(
        sec_to_min(profile_data.time),
        profile_data.battery_current,
        color="purple",
        linestyle="--",
        label="Battery Current (mA)",
    )
    ax0_sec.set_ylabel("Current (mA)")

    colored_region_plot(
        ax[0],
        sec_to_min(profile_data.time),
        profile_data.battery_temp,
        profile_data.battery_temp > battery_thermal_limit,
        color="red",
        alpha=1,
    )

    """
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
    """

    ax[0].set_xlabel("Time (min)")
    ax[0].set_title("Temperature Profile: " + waveform_name)
    ax[0].set_xlim(
        left=sec_to_min(profile_data.time)[0], right=sec_to_min(profile_data.time)[-1]
    )

    ax[0].legend()
    ax[0].grid(True)

    lines, labels = ax[0].get_legend_handles_labels()
    lines2, labels2 = ax0_sec.get_legend_handles_labels()
    ax[0].legend(lines + lines2, labels + labels2)

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
        profile_data.battery_soc,
        color="orange",
        label="State of Charge (%)",
    )
    ax[1].set_xlabel("Time (min)")
    ax[1].set_ylabel("State of Charge (%)")

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


def plot_group_by_timestamp(time_id, files_dict, ext_temp_file):
    import numpy as np
    import matplotlib.pyplot as plt
    import matplotlib

    fig, ax = plt.subplots(2, figsize=(12, 7), sharex=True)
    fig.subplots_adjust(right=0.75)

    # Extract test mode from first file of first battery
    first_battery = next(iter(files_dict))
    first_file = files_dict[first_battery][0]
    mode = first_file.stem.split(".")[2]  # mode is third element
    temperature_str = first_file.stem.split(".")[4]  # temperature is 5th element

    fig.canvas.manager.set_window_title(
        f"Group: {time_id} - {len(files_dict)} batteries - Mode: {mode} - Temp: {temperature_str}°C"
    )

    # Use new colormap API to avoid deprecation warning
    voltage_colors = matplotlib.colormaps["tab10"]
    current_colors = matplotlib.colormaps["Set2"]  # Different colormap for clarity
    temp_colors = matplotlib.colormaps["coolwarm"]

    battery_ids = sorted(files_dict.keys())

    all_voltages = []
    all_currents = []
    all_socs = []
    all_times = []
    all_temps = []

    temp_errors = []

    ax0_sec = ax[0].twinx()
    ax1_sec = ax[1].twinx()

    for i, battery_id in enumerate(battery_ids):
        battery_files = files_dict[battery_id]
        print(f"\n🔍 Battery ID: {battery_id}")
        print("Files to be concatenated:")
        for f in battery_files:
            print(f" - {f.name}")

        profile_data = load_measured_data(
            data_file_paths=battery_files,
            extern_temp_file_path=ext_temp_file,
        )

        temp = profile_data.battery_temp
        temp_range = temp.max() - temp.min()
        all_temps.append(temp)

        if temp_range > 2.0:
            temp_errors.append(
                f"❌ ERROR: Battery {battery_id} temp swayed by {temp_range:.2f}°C during test"
            )

        t = sec_to_min(profile_data.time)
        if len(t) <= 1:
            print(
                f"⚠️ Skipping {battery_files[0].name} — not enough time data (len={len(t)})"
            )
            continue

        all_times.append(t)
        all_voltages.append(profile_data.battery_voltage)
        all_currents.append(profile_data.battery_current)
        all_socs.append(profile_data.battery_soc)

        ax[0].plot(
            t,
            profile_data.battery_voltage,
            label=f"{battery_id} Voltage",
            color=voltage_colors(i),
            linewidth=2.0,
        )

        ax0_sec.plot(
            t,
            profile_data.battery_current,
            label=f"{battery_id} Current",
            linestyle="--",
            color=current_colors(i % 8),
            linewidth=1.5,
            alpha=0.8,
        )

        usb_charging_mask = (profile_data.usb == "USB_connected") & (
            abs(profile_data.battery_current) > 0
        )
        wlc_charging_mask = (
            (profile_data.wlc == "WLC_connected")
            & ~usb_charging_mask
            & (abs(profile_data.battery_current) > 0)
        )

        colored_region_box(ax[0], t, usb_charging_mask, color="blue", alpha=0.2)
        colored_region_box(ax[0], t, wlc_charging_mask, color="green", alpha=0.2)

        ax[1].plot(
            t,
            profile_data.battery_soc,
            label=f"{battery_id} SOC",
            linestyle="-",
            color=voltage_colors(i),
            linewidth=2.0,
        )

        ax1_sec.plot(
            t,
            profile_data.battery_temp,
            label=f"{battery_id} Temp",
            linestyle=":",
            color=temp_colors(i / max(len(battery_ids) - 1, 1)),
            linewidth=1.5,
            alpha=0.8,
        )

        overheat_mask = profile_data.battery_temp > battery_thermal_limit
        colored_region_box(
            ax[1],
            t,
            overheat_mask,
            color=temp_colors(i / max(len(battery_ids) - 1, 1)),
            alpha=0.15,
        )

        colored_region_plot(
            ax[0],
            t,
            profile_data.battery_temp,
            profile_data.battery_temp > battery_thermal_limit,
            color=voltage_colors(i),
            alpha=0.2,
        )

    if not all_times:
        print("No valid data to plot.")
        return

    v_concat = np.concatenate(all_voltages)
    c_concat = np.concatenate(all_currents)
    soc_concat = np.concatenate(all_socs)
    t_concat = np.concatenate(all_times)

    ax[0].set_ylim(
        v_concat.min() - 0.1 * np.ptp(v_concat), v_concat.max() + 0.1 * np.ptp(v_concat)
    )
    ax0_sec.set_ylim(
        c_concat.min() - 0.1 * np.ptp(c_concat), c_concat.max() + 0.1 * np.ptp(c_concat)
    )
    ax[1].set_ylim(
        soc_concat.min() - 0.1 * np.ptp(soc_concat),
        soc_concat.max() + 0.1 * np.ptp(soc_concat),
    )

    ax[0].set_ylabel("Battery Voltage (V)")
    ax0_sec.set_ylabel("Battery Current (mA)")
    ax[1].set_ylabel("State of Charge (%)")
    ax[1].set_xlabel("Time (min)")
    ax1_sec.set_ylabel("Battery Temp (°C)")

    ax[0].set_title(
        f"Voltage/Current Profile Group: {time_id} - Mode: {mode} - Temp: {temperature_str}°C"
    )
    ax[1].set_title("State of Charge Over Time")

    ax[0].grid(True)
    ax[1].grid(True)

    ax[1].set_xlim(left=t_concat.min(), right=t_concat.max())

    ax[0].legend(loc="upper left", bbox_to_anchor=(1.10, 1.25), title="Voltage")
    ax0_sec.legend(loc="upper left", bbox_to_anchor=(1.10, 0.5), title="Current")

    lines_soc, labels_soc = ax[1].get_legend_handles_labels()
    lines_temp, labels_temp = ax1_sec.get_legend_handles_labels()

    ax[1].legend(
        lines_soc + lines_temp,
        labels_soc + labels_temp,
        loc="upper left",
        bbox_to_anchor=(1.10, 0.8),
        title="Temp (°C) and SOC (%)",
    )

    if all_temps:
        temp_concat = np.concatenate(all_temps)
        ax1_sec.set_ylim(
            temp_concat.min() - 0.5 * np.ptp(temp_concat),
            temp_concat.max() + 0.5 * np.ptp(temp_concat),
        )

    # Ensure top plot shows ticks but no labels on x-axis
    ax[0].tick_params(axis="x", labelbottom=False)

    # Bottom plot shows x-axis labels and ticks
    ax[1].tick_params(axis="x", labelbottom=True)

    # Set x limits on bottom plot (shared x-axis)
    ax[1].set_xlim(left=t[0], right=t[-1])

    # Export folder logic
    export_dir = Path("exported_graphs")
    export_dir.mkdir(exist_ok=True)

    output_file = (
        export_dir
        / f"Group: {time_id} - {len(files_dict)} batteries - Mode: {mode} - Temp: {temperature_str}°C.png"
    )
    if not output_file.exists():
        plt.savefig(output_file, bbox_inches="tight")
        print(f"✅ Exported graph to {output_file}")
    else:
        print(f"🟡 Skipped export — file already exists: {output_file}")

    if temp_errors:
        print("\nSummary of temperature threshold errors:")
        for err in temp_errors:
            print(err)


def main():
    mode = select_mode()

    if mode == "Select individual waveform files":
        selected_waveforms = select_waveforms()
        for waveform in selected_waveforms:
            profile_data = load_measured_data(
                data_file_paths=waveform["waveform"],
                extern_temp_file_path=waveform["external_temp"],
            )
            plot_temperature_profile(waveform["waveform"].name, profile_data)

    else:
        selected_groups = select_waveform_groups_by_timestamp()
        for group in selected_groups:
            plot_group_by_timestamp(
                group["time_id"], group["files"], group["external_temp"]
            )
    # ... after plotting and setting labels/legends ...

    plt.show()


if __name__ == "__main__":
    main()
