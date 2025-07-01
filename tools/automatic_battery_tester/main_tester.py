# main_tester.py

import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

import toml
from dut import DutController
from hardware_ctl import RelayController
from notifications import send_slack_message
from test_logic import LinearScenario, RandomWonderScenario, SwitchingScenario

# Configure logging
log_formatter = log_formatter = logging.Formatter(
    "[%(levelname).1s %(asctime)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)
log_file = "test.log"

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# Clear all existing handlers to avoid duplicates
if logger.hasHandlers():
    logger.handlers.clear()

# File handler
try:
    file_handler = logging.FileHandler(log_file, mode="w", encoding="utf-8")
    file_handler.setFormatter(log_formatter)
    file_handler.setLevel(logging.INFO)
    logger.addHandler(file_handler)
except Exception as log_e:
    print(f"WARNING: Failed to create file log handler for {log_file}: {log_e}")

# Console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(log_formatter)
console_handler.setLevel(logging.INFO)
logger.addHandler(console_handler)


def load_config(config_path="test_config.toml") -> Optional[Dict[str, Any]]:
    """Load test configuration from TOML config file ."""
    config_file = config_path
    logging.info(f"Loading configuration file: {config_file}")
    try:
        config = toml.load(config_file)

        # Validate required sections in the config file
        required_sections = ["general", "relay", "duts", "test_plan", "notifications"]

        for section in required_sections:
            if section not in config:
                raise ValueError(
                    f"Missing required section '{section}' in config file."
                )

        logging.info("Config file loading successfully.")
        return config

    except FileNotFoundError:
        logging.error(f"Configuration file not found at {config_file}")
        return None

    except toml.TomlDecodeError as e:
        logging.error(f"Error decoding TOML configuration file: {e}")
        return None

    except Exception as e:
        logging.error(f"Error loading configuration file: {e}")
        return None


def run_test_cycle(
    config: dict,
    temp_c: float,
    cycle_num: int,
    test_mode: str,
    relay_ctl: RelayController,
    dut_ctl: DutController,
) -> bool:
    """Run single test cycle for given test mode on all DUTs at specified temperature"""

    # Select test scenario
    if test_mode == "linear":

        test_scenario = LinearScenario(
            discharge_load=config["test_plan"]["linear_discharge_load"],
            relaxation_time_min=config["test_plan"]["linear_relaxation_time_min"],
        )

    elif test_mode == "switching":

        test_scenario = SwitchingScenario(
            discharge_switch_cycle_min=config["test_plan"][
                "switching_discharge_switch_cycle_min"
            ],
            relaxation_time_min=config["test_plan"]["switching_relaxation_time_min"],
        )

    elif test_mode == "random_wonder":

        test_scenario = RandomWonderScenario(
            core_test_time=config["test_plan"]["random_wonder_core_test_time_min"],
            relaxation_time_min=config["test_plan"][
                "random_wonder_relaxation_time_min"
            ],
        )

    else:

        logging.error(f"Unknown test mode: {test_mode}. Cannot run test cycle.")
        return False

    # Setup
    test_scenario.setup(dut_controller=dut_ctl)

    # Test loop
    while True:

        # Call run function in loop to execute the test scenario.
        finished = test_scenario.run(dut_controller=dut_ctl)

        # Read power manager report and log them to file
        test_scenario.log_data(
            dut_controller=dut_ctl,
            output_directory=Path(config["general"]["output_directory"]),
            temp=temp_c,
        )

        if finished:
            break  # Exit test loop

        time.sleep(1)

    # Tear down test scenario
    test_scenario.teardown(dut_controller=dut_ctl)

    return True


def main():

    logging.info("==============================================")
    logging.info("   Starting Automated Battery Cycle Tester    ")
    logging.info("==============================================")

    config = load_config()
    if config is None:
        logging.critical("Failed to load configuration. Exiting.")
        sys.exit(1)

    # Initialize hardware controllers
    logging.info("Initializing hardware controllers...")
    relay_ctl = None
    dut_ctl = None

    logging.info("==============================================")
    logging.info("   Initializing Peripherals                   ")
    logging.info("==============================================")

    try:

        # Initialize relay controller (Deditec board)
        relay_ctl = RelayController(ip_address=config["relay"]["ip_address"])

        # Initialize DUTs
        from dut.dut_controller import DutController

        dut_ctl = DutController(config["duts"], relay_ctl=relay_ctl, verbose=False)

    except Exception as e:
        logging.exception(f"Failed to intialize peripherals: {e}")
        exit(1)

    # Create output data directory
    output_data_dir = Path(config["general"]["output_directory"])
    try:
        output_data_dir.mkdir(parents=True, exist_ok=True)
        logging.info(f"Test results will be saved in: {output_data_dir.resolve()}")
    except OSError as e:
        logging.critical(
            f"Failed to create output directory {output_data_dir}: {e}. Exiting."
        )
        if relay_ctl:
            relay_ctl.close()
        if dut_ctl:
            dut_ctl.close()
        sys.exit(1)

    ############################################################################
    # LOAD TEST PLAN
    ############################################################################

    logging.info("==============================================")
    logging.info("   TEST PLAN LOADING                          ")
    logging.info("==============================================")

    temperatures = config["test_plan"].get("temperatures_celsius", [25])
    test_modes_to_run = config["test_plan"].get("test_modes", ["linear"])
    cycles_per_temp = config["test_plan"].get("cycles_per_temperature", 1)
    total_runs = len(temperatures) * cycles_per_temp * len(test_modes_to_run)
    completed_runs = 0

    logger.info(f" + Tested temperatures       : {temperatures}")
    logger.info(f" + Cycles per temperature    : {cycles_per_temp}")
    logger.info(f" + Test modes in every cycle : {test_modes_to_run}")
    logger.info(f" + Total runs planned        : {total_runs}")

    start_time = time.time()
    test_aborted = False

    ############################################################################
    # MAIN TEST LOOP
    ############################################################################
    try:

        # Run a full test cycle for each temperature setting.
        # since the temperature chamber is still controlled only manually, every
        # test will notify the user to set the temperature manually before it
        # start next iteration.
        for temp_c in temperatures:

            # Set temperature in temperature chamber
            logging.info("==============================================")
            logging.info(f"   {temp_c} °C TEMP TEST                      ")
            logging.info("==============================================")
            logging.info(
                f"Set the temperature chamber to {temp_c} °C and wait for stabilization."
            )

            try:
                if config["notifications"]["notification_channel"] == "slack":
                    send_slack_message(
                        config["notifications"]["slack_webhook_url"],
                        f"""Set the temperature chamber to {temp_c} °C and confirm to continue with the test.""",
                    )
            except Exception as e:
                logging.error(f"Failed to send Slack notification: {e}")

            while True:
                user_input = input(f"Confirm temperature is set to {temp_c} °C (Y)?")
                if user_input.lower() == "y":
                    break

            for cycle_num in range(cycles_per_temp):

                for test_mode in test_modes_to_run:

                    run_start_time = time.time()
                    logging.info(f"Running Test Mode: '{test_mode}'")

                    success = run_test_cycle(
                        config, temp_c, cycle_num, test_mode, relay_ctl, dut_ctl
                    )

                    run_end_time = time.time()
                    run_duration_m = (run_end_time - run_start_time) / 60

                    if success:
                        completed_runs += 1
                        logging.info(
                            f"Test Mode '{test_mode}' finished successfully in {run_duration_m:.1f} minutes."
                        )
                    else:
                        logging.error(
                            f"Test Mode '{test_mode}' failed after {run_duration_m:.1f} minutes."
                        )
                        if config.get("general", {}).get("fail_fast", False):
                            logging.warning(
                                "Fail fast enabled. Aborting entire test plan."
                            )
                            test_aborted = True
                            break
                        else:
                            logging.info(
                                "Continuing with the next mode/cycle/temperature."
                            )

                    logging.info(
                        f"Progress: {completed_runs}/{total_runs} total runs completed."
                    )

                if test_aborted:
                    break

            if test_aborted:
                break

            logging.info("==============================================")
            logging.info("   TEST FINISHED                              ")
            logging.info("==============================================")

    except KeyboardInterrupt:
        logging.warning("Test execution interrupted by user (Ctrl+C)")
        test_aborted = True
    except Exception as e:
        logging.exception(f"FATAL ERROR during test execution: {e}")
        test_aborted = True
    finally:

        logging.info("Performing final cleanup...")
        if relay_ctl:
            try:
                logging.info("Ensuring all relays are OFF...")
                dut_ctl.power_down_all()  # Power down all DUTs
                relay_ctl.close()
            except Exception as e_relay:
                logging.error(f"Error during relay cleanup: {e_relay}")

        if dut_ctl:
            try:
                dut_ctl.close()
            except Exception as e_dut:
                logging.error(f"Error during DUT controller cleanup: {e_dut}")

        logging.info("==================== TEST SUMMARY ====================")
        end_time = time.time()
        total_duration_s = end_time - start_time
        total_duration_h = total_duration_s / 3600
        status = (
            "ABORTED"
            if test_aborted
            else (
                "COMPLETED" if completed_runs == total_runs else "PARTIALLY COMPLETED"
            )
        )
        logging.info("-" * 60)
        logging.info(f"Test execution {status}.")
        logging.info(f"Total runs completed: {completed_runs}/{total_runs}")
        logging.info(
            f"Total duration: {total_duration_s:.0f} seconds ({total_duration_h:.2f} hours)."
        )
        logging.info("==================== TEST END     ====================")


if __name__ == "__main__":
    # Ensure at least one handler is set up
    if not logger.hasHandlers():
        logger.addHandler(logging.StreamHandler(sys.stdout))
    main()
