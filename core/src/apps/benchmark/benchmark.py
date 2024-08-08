import utime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Protocol

    from trezor.messages import BenchmarkResult

    class Benchmark(Protocol):
        def prepare(self) -> None: ...

        def run(self) -> None: ...

        def get_result(self, duration_us: int, repetitions: int) -> BenchmarkResult: ...


def run_benchmark(benchmark: Benchmark) -> BenchmarkResult:
    minimum_duration_s = 1
    minimum_duration_us = minimum_duration_s * 1000000
    benchmark.prepare()
    start_time_us = utime.ticks_us()
    repetitions = 0
    while True:
        benchmark.run()
        repetitions += 1
        duration_us = utime.ticks_diff(utime.ticks_us(), start_time_us)
        if duration_us > minimum_duration_us:
            break
    return benchmark.get_result(duration_us, repetitions)
