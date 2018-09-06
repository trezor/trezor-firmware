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
    backup_device            Perform device seed backup.
    change_pin               Change new PIN or remove existing.
    clear_session            Clear session (remove cached PIN, passphrase,...
    cosi_commit              Ask device to commit to CoSi signing.
    cosi_sign                Ask device to sign using CoSi.
    decrypt_keyvalue         Decrypt value by given key and path.
    decrypt_message          Decrypt message.
    disable_passphrase       Disable passphrase.
    enable_passphrase        Enable passphrase.
    encrypt_keyvalue         Encrypt value by given key and path.
    encrypt_message          Encrypt message.
    ethereum_get_address     Get Ethereum address in hex encoding.
    ethereum_sign_message    Sign message with Ethereum address.
    ethereum_sign_tx         Sign (and optionally publish) Ethereum...
    ethereum_verify_message  Verify message signed with Ethereum address.
    firmware_update          Upload new firmware to device (must be in...
    get_address              Get address for specified path.
    get_entropy              Get example entropy.
    get_features             Retrieve device features and settings.
    get_public_node          Get public node of given path.
    list                     List connected TREZOR devices.
    list_coins               List all supported coin types by the device.
    load_device              Load custom configuration to the device.
    nem_get_address          Get NEM address for specified path.
    nem_sign_tx              Sign (and optionally broadcast) NEM...
    ontology_get_address     Get Ontology address for specified path.
    ontology_get_public_key  Get Ontology public key for specified path.
    ontology_sign_transfer   Sign Ontology Transfer...
    ontology_sign_withdraw   Sign Ontology Withdraw Ong...
    ontology_sign_register   Sign Ontology ONT ID Registration...
    ontology_sign_add_attr   Sign Ontology ONT ID Attributes adding...
    ping                     Send ping message.
    recovery_device          Start safe recovery workflow.
    reset_device             Perform device setup and generate new seed.
    self_test                Perform a self-test.
    set_flags                Set device flags.
    set_homescreen           Set new homescreen.
    set_label                Set new device label.
    set_u2f_counter          Set U2F counter.
    sign_message             Sign message using address of given path.
    sign_tx                  Sign transaction.
    verify_message           Verify message.
    version                  Show version of trezorctl/trezorlib.
    wipe_device              Reset device to factory defaults and remove...
