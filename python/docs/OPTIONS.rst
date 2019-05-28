Commandline options for trezorctl
=================================

See `EXAMPLES.rst <EXAMPLES.rst>`_ for examples on how to use.

Use the following command to see all options:

.. code::

  trezorctl --help

.. code::

  Usage: trezorctl [OPTIONS] COMMAND [ARGS]...

  Options:
    -p, --path TEXT  Select device by specific path.
    -v, --verbose    Show communication messages.
    -j, --json       Print result as JSON object
    --help           Show this message and exit.

  Commands:
    backup-device                   Perform device seed backup.
    cardano-get-address             Get Cardano address.
    cardano-get-public-key          Get Cardano public key.
    cardano-sign-tx                 Sign Cardano transaction.
    change-pin                      Change new PIN or remove existing.
    clear-session                   Clear session (remove cached PIN, passphrase, etc.).
    cosi-commit                     Ask device to commit to CoSi signing.
    cosi-sign                       Ask device to sign using CoSi.
    decrypt-keyvalue                Decrypt value by given key and path.
    disable-passphrase              Disable passphrase.
    enable-passphrase               Enable passphrase.
    encrypt-keyvalue                Encrypt value by given key and path.
    ethereum-get-address            Get Ethereum address in hex encoding.
    ethereum-sign-message           Sign message with Ethereum address.
    ethereum-sign-tx                Sign (and optionally publish) Ethereum transaction.
    ethereum-sign-typed_data        Sign typed data (EIP-712) with Ethereum address.
    ethereum-verify-message         Verify message signed with Ethereum address.
    firmware-update                 Upload new firmware to device.
    get-address                     Get address for specified path.
    get-entropy                     Get example entropy.
    get-features                    Retrieve device features and settings.
    get-public-node                 Get public node of given path.
    lisk-get-address                Get Lisk address for specified path.
    lisk-get-public-key             Get Lisk public key for specified path.
    lisk-sign-message               Sign message with Lisk address.
    lisk-sign-tx                    Sign Lisk transaction.
    lisk-verify-message             Verify message signed with Lisk address.
    list                            List connected TREZOR devices.
    load-device                     Load custom configuration to the device.
    monero-get-address              Get Monero address for specified path.
    monero-get-watch-key            Get Monero watch key for specified path.
    nem-get-address                 Get NEM address for specified path.
    nem-sign-tx                     Sign (and optionally broadcast) NEM transaction.
    ontology-get-address            Get Ontology address for specified path.
    ontology-get-public-key         Get Ontology public key for specified path.
    ontology-sign-ont-id-add-attributes
                                    Sign Ontology ONT ID Attributes adding.
    ontology-sign-ont-id-register   Sign Ontology ONT ID Registration.
    ontology-sign-transfer          Sign Ontology transfer.
    ontology-sign-withdraw-ong      Sign Ontology withdraw Ong.
    ping                            Send ping message.
    recovery-device                 Start safe recovery workflow.
    reset-device                    Perform device setup and generate new seed.
    ripple-get-address              Get Ripple address
    ripple-sign-tx                  Sign Ripple transaction
    self-test                       Perform a self-test.
    set-auto-lock-delay             Set auto-lock delay (in seconds).
    set-flags                       Set device flags.
    set-homescreen                  Set new homescreen.
    set-label                       Set new device label.
    set-passphrase-source           Set passphrase source.
    set-u2f-counter                 Set U2F counter.
    sign-message                    Sign message using address of given path.
    sign-tx                         Sign transaction.
    stellar-get-address             Get Stellar public address
    stellar-sign-transaction        Sign a base64-encoded transaction envelope
    tezos-get-address               Get Tezos address for specified path.
    tezos-get-public-key            Get Tezos public key.
    tezos-sign-tx                   Sign Tezos transaction.
    verify-message                  Verify message.
    version                         Show version of trezorctl/trezorlib.
    wipe-device                     Reset device to factory defaults and remove all private data.
