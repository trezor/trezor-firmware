# Passphrase Redesign In 1.9.0 / 2.3.0

On the T1, passphrase must be entered on the host PC and sent to Trezor. On the TT, the
user can choose whether to enter the passphrase on host or on Trezor's touch screen.

In versions 1.9.0 and 2.3.0 we have redesigned how the passphrase is
communicated between the Host and the Device. The new design is documented
thoroughly in [passphrase.md](passphrase.md) and this document should help
with the transition from the old design.

## New features

* Passphrase flow is now identical for T1 and TT.
* By keeping track of _sessions_, it is possible to avoid having to send passphrase repeatedly.
* The choice between entering on Host or Device for TT has been moved from Device to Host.
* Multiple passphrases are cached simultaneously.

## Backwards compatibility

T1 1.9.0 is fully backwards-compatible and works with existing Host code.

TT 2.3.0 communicating with old Host software degrades to T1-level features: entering
passphrase on device will not be available, and on-device passphrase caching via the
`state` field will not be available.

As a workaround, it is possible to use the "passphrase always on device" feature on the
new TT firmware. When enabled, the passphrase flow is completely hidden from the Host
software, and the Device itself prompts the user to enter the passphrase.

## Implementation guide

### Protobuf changes

Protobuf has built-in backwards compatibility mechanisms, so a conforming implementation
should continue to work with old protobuf definitions.

To restore support for TT on-device passphrase entry, and to make use of the new
features, you will need to update to newer protobuf definitions from `trezor-common`
(TODO: link to commit in trezor-common).

The gist of the changes is:

- `PassphraseRequest.on_device` was deprecated, and renamed to `_on_device`. New Devices
  will never send this field.
- Corresponding field `PassphraseAck.on_device` was added.
- `PassphraseAck.state` was deprecated, and renamed to `_state`. It is retained for
  code compatibility, but the field should never be set.
- `PassphraseStateRequest`/`PassphraseStateAck` messages were deprecated, and renamed
  with a `Deprecated_` prefix. New Devices will not send or accept these messages.
- `Initialize.state` was renamed to `Initialize.session_id`.
- Corresponding field `Features.session_id` was added. New Devices will always send this
  field in response to `Initialize` call.
- A new value `Capability_PassphraseEntry` was added to the `Features.Capability`
  enum. This capability will be sent from a Device that supports on-device passphrase
  entry (currently only TT).

### Restoring on-device entry for TT

The Host software reacts to a `PassphraseRequest` message by prompting the user for a
passphrase and sending it in the `PassphraseAck.passphrase` field.

A new UI element should be added: when the passphrase prompt is displayed on Host, there
should be an option to "enter passphrase on device". When the user selects this option,
the Host must send a `PassphraseAck(passphrase=null, on_device=true)`.

The "enter passphrase on device" option should be displayed when `Features.capabilities`
contain the `Capability_PassphraseEntry` value, regardless of reported Trezor version or
model. Firmwares older than 2.3.0 or 1.9.0 never set this value, so this ensures
forwards and backwards compatibility.

### Cross-version compatibility for TT

TT version \< 2.3.0 will send `PassphraseRequest(_on_device=true)` if the user selected
on-device entry. Neither T1 nor TT >= 2.3.0 will ever set this field to true.

If the Host receives `PassphraseRequest(_on_device=true)`, it should immediately respond
with `PassphraseAck()` with no fields set.

TT version \< 2.3.0 will send `Deprecated_PassphraseStateRequest(state=[bytes])` after
receiving `PassphraseAck`. The Host should immediately respond with
`Deprecated_PassphraseStateAck()` with no fields set. If the Host does session
management, it should store the value of `state` as the session ID.

### Triggering passphrase prompt

Use `GetAddress(coin_name="Testnet", address_n=[44'/1'/0'/0/0])` (the first address of
the first account of Testnet) to ensure that the Device asks for a passphrase if
needed, and caches it for future use.

### Validating passphrases

You can store the result of the above call, and in the future, compare it to a newly
received address. This is a good way to check if the user is using the same passphrase
as last time.

Do not store user-entered passphrases for the purpose of validation, even in hashed,
encrypted, or otherwise obfuscated format.

### Session support

A call to `Initialize` can include a `session_id` field. When starting a new user
session, this field should be left empty.

The response `Features` message will always include a `session_id` field. The value of
this field should be stored. When calling `Initialize` again, the stored value should
be sent as `session_id`. If the received `Features.session_id` is the same, it means
that session was resumed successfully and the user will not be prompted for passphrase.

```
--> Initialize()
<-- Features(session_id=0xABCDEF, ...)

--> Initialize(session_id=0xABCDEF)
<-- Features(session_id=0xABCDEF)
# (session resumed successfully)

--> Initialize(session_id=0xABCDEF)
<-- Features(session_id=0x123456)
# (session was not resumed, user will be prompted for passphrase again)
```

Session support is identical on T1 and TT, and both models support multiple sessions,
i.e., it is possible to seamlessly switch between using multiple passphrases.

### Cross-version compatible algorithm summary

The following algorithm will ensure that your Host application works properly with
both T1 and TT with both older and newer firmwares.

1. If you have a session ID stored, call `Initialize(session_id=stored_session_id)`
2. Check the value of `Features.session_id`. If it is identical to `stored_session_id`,
   the session was resumed and user will not need to be prompted for a passphrase.
   1. If `Features.session_id` is not set, you are communicating with an older Device.
      Do not store the null value as session ID.
   2. Otherwise store the value as `stored_session_id`.
3. When you receive a `PassphraseRequest(_on_device=true)`, respond with
   `PassphraseAck()` with no fields set.
4. When you receive a `PassphraseRequest`, prompt the user for passphrase.
   1. If `Features.capabilities` contains value `Capability_PassphraseEntry`, display a
      UI element that allows the user to enter passphrase on-device.
   2. If the user chooses this option, send `PassphraseAck(passphrase=null, on_device=true)`
   3. If the user enters the passphrase in your application, send
      `PassphraseAck(passphrase="user entered passphrase", on_device=false)`
5. When you receive a `Deprecated_PassphraseStateRequest(state=...)`, store the value
   of `state` as `stored_session_id`, and respond with `Deprecated_PassphraseStateAck`
   with no fields set.

Note: up to 64 bytes may be required to store the session ID. Firmwares < 2.3.0 use a 
64-byte value, newer firmwares use a 32-byte value.
