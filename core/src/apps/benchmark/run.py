from typing import TYPE_CHECKING

from .benchmark import run_benchmark
from .benchmarks import benchmarks

if TYPE_CHECKING:
    from trezor.messages import BenchmarkResult, BenchmarkRun


async def run(msg: BenchmarkRun) -> BenchmarkResult:
    benchmark_name = msg.name

    if benchmark_name not in benchmarks:
        raise ValueError("Benchmark not found")

    benchmark = benchmarks[benchmark_name]
    result = run_benchmark(benchmark)

    return result
