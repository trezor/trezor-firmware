# Passphrase

As of 1.9.0 / 2.3.0 we have changed how [passphrase](https://wiki.trezor.io/Passphrase) is communicated between the host and the device. For migration information for existing Hosts communicating with Trezor please see this [document](passphrase-redesign-migration.md).

Passphrase is very tightly coupled with _sessions_. The reader is encouraged to read on that topic first in the [sessions.md](sessions.md) section.

## Scheme

As soon as Trezor needs the passphrase to do BIP-39/SLIP-39 derivations it prompts the user for passphrase.

```
GetAddress(...)
--------->          PassphraseRequest()
                       <---------
PassphraseAck
(str passphrase, bool on_device)
--------->          Address(...)
                       <---------
```

In the default Trezor setting, the passphrase is obtained from the Host. Trezor sends a PassphraseRequest message and awaits PassphraseAck as a response. This message contains field `passphrase` to transmit it or it has `on_device` boolean flag to indicate that the user wishes to enter the passphrase on Trezor instead. Setting both `passphrase` and `on_device` to true is forbidden.

Note that this has changed as of 2.3.0. In previous firmware versions the `on_device` flag was in the PassphraseRequest message, since this decision has been made on Trezor. We also had two additional messages PassphraseStateRequest and PassphraseStateAck which were removed.

## Example

On an initialized device with passphrase enabled a common communication starts like this:

```
Initialize()
--------->          Features(..., session_id)
                       <---------
GetAddress(...)
--------->          PassphraseRequest()
                       <---------
PassphraseAck(...)
--------->          Address(...)
                       <---------
```

The device requested the passphrase since the BIP-39/SLIP-39 seed is not yet cached. After this workflow the seed is cached and the passphrase will therefore never be requested again unless the session is cleared*.

Since we do not have sessions, the Host can not be sure that someone else has not used the device and applied another session id (e.g. changed the Passphrase). To work around this we send the session id again on every subsequent message. See more on that in [session.md]().

```
Initialize(session_id)
--------->          Features(..., session_id)
                       <---------
GetPublicKey(...)
--------->          PublicKey(...)
                       <---------
```

As long as the session_id in `Initialize` is the same as the one Trezor stores internally, Trezor guarantees the same passphrase is being used.

----

\* There is one exception and that is Cardano. Because Cardano has a different BIP-39/SLIP-39 derivation scheme for passphrase we can not use the cached seed. As a workaround we prompt for the passphrase again in such case and cache the cardano seed in the cardano app directly.

## Passphrase always on device

User might want to enforce the passphrase entry on the device every time without the hassle of instructing the Host to do so.

For such cases the user may apply the *Passphrase always on device* setting. As the name suggests, with this setting the passphrase is prompted on the device right away and no PassphraseRequest/PassphraseAck messages are exchanged. Note that the passphrase is prompted only once for given session id. If the user wishes to enter another passphrase they need to either send Initialize(session_id=None) or replug the device.
