python-trezor
=============

.. image:: https://travis-ci.org/trezor/python-trezor.svg?branch=master
    :target: https://travis-ci.org/trezor/python-trezor

.. image:: https://badges.gitter.im/trezor/community.svg
    :target: https://gitter.im/trezor/community

Client side implementation for TREZOR-compatible Bitcoin hardware wallets.

See http://bitcointrezor.com for more information.

Example
-------

also found in ``helloworld.py``

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
      # (should be the same address as shown in mytrezor.com)
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

Install
-------

(Run with sudo if not running in superuser mode)

.. code::

  pip install trezor

How to install from source (Windows)
------------------------------------
* Install Python 2.7 (http://python.org)
* Install Cython (Windows binaries on http://cython.org/#download)
* Install Microsoft Visual Studio 2008 Express
* Add "C:\\Program Files (x86)\\Microsoft Visual Studio 9.0" to system PATH
* Clone repository (using TortoiseGit) to local directory
* Run C:\\python27\\python.exe setup.py install (or develop)

How to install from source (Debian/Ubuntu)
------------------------------------------
* sudo apt-get install python-dev python-setuptools cython libusb-1.0-0-dev libudev-dev git
* git clone https://github.com/trezor/python-trezor.git
* cd python-trezor
* python setup.py install (or develop)
