Usage
=====

Show help for all command:

.. code::

  trezorctl --help


Retrieve features, settings and coin types supported by your device:

.. code::

  trezorctl get_features


Bitcoin
-------

Get first receiving address of first account for Bitcoin (Legacy / non-SegWit):

.. code::

  trezorctl get_address --coin Bitcoin --script-type address --address "m/44'/0'/0'/0/0"


Get first receiving address of first account for Bitcoin (Bech32 native SegWit P2WPKH):

.. code::

  trezorctl get_address --coin Bitcoin --script-type segwit --address "m/49'/0'/0'/0/0"


Get first receiving address of first account for Bitcoin (SegWit-in-P2SH):

.. code::

  trezorctl get_address --coin Bitcoin --script-type p2shsegwit --address "m/49'/0'/0'/0/0"


Get Legacy Bitcoin ``xpub`` (can be used to create a watch-only wallet):

.. code::

  trezorctl get_public_node --coin Bitcoin --address "m/44'/0'/0'"


Litecoin
--------

Get first receiving address of first account for Litecoin (Bech32 native SegWit P2WPKH):

.. code::

  trezorctl get_address --coin Litecoin --script-type segwit --address "m/49'/2'/0'/0/0"


Get first receiving address of first account for Litecoin (SegWit-in-P2SH):

.. code::

  trezorctl get_address --coin Litecoin --script-type p2shsegwit --address "m/49'/2'/0'/0/0"


NOTES
-----

1. Bech32 native SegWit encoded addresses require Trezor Firmware v1.6.0 or later.
