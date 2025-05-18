from trezor import log
from trezor.messages import BenchmarkResult

from .common import format_float


class LogBenchmark:
    def __init__(self) -> None:
        pass

    def prepare(self) -> None:
        self.iterations_count = 10000

    def run(self) -> None:
        for i in range(self.iterations_count):
            log.debug(__name__, "msg #%d", i)

    def get_result(self, duration_us: int, repetitions: int) -> BenchmarkResult:
        return BenchmarkResult(
            value=format_float(duration_us / (repetitions * self.iterations_count)),
            unit="us",
        )
