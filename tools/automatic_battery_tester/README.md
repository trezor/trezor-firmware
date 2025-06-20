# Automated Battery Cycle Tester

This project provides a framework for automated testing of charging and discharging cycles of batteries in connected devices (DUT - Device Under Test). It supports multiple test scenarios (Linear, Switching, Random Wonder) at various temperatures, logs detailed data for later analysis, and offers configurable user feedback (Slack notifications).

---

## Project Structure

```
.
├── hardware_ctl/         # Hardware control (relay, DUT, temperature)
├── test_logic/           # Test scenario logic
├── test_results/         # Output CSV logs
├── main_tester.py        # Main entry point
├── test_config.toml      # Configuration file
├── requirements.txt      # Python dependencies
└── README.md             # This file
```

---

## Installation

1. **Python 3.9+ required**

2. **Create and activate a virtual environment:**
   ```sh
   python -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies:**
   ```sh
   pip install -r requirements.txt
   ```

4. **Slack Webhook (optional):**
   If you want Slack notifications, create an [Incoming Webhook](https://api.slack.com/messaging/webhooks) and add the URL to `test_config.toml`.

---

## Configuration

Edit [`test_config.toml`](test_config.toml) to set up:

- **[general]:** Output directory, logging interval, etc.
- **[[duts]]:** List of DUTs (name, CPU ID, USB port, relay port).
- **[relay]:** Relay board IP address.
- **[test_plan]:** Temperatures, cycles, modes, and parameters for each mode.
- **[notifications]:** Slack webhook and channel.

Example:
```toml
[general]
output_directory = "test_results"
log_interval_seconds = 1

[[duts]]
name = "DUT1"
cpu_id = "05001D000A50325557323120"
usb_port = "/dev/ttyACM0"
relay_port = 6

[relay]
ip_address = "192.168.1.10"

[test_plan]
temperatures_celsius = [15, 20, 25, 30, 35, 40, 45]
cycles_per_temperature = 3
test_modes = ["linear", "switching", "random_wonder"]
```

---

## Running the Test

1. Activate the virtual environment:
   ```sh
   source .venv/bin/activate
   ```
2. Edit `test_config.toml` as needed.
3. Run the main script:
   ```sh
   python main_tester.py
   ```
4. Follow console instructions or check log in "test.log" file.

---

## Results

- Results are saved in the `test_results/` directory as CSV files.
- Each test mode and phase has its own file, e.g.:
  ```
  274d.2506161536.linear.charged_relaxing.10.csv
  274d.2506161536.linear.discharged_relaxing.10.csv
  ```

---

## Authors

- [Trezor Firmware Project Team](https://github.com/trezor/trezor-firmware)

---
