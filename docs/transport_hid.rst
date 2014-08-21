Transport via USB HID
--------------

To get a list of TREZORs that are currently plugged into our computer, we use the enumerate method.

.. code-block:: python

 import trezorlib.transport_hid
 list_of_trezor_devices = trezorlib.transport_hid.enumerate()

We can now interact with our TREZORs by creating a :doc:`TrezorClient <client>` object.

.. automodule:: trezorlib.transport_hid
  :members:
  :undoc-members: