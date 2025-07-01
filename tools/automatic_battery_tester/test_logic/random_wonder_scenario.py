import enum
import logging
import random
import time
from pathlib import Path

from dut.dut_controller import DutController

from .test_scenario import TestScenario

SKIP_CHARGING = False
SKIP_RELAXING = False
SKIP_RANDOM_WONDER = False
SKIP_DISCHARGING = False


class ScenarioPhase(enum.Enum):
    NOT_STARTED = 0
    CHARGING = 1
    CHARGED_RELAXING = 2
    RANDOM_WONDER = 3
    DISCHARGING = 4
    DISCHARGED_RELAXING = 5
    DONE = 6


class RandomWonderScenario(TestScenario):

    def __init__(self, core_test_time=60, relaxation_time_min=60):

        self.relaxation_time_min = relaxation_time_min
        self.phase_start = time.time()
        self.core_test_time = core_test_time
        self.random_cycle_time_min = 10
        self.random_direction_up = True
        self.random_discharge_load = 100
        self.random_cycle_start = 0
        self.remaining_time = time.time()
        self.scenario_phase = ScenarioPhase.NOT_STARTED
        self.time_id = "0000000000"
        self.previous_phase = ScenarioPhase.NOT_STARTED

    def setup(self, dut_controller: DutController):

        # Start with charging phase first, so connect the charger with relay
        # and enable the charging.
        self.scenario_phase = ScenarioPhase.CHARGING
        dut_controller.power_up_all()  # Power up all DUTs

        # Wait for DUTs to power up
        time.sleep(3)

        dut_controller.set_backlight(150)
        dut_controller.set_soc_limit(100)
        dut_controller.enable_charging()

        time.sleep(1)  # Give some time for the command to be processed

        self.phase_start = time.time()
        self.test_time_id = f"{time.strftime('%y%m%d%H%M')}"

    def run(self, dut_controller):

        if self.previous_phase != self.scenario_phase:
            logging.info(f"Random Wonder scenario entered {self.scenario_phase} phase.")
            self.previous_phase = self.scenario_phase

        # Charge until all DuT is above certain voltage threshold and charging
        # state is IDLE (means that PMIC automatically stopped charging)
        # Move to next phase when all DUTs are charged.
        if self.scenario_phase == ScenarioPhase.CHARGING:

            if dut_controller.all_duts_charged() or SKIP_CHARGING:
                self.scenario_phase = ScenarioPhase.CHARGED_RELAXING
                self.phase_start = time.time()

        # Relax
        elif self.scenario_phase == ScenarioPhase.CHARGED_RELAXING:

            # Relaxation time is set in minutes, so convert to seconds
            if (time.time() - self.phase_start) >= (
                self.relaxation_time_min * 60
            ) or SKIP_RELAXING:

                dut_controller.power_down_all()
                self.scenario_phase = ScenarioPhase.RANDOM_WONDER
                self.phase_start = time.time()

            else:

                elapsed_min = int((time.time() - self.phase_start) / 60)
                if self.remaining_time != self.relaxation_time_min - elapsed_min:
                    # Update remaining time only if it changed
                    self.remaining_time = self.relaxation_time_min - elapsed_min
                    logging.info(
                        f"Relaxing for {self.relaxation_time_min} minutes, remaining: {self.remaining_time} minutes"
                    )

        elif self.scenario_phase == ScenarioPhase.RANDOM_WONDER:

            # Random Wonder phase, switch the backlight intensity to change
            # the discharge current.
            if (time.time() - self.phase_start) >= (
                self.core_test_time * 60
            ) or SKIP_RANDOM_WONDER:

                # Random wonder test over
                dut_controller.power_down_all()
                dut_controller.set_backlight(100)
                self.scenario_phase = ScenarioPhase.DISCHARGING

                # Reset phase start time
                self.phase_start = time.time()

            elif self.random_direction_up and dut_controller.any_dut_charged():

                # One of the DUTs is charged, bounce back to discharging.
                logging.info("One of the DUTs is charged, switching back to relaxing.")
                self.random_direction_up = False

                dut_controller.power_down_all()
                dut_controller.disable_charging()

                self.random_cycle_time_min = random.randint(
                    5, 15
                )  # Random cycle time between 5 and 15 minutes
                self.random_discharge_load = random.randint(
                    0, 225
                )  # Random discharge load between 0 and 225
                dut_controller.set_backlight(
                    self.random_discharge_load
                )  # Set backlight to 0 to stop discharge

                self.random_cycle_start = time.time()

            elif not self.random_direction_up and dut_controller.any_dut_discharged():

                # One of the DUTs got discharged, bounce back to charging.

                logging.info(
                    "One of the DUTs got discharged, switching back to charging."
                )
                self.random_direction_up = True

                dut_controller.power_up_all()  # Power up all DUTs
                dut_controller.enable_charging()  # Enable charging

                self.random_cycle_time_min = random.randint(
                    5, 15
                )  # Random cycle time between 5 and 15 minutes
                self.random_cycle_start = time.time()

            else:

                if (time.time() - self.random_cycle_start) >= (
                    self.random_cycle_time_min * 60
                ):

                    # Randomize following section
                    self.random_direction_up = random.choice([True, False])
                    self.random_cycle_time_min = random.randint(
                        5, 15
                    )  # Random cycle time between 5 and 15 minutes

                    if self.random_direction_up:

                        # Enable charging
                        dut_controller.power_up_all()  # Power up all DUTs
                        dut_controller.enable_charging()

                    else:

                        self.random_discharge_load = random.randint(
                            0, 225
                        )  # Random discharge load between 0 and 225

                        dut_controller.disable_charging()  # Disable charging
                        dut_controller.power_down_all()  # Power down all DUTs
                        dut_controller.set_backlight(
                            self.random_discharge_load
                        )  # Set backlight to 0 to stop discharge

                    # Reset phase start time
                    self.random_cycle_start = time.time()

                    logging.info(
                        f"Random Wonder cycle changed: "
                        f"direction={'up' if self.random_direction_up else 'down'}, "
                        f"cycle_time={self.random_cycle_time_min}min, "
                        f"discharge_load={self.random_discharge_load}"
                    )

            # Continue in random wonder phase

        elif self.scenario_phase == ScenarioPhase.DISCHARGING:

            if dut_controller.all_duts_discharged() or SKIP_DISCHARGING:
                self.scenario_phase = ScenarioPhase.DISCHARGED_RELAXING
                self.phase_start = time.time()

        elif self.scenario_phase == ScenarioPhase.DISCHARGED_RELAXING:

            # Relaxation time is set in minutes, so convert to seconds
            if (time.time() - self.phase_start) >= (
                self.relaxation_time_min * 60
            ) or SKIP_RELAXING:

                self.scenario_phase = ScenarioPhase.DONE
                logging.info("Scenario completed successfully.")
                return True

            else:
                elapsed_min = int((time.time() - self.phase_start) / 60)

                if self.remaining_time != self.relaxation_time_min - elapsed_min:
                    # Update remaining time only if it changed
                    self.remaining_time = self.relaxation_time_min - elapsed_min
                    logging.info(
                        f"Relaxing for {self.relaxation_time_min} minutes, remaining: {self.remaining_time} minutes"
                    )

        # Relax
        return False

    def log_data(self, dut_controller, output_directory: Path, temp):

        dut_controller.log_data(
            output_directory,
            self.test_time_id,
            "random_wonder",
            self.scenario_phase.name.lower(),
            temp,
        )

    def teardown(self, dut_controller):
        pass
