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

Python-trezor requires Python 3.3 or higher, and libusb 1.0. The easiest way to install it is with ``pip``.
The rest of this guide assumes you have a working ``pip``; if not, you can refer to
`this guide <https://packaging.python.org/tutorials/installing-packages/>`_.

Trezor T only
~~~~~~~~~~~~~

On a typical Linux / Mac / BSD system, you already have all you need. Install ``trezor`` with:

.. code::

  pip3 install --upgrade setuptools
  pip3 install trezor

On Windows, you also need to install `libusb <https://github.com/libusb/libusb/wiki/Windows>`_
and the appropriate `drivers <https://zadig.akeo.ie/>`_. This is, unfortunately, a topic bigger
than this README.

Trezor One support
~~~~~~~~~~~~~~~~~~

In addition to the above, you need to install development headers for HIDAPI.

On a Debian or Ubuntu based system, you can install these:

.. code::

  sudo apt-get install python3-dev python3-pip cython3 libusb-1.0-0-dev libudev-dev

When installing the `trezor` library, you need to specify that you want ``hidapi``:

.. code::

  pip3 install --upgrade setuptools
  pip3 install trezor[hidapi]

Ethereum support
~~~~~~~~~~~~~~~~

Ethereum requires additional python packages. Instead of ``pip3 install trezor``, specify
``pip3 install trezor[ethereum]``.

You can combine it with the above, to get both HIDAPI and Ethereum support:

.. code::

  pip3 install trezor[ethereum,hidapi]

FreeBSD
~~~~~~~

On FreeBSD you can install the packages:

.. code::

  pkg install security/py-trezor

or build via ports:

.. code::

  cd /usr/ports/security/py-trezor
  make install clean


Commandline client (trezorctl)
------------------------------

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


Contributing
------------

Python-trezor pulls coins info and protobuf messages from `trezor-common <https://github.com/trezor/trezor-common>`_ repository. If you are
developing new features for Trezor, you will want to start there. Once your changes are accepted to ``trezor-common``, you can make a PR
against this repository. Don't forget to update the submodule with:

.. code::

  git submodule update --init --remote

Then, rebuild the protobuf messages and get ``coins.json`` by running:

.. code::

  python3 setup.py prebuild

To get support for BTC-like coins, these steps are enough and no further changes to the library are necessary.
