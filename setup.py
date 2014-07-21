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
        'trezorlib.transport_fake',
        'trezorlib.transport_hid',
        'trezorlib.transport_pipe',
        'trezorlib.transport_serial',
        'trezorlib.transport_socket',
        'trezorlib.tx_api',
        'trezorlib.types_pb2',
    ],
    test_suite='tests',
    dependency_links=['https://github.com/trezor/python-mnemonic/archive/master.zip#egg=mnemonic-0.8'],
    install_requires=['ecdsa>=0.9', 'protobuf', 'mnemonic>=0.8', 'hidapi>=0.7.99'],
    include_package_data=True,
    zip_safe=False,
    classifiers=[
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Operating System :: POSIX :: Linux',
        'Operating System :: POSIX :: Windows',
    ],
)
