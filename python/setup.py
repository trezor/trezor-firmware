#!/usr/bin/env python3

# This file is part of the Trezor project.
#
# Copyright (C) 2012-2022 SatoshiLabs and contributors
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3
# as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the License along with this library.
# If not, see <https://www.gnu.org/licenses/lgpl-3.0.html>.

import re
from pathlib import Path

from setuptools import find_packages, setup

CWD = Path(__file__).resolve().parent

install_requires = (CWD / "requirements.txt").read_text().splitlines()

extras_require = {
    "hidapi": ["hidapi>=0.7.99.post20"],
    "ethereum": ["rlp>=1.1.0 ; python_version<'3.7'", "web3>=5"],
    "qt-widgets": ["PyQt5"],
    "extra": ["Pillow"],
    "stellar": ["stellar-sdk>=6"],
}

extras_require["full"] = sum(extras_require.values(), [])


def find_version():
    version_file = (CWD / "src" / "trezorlib" / "__init__.py").read_text()
    version_match = re.search(r"^__version__ = \"(.*)\"$", version_file, re.M)
    if version_match:
        return version_match.group(1)
    else:
        raise RuntimeError("Version string not found")


setup(
    name="trezor",
    version=find_version(),
    author="Trezor",
    author_email="info@trezor.io",
    license="LGPLv3",
    description="Python library for communicating with Trezor Hardware Wallet",
    long_description=(CWD / "README.md").read_text()
    + "\n\n"
    + (CWD / "CHANGELOG.md").read_text(),
    long_description_content_type="text/markdown",
    url="https://github.com/trezor/trezor-firmware/tree/master/python",
    package_data={"trezorlib": ["py.typed"]},
    packages=find_packages("src"),
    package_dir={"": "src"},
    entry_points={"console_scripts": ["trezorctl=trezorlib.cli.trezorctl:cli"]},
    install_requires=install_requires,
    extras_require=extras_require,
    python_requires=">=3.6",
    include_package_data=True,
    zip_safe=False,
    classifiers=[
        "License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)",
        "Operating System :: POSIX :: Linux",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: MacOS :: MacOS X",
        "Programming Language :: Python :: 3 :: Only",
    ],
)
