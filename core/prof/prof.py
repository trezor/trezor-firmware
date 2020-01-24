import sys

from uio import open
from uos import getenv

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


def trace_handler(frame, event, arg):
    __prof__.trace_tick(frame, event, arg)
    return trace_handler


def atexit():
    print("\n------------------ script exited ------------------")
    print("Total traces executed: ", __prof__.trace_count)
    with open(".coverage", "w") as f:
        # wtf so private much beautiful wow
        f.write("!coverage.py: This is a private format, don't read it directly!")
        # poormans json
        f.write(str(__prof__.coverage_data()).replace("'", '"'))


sys.atexit(atexit)

global __prof__
if not "__prof__" in globals():
    __prof__ = _Prof()

sys.settrace(trace_handler)
import main
