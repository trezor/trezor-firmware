Usage
=====

Get first receiving address of first account for Legacy (non-SegWit) Bitcoin:

.. code::

  trezorctl get_address -c Bitcoin -t address -n "m/44'/0'/0'/0/0"

Get first receiving address of first account for SegWit-in-P2SH for Litecoin:

.. code::

  trezorctl get_address -c Litecoin -t p2shsegwit -n "m/49'/2'/0'/0/0"
