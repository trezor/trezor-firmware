Commandline options for trezorctl
=================================

See `EXAMPLES.rst <EXAMPLES.rst>`_ for examples on how to use.

Use the following command to see all options:

.. code::

  trezorctl --help


.. code::

  Usage: trezorctl [OPTIONS] COMMAND [ARGS]...

  Options:
    -t, --transport [usb|udp|pipe|bridge]
                                    Select transport used for communication.
    -p, --path TEXT                 Select device by transport-specific path.
    -v, --verbose                   Show communication messages.
    -j, --json                      Print result as JSON object
    --help                          Show this message and exit.

  Commands:
    backup-device             Perform device seed backup.
    change-pin                Change new PIN or remove existing.
    clear-session             Clear session (remove cached PIN, passphrase,...
    cosi-commit               Ask device to commit to CoSi signing.
    cosi-sign                 Ask device to sign using CoSi.
    decrypt-keyvalue          Decrypt value by given key and path.
    decrypt-message           Decrypt message.
    disable-passphrase        Disable passphrase.
    enable-passphrase         Enable passphrase.
    encrypt-keyvalue          Encrypt value by given key and path.
    encrypt-message           Encrypt message.
    ethereum-get-address      Get Ethereum address in hex encoding.
    ethereum-sign-message     Sign message with Ethereum address.
    ethereum-sign-tx          Sign (and optionally publish) Ethereum...
    ethereum-verify-message   Verify message signed with Ethereum address.
    firmware-update           Upload new firmware to device (must be in...
    get-address               Get address for specified path.
    get-entropy               Get example entropy.
    get-features              Retrieve device features and settings.
    get-public-node           Get public node of given path.
    lisk-get-address          Get Lisk address for specified path.
    lisk-get-public-key       Get Lisk public key for specified path.
    lisk-sign-message         Sign message with Lisk address.
    lisk-sign-tx              Sign Lisk transaction.
    lisk-verify-message       Verify message signed with Lisk address.
    list                      List connected TREZOR devices.
    load-device               Load custom configuration to the device.
    nem-get-address           Get NEM address for specified path.
    nem-sign-tx               Sign (and optionally broadcast) NEM transaction.
    ping                      Send ping message.
    recovery-device           Start safe recovery workflow.
    reset-device              Perform device setup and generate new seed.
    self-test                 Perform a self-test.
    set-auto-lock-delay       Set auto-lock delay (in seconds).
    set-flags                 Set device flags.
    set-homescreen            Set new homescreen.
    set-label                 Set new device label.
    set-passphrase-source     Set passphrase source.
    set-u2f-counter           Set U2F counter.
    sign-message              Sign message using address of given path.
    sign-tx                   Sign transaction.
    stellar-get-address       Get Stellar public address
    stellar-get-public-key    Get Stellar public key
    stellar-sign-transaction  Sign a base64-encoded transaction envelope
    verify-message            Verify message.
    version                   Show version of trezorctl/trezorlib.
    wipe-device               Reset device to factory defaults and remove all...
