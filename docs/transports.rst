Transport methods
------------------

Transports are ways in which your program can communicate with your TREZOR device.  This can be:

 - direct via US
 - indirect: through the TREZOR bridge or network
 - fake: for debugging purposes

Each transport method is represented as an instance of :doc:`the Transport class <transport>`.

The following transport methos are supported:

.. toctree::
   :maxdepth: 2

   transport_hid
   transport_bridge
   transport_fake
   transport_pipe
   transport_serial
   transport_socket