python-trezor
=============

Client side implementation for Trezor-compatible Bitcoin hardware wallets.

See http://bitcointrezor.com for more information.

Example
-------

also found in ``helloworld.py``

.. code:: python

  #!/usr/bin/python

  from trezorlib.client import TrezorClient
  from trezorlib.transport_hid import HidTransport

  def main():
      # List all connected TREZORs on USB
      devices = HidTransport.enumerate()

      # Check whether we found any
      if len(devices) == 0:
          print 'No TREZOR found'
          return

      # Use first connected device
      transport = HidTransport(devices[0])

      # Creates object for manipulating TREZOR
      client = TrezorClient(transport)

      # Print out TREZOR's features and settings
      print client.features

      # Get the first address of first BIP44 account
      # (should be the same address as shown in mytrezor.com)
      bip32_path = client.expand_path("44'/0'/0'/0/0")
      address = client.get_address('Bitcoin', bip32_path)
      print 'Bitcoin address:', address

      client.close()

  if __name__ == '__main__':
      main()

How to install (Windows)
------------------------
* Install Python 2.7 (http://python.org)
* Install Cython (Windows binaries on http://cython.org/#download)
* Install Microsoft Visual Studio 2008 Express
* Add "C:\\Program Files (x86)\\Microsoft Visual Studio 9.0" to system PATH
* Clone repository (using TortoiseGit) to local directory
* Run C:\\python27\\python.exe setup.py install (or develop)

How to install (Debian-Ubuntu)
------------------------------
* sudo apt-get install python-dev python-setuptools cython libusb-1.0-0-dev libudev-dev
* git clone https://github.com/trezor/python-trezor.git
* cd python-trezor
* python setup.py install (or develop)
