# Trezor Protocol

## version 1

Messages are sent in packets of 64 bytes.

First packet has the following structure:

| offset | length | type        | contents                                                                              |
|--------|--------|-------------|---------------------------------------------------------------------------------------|
|      0 |      3 | char[3]     | '?##' magic constant                                                                  |
|      3 |      2 | BE uint16_t | numerical [message type](messages.proto#L76)                                          |
|      5 |      4 | BE uint32_t | message size                                                                          |
|      9 |     55 | uint8_t[55] | first 55 bytes of message encoded in Protocol Buffers (padded with zeroes if shorter) |

Following packets has the following structure:

| offset | length | type        | contents                                                                               |
|--------|--------|-------------|----------------------------------------------------------------------------------------|
|      0 |      1 | char[1]     | '?' magic constant                                                                     |
|      1 |     63 | uint8_t[63] | following bytes of message encoded in Protocol Buffers (padded with zeroes if shorter) |

## Adding new message

To add new message to Trezor protocol follow these steps:
1. Reconsider if there isn't already a message, that would suit your needs.
2. Choose the right place (file) to put new message:
   - [`messages.proto`](messages.proto) are for management of the messages itself (wire type to message type mapping and etc.)
   - [`messages-common.proto`](messages-common.proto) are for common messages
   - all other files have a suffix `messages-SUFFIX.proto`, where suffix describes specific use case of messages contained within the file
3. Add new message and comment it properly following our [Messages naming and documenting conventions](#messages-naming-and-documenting-conventions).
4. If message is not embedded in another message, it has to have a wire type number
   assigned. This number is used to map between Trezor wire identifier (uint) and a
   protobuf message. Mapping is defined in [`messages.proto`](messages.proto#L76).

Wire identifiers are organized in logical blocks with 100 numbers per block. If you are
extending an existing application (e.g., Ethereum, Monero, Webauthn, etc.), pick the
lowest free number in the block of your application. If you are adding a new
application, pick the lowest unused block and use zero in that block.

## Messages naming and documenting conventions
Message names must:
- be as self explanatory as possible
- have `Ack` suffix if the message is a received message (send from host to device) and serves as a response to some request made by device before
(e.g. initial messages from host to device doesn't have to have this suffix)

Documenting/commenting the messages is mandatory. Please use the following template:
```protobuf
/**
 * MSG_TYPE: Description of the message
 * MSG_FLOW_TAG
 * MSG_FLOW_TAG
 * ...
 */
```
where:
- `MSG_TYPE` is used to describe the purpose of the message and its type. Possible values are:
  - `Request` for inbound messages (coming to the device (Trezor))
  - `Response` for outbound messages (coming out from the device)
  - in case that the message is embedded in another message we don't state the message type
- `MSG_FLOW_TAG` denotes the flow of the messages in a session (use case). Possible tags are:
  - `@start` means that this message is first
  - `@end` means that this message is last
  - `@next` denotes messages that could follow after this message
  - `@embed` denotes messages that are embedded into other message(s)
  - `@auxstart` - denotes message for sub-flow start; this message might appear at any time
during any other flow. When the corresponding @auxend message is processed, the original
flow resumes.
  - `@auxend` - see `@auxstart`

Messages flow is checked at the compile time.

Using the template and the rules we can create for example this messages:
```protobuf
/**
 * Request: Ask device to sign transaction
 * @start
 * @next TxRequest
 * @next Failure
 */
```
```protobuf
/**
 * Structure representing BIP32 (hierarchical deterministic) node
 * Used for imports of private key into the device and exporting public key out of device
 * @embed
 */
```
