#!/usr/bin/env python
from setuptools import setup

install_requires = ['ecdsa>=0.9', 'protobuf>=2.6.1', 'mnemonic>=0.16', 'setuptools>=19.0']

import sys
if '--disable-hidapi' in sys.argv:
    sys.argv.remove('--disable-hidapi')
else:
    install_requires.append('hidapi>=0.7.99')

setup(
    name='trezor',
    version='0.7.10',
    author='TREZOR',
    author_email='info@trezor.io',
    description='Python library for communicating with TREZOR Hardware Wallet',
    url='https://github.com/trezor/python-trezor',
    py_modules=[
        'trezorlib.ckd_public',
        'trezorlib.client',
        'trezorlib.debuglink',
        'trezorlib.mapping',
        'trezorlib.messages_pb2',
        'trezorlib.protobuf_json',
        'trezorlib.qt.pinmatrix',
        'trezorlib.tools',
        'trezorlib.transport',
        'trezorlib.transport_bridge',
        'trezorlib.transport_hid',
        'trezorlib.transport_pipe',
        'trezorlib.transport_udp',
        'trezorlib.tx_api',
        'trezorlib.types_pb2',
    ],
    scripts = ['trezorctl'],
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
