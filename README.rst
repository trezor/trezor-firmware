python-trezor
=============

.. image:: https://travis-ci.org/trezor/python-trezor.svg?branch=master
    :target: https://travis-ci.org/trezor/python-trezor

.. image:: https://badges.gitter.im/trezor/community.svg
    :target: https://gitter.im/trezor/community

Python library for communicating with TREZOR Hardware Wallet

See https://trezor.io for more information

Install
-------

(Run with sudo if not running in superuser mode under Linux)

.. code::

  pip install trezor

On Linux you might need to run these commands first:

.. code::

  sudo apt-get install python-dev cython libusb-1.0-0-dev libudev-dev git
  sudo pip install setuptools

Usage
-----

There is a command line tool called ``trezorctl`` which can perform various tasks. Use the following to learn about its commands:

.. code::

  trezorctl --help

or to learn options of a particular command:

.. code::

  trezorctl commands --help

To use the library in your application look at the following example.

Example
-------

also found in ``tools/helloworld.py``

.. code:: python

  #!/usr/bin/env python

  from trezorlib.client import TrezorClient
  from trezorlib.transport_hid import HidTransport

  def main():
      # List all connected TREZORs on USB
      devices = HidTransport.enumerate()

      # Check whether we found any
      if len(devices) == 0:
          print('No TREZOR found')
          return

      # Use first connected device
      transport = HidTransport(devices[0])

      # Creates object for manipulating TREZOR
      client = TrezorClient(transport)

      # Print out TREZOR's features and settings
      print(client.features)

      # Get the first address of first BIP44 account
      # (should be the same address as shown in wallet.trezor.io)
      bip32_path = client.expand_path("44'/0'/0'/0/0")
      address = client.get_address('Bitcoin', bip32_path)
      print('Bitcoin address:', address)

      client.close()

  if __name__ == '__main__':
      main()

PIN Entering
------------

When you are asked for PIN, you have to enter scrambled PIN. Follow the numbers shown on TREZOR display and enter the their positions using the numeric keyboard mapping:

=== === ===
 7   8   9
 4   5   6
 1   2   3
=== === ===

Example: your PIN is **1234** and TREZOR is displaying the following:

=== === ===
 2   8   3
 5   4   6
 7   9   1
=== === ===

You have to enter: **3795**
