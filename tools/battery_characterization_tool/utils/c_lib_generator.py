"""
Battery Libraries Generator

Generates battery_data header file based on the provided battery model data.
"""

import os


def generate_battery_data_header(battery_model_data, battery_name, output_path):
    """
    Generate C header file containing battery data lookup tables and parameters

    Parameters:
    - battery_model_data: Dictionary containing the complete battery model data
    - battery_name: String identifier for the battery model
    - output_path: Path to save the header file
    """
    header_guard = f"BATTERY_DATA_{battery_name.upper()}_H"

    # Extract temperature points from the battery model data
    # Get separate temperature arrays for charging and discharging
    temp_keys = list(battery_model_data["ocv_curves"].keys())
    temp_points_dischg = []
    temp_points_chg = []
    for key in temp_keys:
        temp_data = battery_model_data["ocv_curves"][key]
        temp_points_dischg.append(temp_data["bat_temp_dischg"])
        temp_points_chg.append(temp_data["bat_temp_chg"])

    header = [
        "/**",
        f" * Battery Data: {battery_name.upper()}",
        " * Auto-generated from battery characterization data",
        " * Contains lookup tables and parameters for the specific battery model",
        " */",
        "",
        f"#ifndef {header_guard}",
        f"#define {header_guard}",
        "",
        "#include <stdint.h>",
        "",
        "/**",
        " * Battery Specifications:",
        f" * Model: {battery_name.upper()}",
        " * Chemistry: LiFePO4",
        " * Characterized on: TODO - Add date",
        " */",
        "",
        "// Configuration",
        f"#define BATTERY_NUM_TEMP_POINTS {len(temp_keys)}",
        "",
        "// SOC breakpoints for piecewise functions",
        "#define BATTERY_SOC_BREAKPOINT_1 0.25f",
        "#define BATTERY_SOC_BREAKPOINT_2 0.8f",
        "",
        "// Temperature points arrays (in Celsius)",
        "// Discharge temperatures",
        "static const float BATTERY_TEMP_POINTS_DISCHG[BATTERY_NUM_TEMP_POINTS] = {",
    ]

    # Add discharge temperature points
    temp_strings_dischg = [f"    {temp:.2f}f" for temp in temp_points_dischg]
    header.append(", ".join(temp_strings_dischg))
    header.append("};")
    header.append("")

    # Add charge temperature points
    header.append("// Charge temperatures")
    header.append(
        "static const float BATTERY_TEMP_POINTS_CHG[BATTERY_NUM_TEMP_POINTS] = {"
    )
    temp_strings_chg = [f"    {temp:.2f}f" for temp in temp_points_chg]
    header.append(", ".join(temp_strings_chg))
    header.append("};")
    header.append("")

    # Add internal resistance parameters
    header.append(
        "// Internal resistance curve parameters (rational function parameters a+b*t)/(c+d*t)"
    )
    header.append("static const float BATTERY_R_INT_PARAMS[4] = {")
    r_int_params = battery_model_data["r_int"]
    header.append("    // a, b, c, d for rational function (a + b*t)/(c + d*t)")
    header.append(
        f"    {r_int_params[0]:.6f}f, {r_int_params[1]:.6f}f, {r_int_params[2]:.6f}f, {r_int_params[3]:.6f}f"
    )
    header.append("};")
    header.append("")

    # Add discharge OCV curve parameters for each temperature
    header.append("// Discharge OCV curve parameters for each temperature")
    header.append(
        "static const float BATTERY_OCV_DISCHARGE_PARAMS[BATTERY_NUM_TEMP_POINTS][10] = {"
    )

    for temp_idx, temp_key in enumerate(temp_keys):
        ocv_data = battery_model_data["ocv_curves"][temp_key]
        ocv_params = ocv_data["ocv_dischg"]  # Updated key name
        actual_temp = ocv_data["bat_temp_dischg"]

        header.append(f"    // Temperature: {actual_temp:.2f}°C (key: {temp_key})")
        header.append("    {")
        header.append(
            f"        {ocv_params[0]:.6f}f, {ocv_params[1]:.6f}f, // m, b (linear segment)"
        )
        header.append(
            f"        {ocv_params[2]:.6f}f, {ocv_params[3]:.6f}f, {ocv_params[4]:.6f}f, {ocv_params[5]:.6f}f, // a1, b1, c1, d1 (first rational segment)"
        )
        header.append(
            f"        {ocv_params[6]:.6f}f, {ocv_params[7]:.6f}f, {ocv_params[8]:.6f}f, {ocv_params[9]:.6f}f  // a3, b3, c3, d3 (third rational segment)"
        )
        header.append("    }" + ("," if temp_idx < len(temp_keys) - 1 else ""))

    header.append("};")
    header.append("")

    # Add charge OCV curve parameters for each temperature
    header.append("// Charge OCV curve parameters for each temperature")
    header.append(
        "static const float BATTERY_OCV_CHARGE_PARAMS[BATTERY_NUM_TEMP_POINTS][10] = {"
    )

    for temp_idx, temp_key in enumerate(temp_keys):
        ocv_data = battery_model_data["ocv_curves"][temp_key]
        ocv_params = ocv_data["ocv_chg"]  # Updated key name
        actual_temp = ocv_data["bat_temp_chg"]

        header.append(f"    // Temperature: {actual_temp:.2f}°C (key: {temp_key})")
        header.append("    {")
        header.append(
            f"        {ocv_params[0]:.6f}f, {ocv_params[1]:.6f}f, // m, b (linear segment)"
        )
        header.append(
            f"        {ocv_params[2]:.6f}f, {ocv_params[3]:.6f}f, {ocv_params[4]:.6f}f, {ocv_params[5]:.6f}f, // a1, b1, c1, d1 (first rational segment)"
        )
        header.append(
            f"        {ocv_params[6]:.6f}f, {ocv_params[7]:.6f}f, {ocv_params[8]:.6f}f, {ocv_params[9]:.6f}f  // a3, b3, c3, d3 (third rational segment)"
        )
        header.append("    }" + ("," if temp_idx < len(temp_keys) - 1 else ""))

    header.append("};")
    header.append("")

    # Add capacity data
    header.append("// Battery capacity data for each temperature")
    header.append("static const float BATTERY_CAPACITY[BATTERY_NUM_TEMP_POINTS][2] = {")

    for temp_idx, temp_key in enumerate(temp_keys):
        ocv_data = battery_model_data["ocv_curves"][temp_key]
        discharge_capacity = ocv_data["total_capacity_dischg"]  # Updated key name
        charge_capacity = ocv_data["total_capacity_chg"]  # Updated key name
        actual_temp = ocv_data["bat_temp_dischg"]

        header.append(f"    // Temperature: {actual_temp:.2f}°C (key: {temp_key})")
        header.append(
            f"    {{ {discharge_capacity:.2f}f, {charge_capacity:.2f}f }}"
            + ("," if temp_idx < len(temp_keys) - 1 else "")
        )

    header.append("};")
    header.append("")
    header.append(f"#endif // {header_guard}")

    # Write the header to file
    with open(output_path, "w") as f:
        f.write("\n".join(header))

    print(f"Battery data header file generated: {output_path}")


def generate_battery_libraries(
    battery_model_data, output_dir=".", battery_name="default"
):
    """
    Generate all battery-related libraries

    Parameters:
    - battery_model_data: Dictionary containing battery model data
    - output_dir: Directory to save the output files
    - battery_name: Name identifier for the battery
    """
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Define file paths
    data_h = os.path.join(output_dir, f"battery_data_{battery_name.lower()}.h")

    # Generate files
    generate_battery_data_header(battery_model_data, battery_name, data_h)

    print(
        f"Battery model exported to {output_dir}/battery_data_{battery_name.lower()}.h"
    )
