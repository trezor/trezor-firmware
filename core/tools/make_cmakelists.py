import argparse


def gen(sources, dirs, defs):
    target = "CMakeLists.txt"

    with open(target, 'w') as f:

        f.write("cmake_minimum_required(VERSION 3.20)\n")
        f.write("project(core)\n")
        f.write("\n")
        f.write("set(CMAKE_CXX_STANDARD 14)\n")

        f.write("\n")
        f.write("\n")

        f.write("add_definitions(\n")
        for d in defs:
            f.write(f'        -D{d}\n')
        f.write(")\n")

        f.write("\n")
        f.write("\n")
        for d in dirs:
            f.write(f'include_directories({d})\n')

        f.write("\n")
        f.write("\n")
        f.write("add_executable(core\n")

        for s in sources:
            f.write(f'        {s}\n')
        f.write(")\n")
        f.write("\n")


if __name__ == "__main__":
    CLI = argparse.ArgumentParser()
    CLI.add_argument(
        "--sources",
        nargs="*",
        type=str,
        default=[],
    )
    CLI.add_argument(
        "--dirs",
        nargs="*",
        type=str,
        default=[],
    )
    CLI.add_argument(
        "--defs",
        nargs="*",
        type=str,
        default=[],
    )

    args = CLI.parse_args()
    gen(args.sources, args.dirs, args.defs)
