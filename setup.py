from distribute_setup import use_setuptools
use_setuptools()

from setuptools import setup, find_packages
from os.path import dirname, join

here = dirname(__file__)
setup(
    name='python-trezor',
    version='0.5.0',
    author='Bitcoin TREZOR',
    author_email='info@bitcointrezor.com',
    description='Python library for handling TREZOR hardware bitcoin wallet',
    long_description=open(join(here, 'README.rst')).read(),
    packages=find_packages(),
    test_suite='tests',
    dependency_links=['https://github.com/trezor/python-mnemonic/archive/master.zip#egg=mnemonic-0.6'],
    install_requires=['ecdsa>=0.9', 'protobuf', 'mnemonic>=0.6', 'hidapi>=0.7.99'],
    include_package_data=True,
    zip_safe=False,
    classifiers=[
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Operating System :: POSIX :: Linux',
        'Operating System :: POSIX :: Windows',
    ],
)
