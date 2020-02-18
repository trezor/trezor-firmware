
# Passphrase Redesign In 1.9.0 / 2.3.0

In versions 1.9.0 and 2.3.0 we have redesigned how the passphrase is
communicated between the Host and the Device. The new design is documented
thoroughly in [passphrase.md](passphrase.md) and this document should help
with the transition from the old design.

## Protobuf changes

The gist of the changes is:

- `PassphraseRequest.on_device` was deprecated.
- And the field was moved to PassphraseAck. The information whether the
passphrase is entered on the device is now decided on the Host.
- PassphraseStateRequest/PassphraseStateAck messages were deprecated.
- Features return a `session_id` (replacement for `state`).

The new messages can be found in trezor-common (TODO: link to commit in
trezor-common).

## Notable Changes

### Unified exchange for T1 and TT

The exchange is now the same for T1 and for TT. `PassphraseStateRequest` and
`PassphraseStateAck` are no longer used.

The protocol is described in [passphrase.md](passphrase.md). In a nutshell once
the Device sends `PassphraseRequest` the Host must respond with `PassphraseAck`
and choose between these two options:

- Either send `on_device = True` and omit the `passphrase` field. Then the user
is prompted on Trezor to enter the passphrase.
- Or omit `on_device` and send the passphrase string in `passphrase`. 

### Different "on device" workflow

As mentioned, the `on_device` field has been moved from `PassphraseRequest` to
`PassphraseAck` and the Host now decides where the passphrase should be
entered. For this to function properly the Host needs to provide two options:

1. Enter the passphrase directly.
2. Enter the passphrase on device.

In option (1) the passphrase is simply send in `PassphraseAck.passphrase`. In
option (2) the Host must send `PassphraseAck.on_device = True` and omit the
`passphrase` field. **Failing to provide such an option will make entering the
passphrase on the device impossible.** 

As of 1.9.0 / 2.3.0 you should decide whether the device is capable of
passphrase entry using the new capability "PassphraseEntry" as received in
Features. For older versions it is possible for model T but not for model One.

### Session id

We have replaced `state` with `session_id`. As mentioned you can obtain this
from Features. Session id is completely random and is not derived from
passphrase in any way.

You can and should use this session id to invoke Trezor's cache of the
passphrase. Simply store the session id and then send it in Initialize:
`Initialize(session_id=[your session id])`. In case the session is cached, the
passphrase will not be prompted again.

### Passphrase check

Some hosts were using the state to find out if the same passphrase is being
used as previously. Since the session id is now completely random and not
persistent over power-off this is not possible anymore.

If you wish to provide some sanity check that the user entered the same
passphrase as previously, simply remember an address. We recommend using
Testnet's address 44'/1'/0'/0/0. Then you store it and check if it equal
once the user entered theirs passphrase.

### Supporting older firmwares

With the new trezor-common code you should be able to support older firmwares as
well. T1 should work out of the box!

For TT, if the older firmware sends `PassphraseRequest.on_device` it is labeled
as deprecated `_on_device` in the new Protobuf. However, that does not prevent
you from using it:

- In case the value is set to True, respond with an empty `PassphraseAck`.
- In case the value is set to False, respond with `PassphraseAck` and set the
passphrase in `passphrase` field.

If you receive `PassphraseStateRequest`, now renamed to 
`Deprecated_PassphraseStateRequest` just respond with
`Deprecated_PassphraseStateAck`.

// TODO: describe the "state" in PassphraseState?
