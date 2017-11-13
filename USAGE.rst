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

  trezorctl get_address -c Bitcoin -t address -n "m/44'/0'/0'/0/0"


Get first receiving address of first account for Bitcoin (SegWit-in-P2SH):

.. code::

  trezorctl get_address -c Bitcoin -t p2shsegwit -n "m/49'/0'/0'/0/0"


Get Legacy Bitcoin ``xpub`` (can be used to create a watch-only wallet):

.. code::

  trezorctl get_public_node -c Bitcoin -n "m/44'/0'/0'"


Litecoin
--------

Get first receiving address of first account for Litecoin (SegWit-in-P2SH):

.. code::

  trezorctl get_address -c Litecoin -t p2shsegwit -n "m/49'/2'/0'/0/0"
