#!/usr/bin/env python3
import os.path
import shutil
import subprocess
import sys
import tempfile

from setuptools import setup, Command, find_packages
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

CWD = os.path.dirname(os.path.realpath(__file__))
TREZOR_COMMON = os.path.join(CWD, 'vendor', 'trezor-common')


def read(name):
    filename = os.path.join(CWD, name)
    with open(filename, 'r') as f:
        return f.read()


class PrebuildCommand(Command):
    description = 'update vendored files (coins.json, protobuf messages)'
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        # check for existence of the submodule directory
        common_defs = os.path.join(TREZOR_COMMON, 'defs')
        if not os.path.exists(common_defs):
            raise Exception('trezor-common submodule seems to be missing.\n' +
                            'Use "git submodule update --init" to retrieve it.')

        # generate and copy coins.json to the tree
        with tempfile.TemporaryDirectory() as tmpdir:
            build_coins = os.path.join(TREZOR_COMMON, 'defs', 'coins', 'tools', 'build_coins.py')
            subprocess.check_call([sys.executable, build_coins], cwd=tmpdir)
            shutil.copy(os.path.join(tmpdir, 'coins.json'), os.path.join(CWD, 'trezorlib', 'coins.json'))

        # regenerate messages
        try:
            subprocess.check_call([os.path.join(CWD, 'tools', 'build_protobuf'), '--no-core'])
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
    long_description='{}\n\n{}'.format(
        read('README.md'),
        read('CHANGELOG.md'),
    ),
    long_description_content_type='text/markdown',
    url='https://github.com/trezor/python-trezor',
    packages=find_packages(),
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
