Examples demonstrating how to use trezorctl
===========================================

Show all available `options <OPTIONS.rst>`_:

.. code::

  $ trezorctl --help


Retrieve features, settings and coin types supported by your device:

.. code::

  $ trezorctl get-features


Bitcoin examples
----------------

Get first receiving address of first account for Bitcoin (Legacy / non-SegWit):

.. code::

  $ trezorctl btc get-address --script-type address --address m/44h/0h/0h/0/0

Get first receiving address of first account for Bitcoin (SegWit-in-P2SH):

.. code::

  $ trezorctl btc get-address --script-type p2shsegwit --address m/49h/0h/0h/0/0

Get first receiving address of first account for Bitcoin (Bech32 native SegWit P2WPKH):

.. code::

  trezorctl btc get-address --script-type segwit --address m/84h/0h/0h/0/0

Get Legacy Bitcoin ``xpub`` (can be used to create a watch-only wallet):

.. code::

  trezorctl btc get-public-node --address m/44h/0h/0h


Transaction signing
-------------------

``trezorctl`` supports offline signing of transactions in a `custom JSON format <transaction-format.md>`_.
If you have transaction data in file ``tx.json``, use the following call to get the signature:

.. code::

  $ trezorctl btc sign-tx tx.json
  Please confirm action on your Trezor device

  Signed transaction:
  02000000025a6bdf3ac73e3e7047380d484e2f7d58ea633a509b9a63fe95fab84d64(...)

A provided script can be used to sign transactions interactively. You will need the following pieces of info:

1) Transaction ID containing the Output we want to spend (aka ``prevhash`` or ``a5ea715a...d201e64e`` in example below).
2) Index number of the Output being spent from the above tx (aka ``previndex`` or ``0`` in example below).
3) BIP32 path to the Node which can spend the above UTXO (eg ``Bitcoin/0h/0/0`` for the first).
4) Destination address where you want to send funds (eg ``3M8XGFBKwkf7miBzpkU3x2DoWwAVrD1mhk`` below).
5) Amount to send in satoshis - ``91305`` in the example below (multiply BTC amount 0.00091305 by 100,000,000).
6) Expected fee (``0.00019695`` BTC in example below). Note: the miner receives all satoshis left unspent from a transaction.  If you want to receive some change, you need to send it to an address you own (otherwise it will go to miner).  Fee is not needed below, we just want it as a sanity check.

There are many ways to retrieve the info above: from a watch-only wallet in Bitcoin Core, https://coinb.in (`screenshot <sign_tx-coinb.in.png>`_) etc. The easiest way is using the Trezor Suite: https://suite.trezor.io

After authenticating, open the "Send" tab, fill-out all details, then open the "Show transaction details" menu to see the info needed above (`screenshot <sign_tx-trezor.io.png>`_).  Once you have the required details, you can then perform the transaction signing using ``trezorctl`` as shown in the example below:

.. code::

  $ python3 tools/build_tx.py | trezorctl btc sign-tx -

  Coin name [Bitcoin]: Bitcoin

  Previous output to spend (txid:vout) []: a5ea715aa99ca30516f3af6f622dfe7399d883d49ad74b1fe33fdf73d201e64e:0
  BIP-32 path to derive the key: Bitcoin/0h/0/0
  Prefilling input amount: 111000
  Sequence Number to use (RBF opt-in enabled by default) [4294967293]: 4294967293
  Input type (address, segwit, p2shsegwit) [address]:

  Previous output to spend (txid:vout) []:

  Output address (for non-change output) []: 3M8XGFBKwkf7miBzpkU3x2DoWwAVrD1mhk
  Amount to spend (satoshis): 91305

  Output address (for non-change output) []:
  BIP-32 path (for change output) []:
  Transaction version [2]:
  Transaction locktime [0]:
  Please confirm action on your Trezor device

  Signed Transaction:
  02000000014ee601d273df3fe31f4bd79ad483d89973fe2d626faff316(...)

The signed transaction text can then be inspected in Electrum (`screenshot <sign_tx-electrum2.png>`_), `coinb.in <https://coinb.in/?verify=01000000014ee601d273df3fe31f4bd79ad483d89973fe2d626faff31605a39ca95a71eaa5000000006a47304402206386a0ad0f0b196d375a0805eee2aebe4644032c2998aaf00e43ce68a293986702202ad25964844657e10130f81201b7d87eb8047cf0c09dfdcbbe68a1a732e80ded012103b375a0dd50c8dbc4a6156a55e31274ee0537191e1bc824a09278a220fafba2dbffffffff01a96401000000000017a914d53d47ccd1579b93c284e9caf3c81f3f417871698700000000#verify>`_ or another tool.  If all info is correct, you can then broadcast the tx to the Bitcoin network via the URL provided by ``trezorctl`` or Electrum (Tools → Load transaction → From text. Here is a `screenshot <sign_tx-electrum1.png>`_).  TIP: Electrum will only show the transaction fee if you previously imported the spending address (eg ``16ijWp48xn8hj6deD5ZHSJcgNjtYbpiki8`` from example tx above).  Also, the final tx size (and therefore satoshis / byte) might be slightly different than the estimate shown on suite.trezor.io

The final broadcast and mined transaction can be seen here: https://blockchain.info/tx/270684c14be85efec9adafa50339fd120658381ed2300b9207d0a0df2a5f0bf9


Litecoin examples
-----------------

Get first receiving address of first account for Litecoin (SegWit-in-P2SH):

.. code::

  $ trezorctl ltc get-address --script-type p2shsegwit --address m/49h/2h/0h/0/0

Get first receiving address of first account for Litecoin (Bech32 native SegWit P2WPKH):

.. code::

  $ trezorctl ltc get-address --script-type segwit --address m/84h/2h/0h/0/0

Notes
-----

1. Bech32 native SegWit encoded addresses require `Trezor Firmware v1.6.0 <https://github.com/trezor/trezor-mcu/releases>`_ or later.
