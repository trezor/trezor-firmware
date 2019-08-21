#!/usr/bin/env python3
import os.path
import re
from distutils.errors import DistutilsError

from setuptools import Command, find_packages, setup

install_requires = [
    "setuptools>=19.0",
    "ecdsa>=0.9",
    "mnemonic>=0.17",
    "shamir-mnemonic>=0.1.0",
    "requests>=2.4.0",
    "click>=7,<8",
    "pyblake2>=0.9.3",
    "libusb1>=1.6.4",
    "construct>=2.9",
    "typing_extensions>=3.6",
]

CWD = os.path.dirname(os.path.realpath(__file__))


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


class PrebuildCommand(Command):
    description = "Deprecated. Run 'make gen' instead."
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        raise DistutilsError(self.description)


setup(
    name="trezor",
    version=find_version(),
    author="Trezor",
    author_email="info@trezor.io",
    license="LGPLv3",
    description="Python library for communicating with Trezor Hardware Wallet",
    long_description="{}\n\n{}".format(read("README.md"), read("CHANGELOG.md")),
    long_description_content_type="text/markdown",
    url="https://github.com/trezor/python-trezor",
    packages=find_packages(),
    package_data={"trezorlib": ["coins.json"]},
    scripts=["trezorctl"],
    install_requires=install_requires,
    extras_require={
        "hidapi": ["hidapi>=0.7.99.post20"],
        "ethereum": ["rlp>=1.1.0", "web3>=4.8"],
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
