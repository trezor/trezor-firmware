from abc import ABC, abstractmethod

class TestScenario(ABC):
    """Parent class for test scenarios."""

    @abstractmethod
    def setup(self):
        pass

    @abstractmethod
    def run(self):
        pass

    @abstractmethod
    def teardown(self):
        pass

    @abstractmethod
    def log_data(self):
        pass


















































