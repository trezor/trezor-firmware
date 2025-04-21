import micropython
import sys
from typing import TYPE_CHECKING, Any, Callable, TypeAlias

import coveragedata
from uio import open
from uos import getenv

if TYPE_CHECKING:
    from types import FrameType

    TraceFunction: TypeAlias = Callable[[FrameType, str, Any], "TraceFunction"]


# We need to insert "" to sys.path so that the frozen build can import main from the
# frozen modules, and regular build can import it from current directory.
sys.path.insert(0, "")

PATH_PREFIX = (getenv("TREZOR_SRC") or ".") + "/"


class _Prof:
    trace_count = 0
    display_flags = 0

    def trace_tick(self, frame: FrameType, event: str) -> None:
        self.trace_count += 1

        # if frame.f_code.co_filename.endswith('/loop.py'):
        #     print(event, frame.f_code.co_filename, frame.f_lineno)

        if event == "line":
            coveragedata.add(frame.f_code.co_filename, frame.f_lineno)

    def write_data(self) -> None:
        print("Traces count: ", self.trace_count)
        data = coveragedata.get()
        print("Lines covered:", len(data))
        file_map = {}
        for name, line in data:
            file_map.setdefault(PATH_PREFIX + name, []).append(line)
        print("Files covered:", len(file_map))

        # In case of multithreaded tests, we might be called multiple times.
        # Making sure the threads do not overwrite each other's data.
        worker_id = getenv("PYTEST_XDIST_WORKER")
        if worker_id:
            file_name = f".coverage.{worker_id}.json"
        else:
            file_name = ".coverage.json"
        with open(file_name, "w") as f:
            # poormans json
            f.write(str(file_map).replace("'", '"'))


class AllocCounter:
    def __init__(self) -> None:
        self.last_alloc_count = 0
        self.data = {}
        self.last_line = None

    def count_last_line(self, allocs: int) -> None:
        if self.last_line is None:
            return

        entry = self.data.setdefault(
            self.last_line,
            {
                "total_allocs": 0,
                "calls": 0,
            },
        )
        entry["total_allocs"] += allocs
        entry["calls"] += 1

    def trace_tick(self, frame: FrameType, event: str) -> None:
        allocs_now = micropython.alloc_count()

        if event != "line":
            return

        allocs_per_last_line = allocs_now - self.last_alloc_count
        self.count_last_line(allocs_per_last_line)
        self.last_line = f"{frame.f_code.co_filename}:{frame.f_lineno}"
        self.last_alloc_count = micropython.alloc_count()

    def dump_data(self, filename: str) -> None:
        allocs_now = micropython.alloc_count()
        allocs_per_last_line = allocs_now - self.last_alloc_count
        self.count_last_line(allocs_per_last_line)
        with open(filename, "w") as f:
            for key, val in self.data.items():
                f.write(f'{key} {val["total_allocs"]} {val["calls"]}\n')

    def write_data(self) -> None:
        self.dump_data("alloc_data.txt")


def trace_handler(frame: FrameType, event: str, _arg: Any) -> TraceFunction:
    __prof__.trace_tick(frame, event)
    return trace_handler


global __prof__
if "__prof__" not in globals():
    if getenv("TREZOR_MEMPERF") == "1":
        __prof__ = AllocCounter()
    else:
        __prof__ = _Prof()

sys.settrace(trace_handler)

if isinstance(__prof__, AllocCounter):
    __prof__.last_alloc_count = micropython.alloc_count()

try:
    import main  # noqa: F401
finally:
    print("\n------------------ script exited ------------------")
    __prof__.write_data()
