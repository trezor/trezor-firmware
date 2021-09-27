import sys

from uio import open
from uos import getenv
import micropython

# We need to insert "" to sys.path so that the frozen build can import main from the
# frozen modules, and regular build can import it from current directory.
sys.path.insert(0, "")

PATH_PREFIX = (getenv("TREZOR_SRC") or ".") + "/"


class Coverage:
    def __init__(self):
        self.__files = {}

    def line_tick(self, filename, lineno):
        if not filename in self.__files:
            self.__files[filename] = set()
        self.__files[filename].add(lineno)

    def lines_execution(self):
        lines_execution = {"lines": {}}
        lines = lines_execution["lines"]
        this_file = globals()["__file__"]
        for filename in self.__files:
            if not filename == this_file:
                lines[PATH_PREFIX + filename] = list(self.__files[filename])

        return lines_execution


class _Prof:
    trace_count = 0
    display_flags = 0
    __coverage = Coverage()

    def trace_tick(self, frame, event, arg):
        self.trace_count += 1

        # if frame.f_code.co_filename.endswith('/loop.py'):
        #     print(event, frame.f_code.co_filename, frame.f_lineno)

        if event == "line":
            self.__coverage.line_tick(frame.f_code.co_filename, frame.f_lineno)

    def coverage_data(self):
        return self.__coverage.lines_execution()

    def write_data(self):
        print("Total traces executed: ", __prof__.trace_count)
        with open(".coverage", "w") as f:
            # wtf so private much beautiful wow
            f.write("!coverage.py: This is a private format, don't read it directly!")
            # poormans json
            f.write(str(__prof__.coverage_data()).replace("'", '"'))


class AllocCounter:
    def __init__(self):
        self.last_alloc_count = 0
        self.data = {}
        self.last_line = None

    def count_last_line(self, allocs):
        if self.last_line is None:
            return

        entry = self.data.setdefault(self.last_line, {
            "total_allocs": 0,
            "calls": 0,
        })
        entry["total_allocs"] += allocs
        entry["calls"] += 1

    def trace_tick(self, frame, event, arg):
        allocs_now = micropython.alloc_count()

        if event != "line":
            return

        allocs_per_last_line = allocs_now - self.last_alloc_count
        self.count_last_line(allocs_per_last_line)
        self.last_line = f"{frame.f_code.co_filename}:{frame.f_lineno}"
        self.last_alloc_count = micropython.alloc_count()

    def dump_data(self, filename):
        allocs_now = micropython.alloc_count()
        allocs_per_last_line = allocs_now - self.last_alloc_count
        self.count_last_line(allocs_per_last_line)
        with open(filename, "w") as f:
            for key, val in self.data.items():
                f.write("{} {total_allocs} {calls}\n".format(key, **val))

    def write_data(self):
        self.dump_data("alloc_data.txt")


def trace_handler(frame, event, arg):
    __prof__.trace_tick(frame, event, arg)
    return trace_handler


def atexit():
    print("\n------------------ script exited ------------------")
    __prof__.write_data()


sys.atexit(atexit)

global __prof__
if not "__prof__" in globals():
    if getenv("TREZOR_MEMPERF") == "1":
        __prof__ = AllocCounter()
    else:
        __prof__ = _Prof()

sys.settrace(trace_handler)

if isinstance(__prof__, AllocCounter):
    __prof__.last_alloc_count = micropython.alloc_count()

import main
