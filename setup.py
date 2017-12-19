#!/usr/bin/env python
from setuptools import setup

install_requires = [
    'ecdsa>=0.9',
    'mnemonic>=0.17',
    'setuptools>=19.0',
    'requests>=2.4.0',
    'click>=6.2',
    'pyblake2>=0.9.3',
]

import sys
if '--disable-hidapi' in sys.argv:
    sys.argv.remove('--disable-hidapi')
else:
    install_requires.append('hidapi>=0.7.99.post20')

from trezorlib import __version__ as VERSION

setup(
    name='trezor',
    version=VERSION,
    author='TREZOR',
    author_email='info@trezor.io',
    description='Python library for communicating with TREZOR Hardware Wallet',
    url='https://github.com/trezor/python-trezor',
    packages=[
        'trezorlib',
        'trezorlib.messages',
        'trezorlib.qt',
        'trezorlib.tests.device_tests',
        'trezorlib.tests.unit_tests',
    ],
    scripts=['trezorctl'],
    install_requires=install_requires,
    include_package_data=True,
    zip_safe=False,
    classifiers=[
        'License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)',
        'Operating System :: POSIX :: Linux',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: MacOS :: MacOS X',
    ],
)
