from trezor import miniscript
from trezor.messages import BenchmarkResult

from .common import format_float


class MiniscriptBenchmark:
    def __init__(self) -> None:
        pass

    def prepare(self, descriptor: str, internal: str, index: str) -> None:
        self.args = (descriptor, bool(internal), int(index))
        self.iterations_count = 10

    def run(self) -> None:
        for _ in range(self.iterations_count):
            miniscript.compile(*self.args)

    def get_result(self, duration_us: int, repetitions: int) -> BenchmarkResult:
        return BenchmarkResult(
            value=format_float(duration_us / (repetitions * self.iterations_count)),
            unit="us",
        )
