import re
import sys


def process(source, target):
    re_module = re.compile(r"MP_REGISTER_MODULE\(.*?,\s*.*?\);")
    for line in source:
        for match in re_module.findall(line):
            target.write(f"{match}\n")


if __name__ == "__main__":
    process(sys.stdin, sys.stdout)
