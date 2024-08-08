from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import BenchmarkListNames, BenchmarkNames

from .benchmarks import benchmarks


async def list_names(msg: BenchmarkListNames) -> "BenchmarkNames":
    from trezor.messages import BenchmarkNames

    names = list(benchmarks.keys())
    sorted_names = sorted(names)

    return BenchmarkNames(names=sorted_names)
