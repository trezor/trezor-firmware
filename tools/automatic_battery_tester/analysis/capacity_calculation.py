import sys
from pathlib import Path
from InquirerPy import inquirer
from scipy.interpolate import make_interp_spline
import numpy as np
import matplotlib.pyplot as plt

# Create output directory next to this script
output_dir = Path(__file__).parent / "capacity_graphs"
output_dir.mkdir(exist_ok=True)

invalid_files = []

from utils import (
    load_measured_data,
)  # Assumes it returns object with .time, .battery_current, .battery_soc

default_dataset_dir = Path("../test_results")


def list_csv_files():
    return list(default_dataset_dir.glob("**/*.csv"))


def extract_file_info(file):
    parts = file.stem.split(".")
    if len(parts) < 5:
        return None
    return {
        "battery": parts[0],
        "timestamp": parts[1],
        "mode": parts[2],
        "phase": parts[3],
        "temp": parts[4],
        "path": file,
    }


def collect_files_by_temp():
    files = list_csv_files()
    parsed = [extract_file_info(f) for f in files]

    filtered = []
    for p in parsed:
        if not p:
            continue
        mode = p.get("mode")
        phase = p.get("phase")

        if phase == "charging" and mode in {"linear", "switching", "random_wonder"}:
            filtered.append(p)
        elif phase == "discharging" and mode == "linear":
            filtered.append(p)

    temp_groups = {}
    for p in filtered:
        temp_groups.setdefault(p["temp"], []).append(p)

    return temp_groups


def select_multiple_temperatures(temp_groups):
    choices = []
    for temp, files in temp_groups.items():
        batteries = set(f["battery"] for f in files)
        charging = sum(1 for f in files if f["phase"] == "charging")
        discharging = sum(1 for f in files if f["phase"] == "discharging")
        label = f"{temp}°C  | 🔋 {len(batteries)} batts, ⚡ {charging} charge, 🔻 {discharging} discharge"
        choices.append({"name": label, "value": temp})

    selected = inquirer.checkbox(
        message="Select temperatures to compare (for mean ± std plot):",
        choices=choices,
    ).execute()

    return selected


def select_temperature(temp_groups):
    choices = []
    for temp, files in temp_groups.items():
        batteries = set(f["battery"] for f in files)
        charging = sum(1 for f in files if f["phase"] == "charging")
        discharging = sum(1 for f in files if f["phase"] == "discharging")
        label = f"{temp}°C  | 🔋 {len(batteries)} batts, ⚡ {charging} charge, 🔻 {discharging} discharge"
        choices.append(label)

    temp_choice = inquirer.select(
        message="Select a temperature group:",
        choices=choices,
    ).execute()

    selected_temp = temp_choice.split("°")[0]
    return selected_temp, temp_groups[selected_temp]


def validate_soc_direction(profile, phase, filename):
    soc = profile.battery_soc
    if len(soc) < 2:
        reason = f"SoC array too short (length={len(soc)})"
        return False, reason

    start, end = soc[0], soc[-1]

    if phase == "charging":
        valid = np.isclose(start, 0, atol=3) and np.isclose(end, 100, atol=3)
        if not valid:
            reason = f"SoC start={start:.2f}, end={end:.2f}"
    elif phase == "discharging":
        valid = np.isclose(start, 100, atol=3) and (end <= 1.0)
        if not valid:
            reason = f"SoC start={start:.2f}, end={end:.2f}"
    else:
        valid = False
        reason = "Unknown phase"

    if not valid:
        return False, reason
    return True, None


from scipy.ndimage import median_filter, uniform_filter1d


def coulomb_counter(time, ibat):
    """
    ibat in mA, time in seconds
    Calculate total charge in mAh using trapezoidal summation
    """
    curr_acc = 0
    for i in range(1, len(time)):
        # Average current between points
        avg_current = abs((ibat[i - 1] + ibat[i]) / 2)
        dt = time[i] - time[i - 1]  # seconds
        curr_acc += avg_current * dt
    return curr_acc / 3600  # convert mAs to mAh


def integrate_capacity(profile, phase, median_window=10, ma_window=15):
    time_s = profile.time  # seconds
    current_mA = profile.battery_current
    soc = profile.battery_soc

    # --- Median filter to remove sharp noise/outliers ---
    current_filtered = median_filter(current_mA, size=median_window, mode="nearest")

    # --- Strong moving average to smooth general curve ---
    current_smoothed = uniform_filter1d(
        current_filtered, size=ma_window, mode="nearest"
    )

    # --- Determine cutoff based on SoC or current ~ 0 ---
    cutoff_idx = None
    if phase == "charging":
        indices = np.where(soc >= 99)[0]
        if len(indices) > 0:
            cutoff_idx = indices[0]
    elif phase == "discharging":
        indices = np.where(soc <= 1)[0]
        if len(indices) > 0:
            cutoff_idx = indices[0]

    if cutoff_idx is None:
        zero_current_indices = np.where(np.isclose(current_smoothed, 0, atol=0.1))[0]
        if len(zero_current_indices) > 0:
            cutoff_idx = zero_current_indices[0]

    if cutoff_idx is not None:
        time_s = time_s[: cutoff_idx + 1]
        current_smoothed = current_smoothed[: cutoff_idx + 1]

    # capacity_mAs = np.trapz(current_smoothed, time_s)
    # capacity_mAh = capacity_mAs / 3600.0

    capacity_mAh = coulomb_counter(time_s, current_smoothed)

    return abs(capacity_mAh)


def print_coulombic_efficiency_per_battery(capacities_by_battery):
    print("\n--- Coulombic Efficiency per Battery, Mode, and Cycle ---")
    for battery, mode_dict in capacities_by_battery.items():
        for mode, caps in mode_dict.items():
            charging_caps = caps.get("charging", [])
            discharging_caps = caps.get("discharging", [])
            min_len = min(len(charging_caps), len(discharging_caps))
            if min_len == 0:
                print(
                    f"Battery: {battery}, Mode: {mode} ⚠️ Insufficient data for CE calculation."
                )
                continue

            ce_values = (
                np.array(discharging_caps[:min_len])
                / np.array(charging_caps[:min_len])
                * 100
            )
            ce_mean = np.mean(ce_values)
            ce_std = np.std(ce_values)

            print(f"\n🔋 Battery: {battery} | Mode: {mode}")
            for cycle_idx, ce in enumerate(ce_values, 1):
                print(f"  Cycle {cycle_idx}: CE = {ce:.4f}%")
            print(f"  → Mean CE: {ce_mean:.4f}% ± {ce_std:.4f}%\n")


def plot_combined_capacity_distribution(
    charging_caps, discharging_caps, temp, capacities_by_battery
):
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MaxNLocator
    from scipy.stats import norm
    from matplotlib.lines import Line2D
    from pathlib import Path

    fig, ax = plt.subplots(2, figsize=(12, 7), sharex=False)
    fig.subplots_adjust(left=0.25, right=0.78, hspace=0.5)  # space for CE and legends
    fig.canvas.manager.set_window_title(f"Capacity Distributions - Temp: {temp}°C")

    normal_color = "black"

    battery_ids = list(capacities_by_battery.keys())
    cmap = plt.get_cmap("tab20")
    battery_colors = {bat: cmap(i % 20) for i, bat in enumerate(battery_ids)}

    def get_padded_xlim(data, padding_ratio=0.03):
        data_min = min(data)
        data_max = max(data)
        padding = (data_max - data_min) * padding_ratio
        return data_min - padding, data_max + padding

    # --- Charging Plot ---
    ax0 = ax[0]
    charging_data = []
    for bat in battery_ids:
        merged = []
        for mode_caps in capacities_by_battery[bat].values():
            merged.extend(mode_caps.get("charging", []))
        charging_data.append(merged)

    if any(len(d) > 0 for d in charging_data):
        all_charging = np.concatenate([np.array(d) for d in charging_data if d])
        x_c_min, x_c_max = get_padded_xlim(all_charging)
        bins_c = np.linspace(x_c_min, x_c_max, 16)

        counts_c, bins_c_vals, patches_c = ax0.hist(
            charging_data,
            bins=bins_c,
            stacked=True,
            color=[battery_colors[bat] for bat in battery_ids],
            edgecolor="black",
            alpha=0.7,
        )

        print("\n[DEBUG] Charging Histogram:")
        for i, bat in enumerate(battery_ids):
            print(f"  Battery '{bat}': counts={counts_c[i]}, sum={counts_c[i].sum()}")
        print(f"  Combined counts sum: {counts_c.sum()}")
        print(f"  Bins: {bins_c}")

        mean_c = np.mean(all_charging)
        std_c = np.std(all_charging)
        x_c = np.linspace(x_c_min, x_c_max, 200)
        pdf_c = norm.pdf(x_c, mean_c, std_c)

        ax0.plot(x_c, pdf_c, color=normal_color, linewidth=2)
        ax0.set_xlim(x_c_min, x_c_max)
        ax0.set_ylim(0, None)
        ax0.xaxis.set_major_locator(MaxNLocator(integer=True))
    else:
        ax0.text(0.5, 0.5, "No charging data", ha="center", va="center")

    ax0.set_title(f"Charging Capacity Distribution @ {temp}°C")
    ax0.set_ylabel("Density")
    ax0.grid(True)

    # --- Discharging Plot ---
    ax1 = ax[1]

    valid_discharge = []
    for bat in battery_ids:
        merged = []
        for mode_caps in capacities_by_battery[bat].values():
            merged.extend(mode_caps.get("discharging", []))
        if merged:
            valid_discharge.append((bat, merged))

    discharging_data = [data for _, data in valid_discharge]
    discharging_ids = [bat for bat, _ in valid_discharge]

    if discharging_data:
        all_discharging = np.concatenate([np.array(d) for d in discharging_data])
        x_d_min, x_d_max = get_padded_xlim(all_discharging)
        bins_d = np.linspace(x_d_min, x_d_max, 16)

        hist_data = ax1.hist(
            discharging_data,
            bins=bins_d,
            stacked=True,
            color=[battery_colors[bat] for bat in discharging_ids],
            edgecolor="black",
            alpha=0.8,
            label=discharging_ids,
        )

        print("\n[DEBUG] Discharging Histogram:")
        for i, (bat, counts) in enumerate(zip(discharging_ids, hist_data[0])):
            print(f"  Battery '{bat}': counts={counts}, sum={np.sum(counts):.1f}")

        print(f"  Combined counts sum: {np.sum(hist_data[0]):.1f}")
        print(f"  Bins: {bins_d}")

        mean_d = np.mean(all_discharging)
        std_d = np.std(all_discharging)
        x_d = np.linspace(x_d_min, x_d_max, 200)
        ax1.plot(
            x_d,
            norm.pdf(x_d, mean_d, std_d)
            * len(all_discharging)
            * (bins_d[1] - bins_d[0]),
            color=normal_color,
            linewidth=2,
            label=f"Normal Fit\nμ={mean_d:.2f}, σ={std_d:.2f}",
        )

        ax1.set_xlim(x_d_min, x_d_max)
        ax1.xaxis.set_major_locator(MaxNLocator(integer=True))
    else:
        ax1.text(0.5, 0.5, "No discharging data", ha="center", va="center")

    ax1.set_title("Discharging Capacity Distribution")
    ax1.set_xlabel("Capacity (mAh)")
    ax1.set_ylabel("Count")
    ax1.grid(True)
    ax1.legend(loc="upper right")

    """
    # Legends for batteries outside right
    battery_patches = [
        mpatches.Patch(color=battery_colors[bat], label=bat) for bat in battery_ids
    ]
    """
    # Charging legends
    mean_c_text = (
        f"Normal Fit\nμ={mean_c:.2f}, σ={std_c:.2f}"
        if any(len(d) > 0 for d in charging_data)
        else "No data"
    )
    normal_line = Line2D([0], [0], color=normal_color, linewidth=2, label=mean_c_text)
    leg1 = ax0.legend(
        handles=[normal_line], loc="upper right", fontsize=9, frameon=True
    )
    """
    leg2 = ax0.legend(
        handles=battery_patches,
        title="Batteries (Charging)",
        loc="upper left",
        bbox_to_anchor=(1.05, 1.0),
        fontsize=8,
    )
    """
    ax0.add_artist(leg1)

    # Discharging legends
    mean_d_text = (
        f"Normal Fit\nμ={mean_d:.2f}, σ={std_d:.2f}"
        if any(len(d) > 0 for d in discharging_data)
        else "No data"
    )
    normal_line_d = Line2D([0], [0], color=normal_color, linewidth=2, label=mean_d_text)
    leg3 = ax1.legend(
        handles=[normal_line_d], loc="upper right", fontsize=9, frameon=True
    )
    """
    leg4 = ax1.legend(
        handles=battery_patches,
        title="Batteries (Discharging)",
        loc="upper left",
        bbox_to_anchor=(1.05, 1.0),
        fontsize=8,
    )
    """
    ax1.add_artist(leg3)

    print("\n--- DEBUG: Modes and Phases Detected in capacities_by_battery ---")
    for battery, modes in capacities_by_battery.items():
        print(f"Battery: {battery}")
        for mode, phase_dict in modes.items():
            print(f"  Mode: {mode}")
            for phase, cap_list in phase_dict.items():
                print(f"    Phase: {phase} → {len(cap_list)} entries")

    # --- Coulombic Efficiency Summary Box (Mode → CE1, CE2...) ---
    ce_ax = fig.add_axes([0.0325, 0.20, 0.18, 0.7])
    ce_ax.axis("off")

    y_pos = 1.0
    line_height = 0.06
    text_size = 8.5

    ce_ax.text(
        -0.05,
        y_pos,
        "Coulombic Efficiency Summary",
        fontsize=10,
        weight="bold",
        va="top",
    )
    y_pos -= line_height * 1.2

    for battery in battery_ids:
        caps = capacities_by_battery[battery]
        color = battery_colors[battery]

        all_ce_values = []
        mode_ce_lines = []

        for mode in caps:
            phase_data = caps[mode]
            charging = phase_data.get("charging", [])
            discharging = phase_data.get("discharging", [])
            min_len = min(len(charging), len(discharging))

            if min_len == 0:
                print(
                    f"⚠️ Skipping CE for battery '{battery}', mode '{mode}' → charging: {len(charging)}, discharging: {len(discharging)}"
                )
                continue  # skip this mode due to incomplete data

            charging_arr = np.array(charging[:min_len])
            discharging_arr = np.array(discharging[:min_len])
            ce_values = discharging_arr / charging_arr * 100
            all_ce_values.extend(ce_values)

            ce_strs = ", ".join(f"{ce:.2f}%" for ce in ce_values)
            mode_ce_lines.append(f"  {mode}: {ce_strs}")

        if not all_ce_values:
            ce_ax.text(
                0,
                y_pos,
                f"{battery}: ⚠️ Insufficient data",
                color="red",
                fontsize=text_size,
                va="top",
            )
            y_pos -= line_height
            continue

        mean_ce = np.mean(all_ce_values)
        ce_ax.text(
            0,
            y_pos,
            f"{battery} → {mean_ce:.2f}%",
            color=color,
            fontsize=text_size + 0.5,
            weight="bold",
            va="top",
        )
        y_pos -= line_height * 1.1

        for line in mode_ce_lines:
            ce_ax.text(0.02, y_pos, line, color=color, fontsize=text_size, va="top")
            y_pos -= line_height * 0.9

        y_pos -= line_height * 0.3  # extra spacing

    # Export and show
    export_dir = Path("capacity_graphs")
    export_dir.mkdir(exist_ok=True)
    filename = f"Capacity_Distribution_{temp}C.png"
    export_path = export_dir / filename
    plt.savefig(export_path, bbox_inches="tight")
    print(f"✅ Exported graph to {export_path.resolve()}")

    plt.show()


def plot_mean_capacity_across_temperatures(temp_list, temp_groups):
    def gather_stats(phase):
        mean_caps = []
        std_caps = []
        temps_numeric = []

        for temp in temp_list:
            files = temp_groups[temp]
            grouped = {}
            for f in files:
                grouped.setdefault(f["battery"], []).append(f)

            all_caps = []

            for battery, entries in grouped.items():
                for e in entries:
                    if e["phase"] != phase:
                        continue
                    try:
                        profile = load_measured_data(data_file_paths=[e["path"]])
                        valid, reason = validate_soc_direction(
                            profile, e["phase"], e["path"].name
                        )
                        if not valid:
                            continue
                        capacity = integrate_capacity(profile, e["phase"])
                        all_caps.append(capacity)
                    except Exception as ex:
                        print(f"Error in {e['path'].name}: {ex}")
                        continue

            if all_caps:
                mean_caps.append(np.mean(all_caps))
                std_caps.append(np.std(all_caps))
                temps_numeric.append(float(temp))

        return temps_numeric, mean_caps, std_caps

    def plot_capacity(temps_numeric, mean_caps, std_caps, phase):
        if not mean_caps:
            print(f"⚠️ No data found to plot for {phase} phase.")
            return

        # Sort by temperature
        sorted_indices = np.argsort(temps_numeric)
        temps_sorted = np.array(temps_numeric)[sorted_indices]
        mean_sorted = np.array(mean_caps)[sorted_indices]
        std_sorted = np.array(std_caps)[sorted_indices]

        fig, ax = plt.subplots(figsize=(10, 6))

        ax.errorbar(
            temps_sorted,
            mean_sorted,
            yerr=std_sorted,
            fmt="o",
            capsize=8,
            elinewidth=2,
            marker="s",
            color="blue",
        )

        ax.set_title(f"{phase.capitalize()} Capacity vs Temperature (Mean ± Std Dev)")
        ax.set_xlabel("Temperature (°C)")
        ax.set_ylabel(f"{phase.capitalize()} Capacity (mAh)")
        ax.grid(True)

        ax.set_xlim(0, 50)
        ax.set_xticks(np.arange(0, 51, 5))

        # Fade ticks not corresponding to data points
        tick_labels = ax.get_xticklabels()
        for label in tick_labels:
            try:
                tick_val = float(label.get_text())
                if tick_val not in temps_sorted:
                    label.set_alpha(0.3)
                    label.set_color("gray")
            except ValueError:
                pass

        # Zoom out Y axis with padding of 3 * error bar length
        upper_bounds = mean_sorted + 3 * std_sorted
        lower_bounds = mean_sorted - 3 * std_sorted

        y_min = max(0, np.min(lower_bounds))
        y_max = np.max(upper_bounds)
        y_range = y_max - y_min
        y_min -= 0.05 * y_range
        y_max += 0.05 * y_range
        ax.set_ylim(y_min, y_max)

        if len(temps_sorted) >= 2:
            # Main trendline
            z = np.polyfit(temps_sorted, mean_sorted, 1)
            p = np.poly1d(z)
            ax.plot(temps_sorted, p(temps_sorted), color="red", label="Trendline")

            # Upper bound trendline (mean + std)
            z_upper = np.polyfit(temps_sorted, mean_sorted + std_sorted, 1)
            p_upper = np.poly1d(z_upper)
            ax.plot(temps_sorted, p_upper(temps_sorted), "r--", label="Upper bound")

            # Lower bound trendline (mean - std)
            z_lower = np.polyfit(temps_sorted, mean_sorted - std_sorted, 1)
            p_lower = np.poly1d(z_lower)
            ax.plot(temps_sorted, p_lower(temps_sorted), "r--", label="Lower bound")

            ax.legend()
        else:
            print(f"⚠️ Not enough data points to fit trendlines for {phase} phase.")

        plt.tight_layout()

        export_path = output_dir / f"Mean_Capacity_vs_Temperature_{phase}.png"
        plt.savefig(export_path)
        print(f"✅ Saved plot to {export_path.resolve()}")
        plt.show(block=False)

    # Plot discharging
    temps_discharging, mean_discharging, std_discharging = gather_stats("discharging")
    plot_capacity(temps_discharging, mean_discharging, std_discharging, "discharging")

    # Plot charging
    temps_charging, mean_charging, std_charging = gather_stats("charging")
    plot_capacity(temps_charging, mean_charging, std_charging, "charging")
    input("Press Enter to exit and close plot...")


def main():

    invalid_files = []

    if not default_dataset_dir.exists():
        print(f"Error: directory {default_dataset_dir} not found.")
        sys.exit(1)

    temp_groups = collect_files_by_temp()
    if not temp_groups:
        print("No valid files found.")
        sys.exit(1)

    # New choice tree for two analysis options
    action = inquirer.select(
        message="Choose analysis mode:",
        choices=[
            "🔹 Plot capacity distributions for a single temperature",
            "🔸 Compare mean discharging capacity across temperatures",
        ],
    ).execute()

    if action == "🔹 Plot capacity distributions for a single temperature":
        selected_temp, selected_files = select_temperature(temp_groups)

        batteries = set(p["battery"] for p in selected_files)
        print(
            f"\n🔍 {len(batteries)} unique batteries with temperature {selected_temp}°C\n"
        )

        battery_to_files = {}
        for f in selected_files:
            battery_to_files.setdefault(f["battery"], []).append(f)

        capacities_by_battery = {}

        for battery_id, entries in sorted(battery_to_files.items()):
            capacities_by_battery[battery_id] = {}

            for phase in ["charging", "discharging"]:
                phase_entries = [e for e in entries if e["phase"] == phase]
                for entry in phase_entries:
                    print(
                        f"📂 Processing battery: {battery_id}, phase: {phase}, file: {entry['path'].name}"
                    )
                    try:
                        profile = load_measured_data(data_file_paths=[entry["path"]])
                        valid, reason = validate_soc_direction(
                            profile, phase, entry["path"].name
                        )
                        if not valid:
                            invalid_files.append((entry["path"].name, reason))
                            continue

                        capacity = integrate_capacity(profile, phase)
                        filename_parts = entry["path"].name.split(".")
                        mode = (
                            filename_parts[2] if len(filename_parts) > 2 else "unknown"
                        )

                        if mode not in capacities_by_battery[battery_id]:
                            capacities_by_battery[battery_id][mode] = {
                                "charging": [],
                                "discharging": [],
                            }

                        capacities_by_battery[battery_id][mode][phase].append(capacity)
                        print(
                            f"✅ Estimated capacity: {capacity:.2f} mAh (Mode: {mode})\n"
                        )
                    except Exception as e:
                        print(f"❌ Error processing file: {entry['path'].name}: {e}\n")

        if capacities_by_battery:
            all_charging = []
            all_discharging = []
            for battery_modes in capacities_by_battery.values():
                for mode_data in battery_modes.values():
                    all_charging.extend(mode_data.get("charging", []))
                    all_discharging.extend(mode_data.get("discharging", []))

            plot_combined_capacity_distribution(
                all_charging, all_discharging, selected_temp, capacities_by_battery
            )
        else:
            print("⚠️ No valid capacity data to plot.")

    elif action == "🔸 Compare mean discharging capacity across temperatures":
        selected_temps = select_multiple_temperatures(temp_groups)
        if not selected_temps:
            print("❌ No temperatures selected.")
            return
        plot_mean_capacity_across_temperatures(selected_temps, temp_groups)

    if invalid_files:
        print("\n⚠️ Skipped files due to SoC validation failure:")
        for fname, reason in invalid_files:
            print(f"  - {fname}: {reason}")


if __name__ == "__main__":
    main()
