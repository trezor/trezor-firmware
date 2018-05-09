#!/usr/bin/env python3
import os.path
import shutil
import subprocess

from setuptools import setup, Command
from setuptools.command.build_py import build_py
from setuptools.command.develop import develop

install_requires = [
    'setuptools>=19.0',
    'ecdsa>=0.9',
    'mnemonic>=0.17',
    'requests>=2.4.0',
    'click>=6.2',
    'pyblake2>=0.9.3',
    'libusb1>=1.6.4',
]

from trezorlib import __version__ as VERSION


class PrebuildCommand(Command):
    description = 'update vendored files (coins.json, protobuf messages)'
    user_options = []

    TREZOR_COMMON = os.path.join('vendor', 'trezor-common')

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        # check for existence of the submodule directory
        coins_json = os.path.join(self.TREZOR_COMMON, 'coins.json')
        if not os.path.exists(coins_json):
            raise Exception('trezor-common submodule seems to be missing.\n' +
                            'Use "git submodule update --init" to retrieve it.')

        # copy coins.json to the tree
        shutil.copy(coins_json, 'trezorlib')

        # regenerate messages
        try:
            subprocess.check_call(os.path.join(os.getcwd(), 'tools', 'build_protobuf'))
        except Exception as e:
            print(e)
            print("Generating protobuf failed. Maybe you don't have 'protoc', or maybe you are on Windows?")
            print("Using pre-generated files.")


def _patch_prebuild(cls):
    """Patch a setuptools command to depend on `prebuild`"""
    orig_run = cls.run

    def new_run(self):
        self.run_command('prebuild')
        orig_run(self)

    cls.run = new_run


_patch_prebuild(build_py)
_patch_prebuild(develop)


setup(
    name='trezor',
    version=VERSION,
    author='TREZOR',
    author_email='info@trezor.io',
    description='Python library for communicating with TREZOR Hardware Wallet',
    url='https://github.com/trezor/python-trezor',
    packages=[
        'trezorlib',
        'trezorlib.transport',
        'trezorlib.messages',
        'trezorlib.qt',
        'trezorlib.tests.device_tests',
        'trezorlib.tests.unit_tests',
    ],
    package_data={
        'trezorlib': ['coins.json'],
    },
    scripts=['trezorctl'],
    install_requires=install_requires,
    extras_require={
        ':python_version < "3.5"': ['typing>=3.0.0'],
        'hidapi': ['hidapi>=0.7.99.post20'],
        'ethereum': [
            'rlp>=0.4.4',
            'ethjsonrpc>=0.3.0',
        ],
    },
    python_requires='>=3.3',
    include_package_data=True,
    zip_safe=False,
    classifiers=[
        'License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)',
        'Operating System :: POSIX :: Linux',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: MacOS :: MacOS X',
        'Programming Language :: Python :: 3 :: Only',
    ],
    cmdclass={
        'prebuild': PrebuildCommand,
    },
)
