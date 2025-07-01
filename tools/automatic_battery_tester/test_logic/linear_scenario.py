import enum
import logging
import time
from pathlib import Path

from dut.dut_controller import DutController

from .test_scenario import TestScenario

SKIP_CHARGING = False
SKIP_RELAXING = False
SKIP_DISCHARGING = False


class ScenarioPhase(enum.Enum):
    NOT_STARTED = 0
    CHARGING = 1
    CHARGED_RELAXING = 2
    DISCHARGING = 3
    DISCHARGED_RELAXING = 4
    DONE = 5


class LinearScenario(TestScenario):

    def __init__(self, discharge_load=100, relaxation_time_min=60):

        # DUT use display backlight intensity to change its load (discharge
        # current). Backlight intensity could be set in range of 0-255, but
        # there is no direct translation into discharge current.
        # Typically the discharge current is ~aprx 80mA with backlight set to 0
        # and 220mA when set to max 225.
        self.discharge_load = discharge_load
        self.relaxation_time_min = relaxation_time_min
        self.phase_start = time.time()
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
            logging.info(f"Linear scenario entered {self.scenario_phase} phase.")
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
                dut_controller.set_backlight(self.discharge_load)
                self.scenario_phase = ScenarioPhase.DISCHARGING
                self.phase_start = time.time()

            else:

                elapsed_min = int((time.time() - self.phase_start) / 60)

                if self.remaining_time != self.relaxation_time_min - elapsed_min:
                    # Update remaining time only if it changed
                    self.remaining_time = self.relaxation_time_min - elapsed_min
                    logging.info(
                        f"Relaxing for {self.relaxation_time_min} minutes, remaining: {self.remaining_time} minutes"
                    )

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
            "linear",
            self.scenario_phase.name.lower(),
            temp,
        )

    def teardown(self, dut_controller):
        pass
