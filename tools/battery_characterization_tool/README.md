# Battery Characterization Tool

A comprehensive tool for LiFePO4 battery model identification, simulation, and analysis. This tool processes battery test data to extract battery characteristics, generate battery models, and simulate battery behavior under various conditions.

**Battery Model**: Simple model with single internal resistance (no capacity modeling).

## Prerequisites

- Python 3.8 or higher

## Project Structure

```bash
battery_characterization_tool/
├── README.md                         # This file
├── requirements.txt                  # Python dependencies
├── battery_model_identification.py   # Main identification script
├── fuel_gauge_simulator.py           # Main simulator script
├── dataset/                          # Dataset management
│   ├── battery_dataset.py            # Dataset loading and processing
│   ├── battery_profile.py            # Battery profile utilities
│   └── datasets/                     # Battery test data
├── models/                           # Battery modeling
│   ├── battery_model.py              # Core battery model class
│   ├── identification.py             # Model identification algorithms
│   ├── simulator.py                  # Battery simulation engine
│   ├── estimators/                   # State estimation algorithms
│   └── battery_models/               # Configuration files (*.toml)
├── utils/                            # Utilities
│   ├── c_lib_generator.py            # C library generation
│   └── console_formatter.py          # Console output formatting
└── exported_data/                    # Generated output
    ├── battery_models/               # Generated battery models (*.json)
    └── simulation_results/           # Simulation outputs
```

## Installation

### 1. Create and Activate Python Virtual Environment

```bash
cd tools/battery_characterization_tool

# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate
```

### 2. Install Dependencies

With the virtual environment activated, install the required packages:

```bash
pip install -r requirements.txt
```

## Battery Model Identification Script

The battery model identification script processes captured battery data from a selected dataset to estimate battery internal resistance and open-circuit voltage across a given temperature range. The estimated data is compiled into a battery model which is then exported for further use in the `fuel_gauge_simulator.py` script and embedded libraries.

**Prerequisites before running:**

- Add a correctly formatted dataset to the `/dataset/datasets/` directory
- Add a battery model configuration `.toml` file in `models/battery_models/`

### Dataset Structure

Battery datasets should be organized in the `dataset/datasets/` directory. Each dataset should have its own directory and contain CSV files with battery test data in the following format:

```bash
<battery_id>.<timestamp_id>.<test_mode>.<mode_phase>.<temperature>.csv
```

**Example:**

```text
eb95.2507251530.linear.charging.25.csv
```

> **Note:** Battery datasets are typically created by the `automatic_battery_tester` tool available in `tools/automatic_battery_tester`

### Battery Model Configuration File

Battery models are configured using TOML files located in `models/battery_models/`.

**Example configuration:**

```toml
battery_manufacturer = "JYHPFL333838"
temperatures_to_process = ["20", "25", "15", "30"]
```

### Running in Interactive Mode

Running the script without parameters will start interactive mode, prompting you to select a battery dataset and model:

```bash
python battery_model_identification.py
```

### Command Line Options

```bash
# Select dataset and configuration file directly
python battery_model_identification.py --config-file <path_to_config> --dataset <path_to_dataset>

# Enable debug mode for basic debug plots
python battery_model_identification.py --debug

# Enable trace mode for detailed plots
python battery_model_identification.py --trace
```

## Fuel Gauge Simulator Script

The fuel gauge simulator script takes an identified battery model `.json` file and uses it to simulate the behavior of various fuel gauge estimator implementations (such as Extended Kalman Filter, Coulomb Counter, or Dummy estimator). The script prompts the user to select a battery model and dataset to run a simulation on. Simulation result graphs are exported to `exported_data/simulation_results/`.

### Running the Script

The simulator runs in interactive mode, guiding you through:

1. **Dataset Selection**: Choose from available datasets in `dataset/datasets/`
2. **Battery Model Selection**: Choose from generated models in `exported_data/battery_models/`

```bash
python fuel_gauge_simulator.py
```

## Output Files

### Battery Model Identification

- **Battery Models**: JSON files in `exported_data/battery_models/`
- **C Libraries**: Header with battery model data for embedded use
- **Debug Plots**: Visualization of identified parameters (when `--debug` or `--trace` enabled)

### Fuel Gauge Simulation

- **Simulation Results**: Graphs and data in `exported_data/simulation_results/`

## License

This tool is part of the Trezor firmware project. Please refer to the main repository license for details.
