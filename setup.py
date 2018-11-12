#!/usr/bin/env python3
import glob
import json
import os.path
import re
import subprocess
import sys
from distutils.errors import DistutilsError

from setuptools import Command, find_packages, setup
from setuptools.command.build_py import build_py
from setuptools.command.develop import develop

install_requires = [
    "setuptools>=19.0",
    "ecdsa>=0.9",
    "mnemonic>=0.17",
    "requests>=2.4.0",
    "click>=7,<8",
    "pyblake2>=0.9.3",
    "libusb1>=1.6.4",
    "construct>=2.9",
    "typing_extensions>=3.6",
]

CWD = os.path.dirname(os.path.realpath(__file__))
TREZOR_COMMON = os.path.join(CWD, "vendor", "trezor-common")


def read(*path):
    filename = os.path.join(CWD, *path)
    with open(filename, "r") as f:
        return f.read()


def find_version():
    version_file = read("trezorlib", "__init__.py")
    version_match = re.search(r"^__version__ = \"(.*)\"$", version_file, re.M)
    if version_match:
        return version_match.group(1)
    else:
        raise RuntimeError("Version string not found")


def build_coins_json(dst):
    TOOLS_PATH = os.path.join(TREZOR_COMMON, "tools")
    sys.path.insert(0, TOOLS_PATH)
    import coin_info

    coins = coin_info.coin_info().bitcoin
    support = coin_info.support_info(coins)
    for coin in coins:
        coin["support"] = support[coin["key"]]

    with open(dst, "w") as f:
        json.dump(coins, f, indent=2, sort_keys=True)

    del sys.path[0]


class PrebuildCommand(Command):
    description = "update vendored files (coins.json, protobuf messages)"
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        # check for existence of the submodule directory
        common_defs = os.path.join(TREZOR_COMMON, "defs")
        if not os.path.exists(common_defs):
            raise DistutilsError(
                "trezor-common submodule seems to be missing.\n"
                + "Use 'git submodule update --init' to retrieve it."
            )

        # generate and copy coins.json to the tree
        coins_json = os.path.join(CWD, "trezorlib", "coins.json")
        build_coins_json(coins_json)

        # regenerate messages
        try:
            proto_srcs = glob.glob(os.path.join(TREZOR_COMMON, "protob", "*.proto"))
            subprocess.check_call(
                [
                    sys.executable,
                    os.path.join(TREZOR_COMMON, "protob", "pb2py"),
                    "-o",
                    os.path.join(CWD, "trezorlib", "messages"),
                    "-P",
                    "..protobuf",
                ]
                + proto_srcs
            )
        except Exception as e:
            raise DistutilsError(
                "Generating protobuf failed. Make sure you have 'protoc' in your PATH."
            ) from e


def _patch_prebuild(cls):
    """Patch a setuptools command to depend on `prebuild`"""
    orig_run = cls.run

    def new_run(self):
        self.run_command("prebuild")
        orig_run(self)

    cls.run = new_run


_patch_prebuild(build_py)
_patch_prebuild(develop)


setup(
    name="trezor",
    version=find_version(),
    author="TREZOR",
    author_email="info@trezor.io",
    license="LGPLv3",
    description="Python library for communicating with TREZOR Hardware Wallet",
    long_description="{}\n\n{}".format(read("README.md"), read("CHANGELOG.md")),
    long_description_content_type="text/markdown",
    url="https://github.com/trezor/python-trezor",
    packages=find_packages(),
    package_data={"trezorlib": ["coins.json"]},
    scripts=["trezorctl"],
    install_requires=install_requires,
    extras_require={
        "hidapi": ["hidapi>=0.7.99.post20"],
        "ethereum": ["rlp>=0.4.4", "ethjsonrpc>=0.3.0"],
    },
    python_requires=">=3.5",
    include_package_data=True,
    zip_safe=False,
    classifiers=[
        "License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)",
        "Operating System :: POSIX :: Linux",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: MacOS :: MacOS X",
        "Programming Language :: Python :: 3 :: Only",
    ],
    cmdclass={"prebuild": PrebuildCommand},
)
