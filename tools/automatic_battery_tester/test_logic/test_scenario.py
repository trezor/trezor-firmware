from abc import ABC, abstractmethod


class TestScenario(ABC):
    """Parent class for test scenarios."""

    @abstractmethod
    def setup(self) -> None:
        pass

    @abstractmethod
    def run(self) -> bool:
        pass

    @abstractmethod
    def teardown(self) -> None:
        pass

    @abstractmethod
    def log_data(self) -> None:
        pass
