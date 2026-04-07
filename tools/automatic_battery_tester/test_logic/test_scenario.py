from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from dut.dut_controller import DutController


class TestScenario(ABC):
    """Parent class for test scenarios."""

    @abstractmethod
    def setup(self, dut_controller: DutController) -> None:
        pass

    @abstractmethod
    def run(self, dut_controller: DutController) -> bool:
        pass

    @abstractmethod
    def teardown(self, dut_controller: DutController) -> None:
        pass

    @abstractmethod
    def log_data(
        self, dut_controller: DutController, output_directory: Path, temp: float | int
    ) -> None:
        pass
