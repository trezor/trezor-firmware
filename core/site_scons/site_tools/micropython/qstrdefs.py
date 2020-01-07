import re
import sys


def process(source, target):
    re_qstr = re.compile(r"MP_QSTR_[_a-zA-Z0-9]+")
    for line in source:
        for match in re_qstr.findall(line):
            name = match.replace("MP_QSTR_", "")
            target.write("Q(%s)\n" % name)


if __name__ == "__main__":
    process(sys.stdin, sys.stdout)
