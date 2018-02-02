python-trezor
=============

.. image:: https://travis-ci.org/trezor/python-trezor.svg?branch=master
    :target: https://travis-ci.org/trezor/python-trezor

.. image:: https://badges.gitter.im/trezor/community.svg
    :target: https://gitter.im/trezor/community

Python library and commandline client for communicating with TREZOR Hardware Wallet

See https://trezor.io for more information

Install
-------

Linux requirements:

.. code::

  sudo apt-get install python3-dev cython3 libusb-1.0-0-dev libudev-dev git

Linux & Mac Python requirements:

.. code::

  sudo -H pip3 install setuptools
  sudo -H pip3 install -r requirements.txt
  sudo -H pip3 install trezor

On FreeBSD you can install the packages:

.. code::

  pkg install security/py-trezor

or build via ports:

.. code::

  cd /usr/ports/security/py-trezor
  make install clean


Commandline client (trezorctl)
---------------------------

The included ``trezorctl`` python script can perform various tasks such as changing setting in the Trezor, signing transactions, retrieving account info and addresses. See the `docs/ <docs/>`_ sub folder for detailed examples and options.

NOTE: An older version of the ``trezorctl`` command is `available for Debian Stretch <https://packages.debian.org/en/stretch/python-trezor>`_ (and comes pre-installed on `Tails OS <https://tails.boum.org/>`_).


Python Library
--------------

You can use this python library to interact with a Bitcoin Trezor and use its capabilities in your application.
See examples here in the `tools/ <tools/>`_ sub folder.


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
