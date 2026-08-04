# Modular App Development

## App Metadata

Every modular app must declare its metadata in `Cargo.toml` under `[package.metadata.trezor]`:

```toml
[package.metadata.trezor]
id = "ethereum.trezor.com"
name = "Ethereum"
vendor = "SatoshiLabs"
stack-size = 16384
heap-size = 1024
app-ring = 0
curves = ["secp256k1"]
paths = [
    "m/44'/coin_type'/0'/0/account",
    "m/44'/coin_type'/account'/change/address_index/**",
    "m/44'/coin_type'/account'",
    "m/44'/coin_type'/0'/account",
    "m/45'/coin_type/account/change/address_index",
]
slip44-id = 60
```

| Field | Description |
|-------|-------------|
| `id` | Unique reverse-domain identifier of the app |
| `name` | Human-readable app name shown in the UI |
| `vendor` | App vendor name |
| `stack-size` | Stack memory allocated for the app in bytes |
| `heap-size` | Heap memory allocated for the app in bytes |
| `app-ring` | Privilege ring level; `0` is the most privileged |
| `curves` | List of elliptic curves the app is permitted to use |
| `paths` | Allowed BIP32 derivation path patterns (see below) |
| `slip44-id` | [SLIP-44](https://github.com/satoshilabs/slips/blob/master/slip-0044.md) coin type identifier |

### Derivation Path Patterns

The `paths` field restricts which BIP32 paths the app may derive keys for. The following patterns are commonly used:

| Pattern | Description |
|---------|-------------|
| `m/44'/coin_type'/0'/0/account` | BIP-44 for account-based currencies (e.g. ETH) |
| `m/44'/coin_type'/account'/change/address_index/**` | BIP-44 for UTXO-based currencies |
| `m/44'/coin_type'/account'` | SEP-0005 for non-UTXO currencies (Stellar, etc.) |
| `m/44'/coin_type'/0'/account` | SEP-0005 Ledger Live legacy path |
| `m/45'/coin_type/account/change/address_index` | CASA multisig path |

---

## App Entry Point

Every app must export an `app()` function as its entry point:

```rust
#[unsafe(no_mangle)]
pub fn app() -> Result<()> {
    loop {
        let message = CORE_SERVICE.receive(Timeout::max())?;
        match message.service().into() {
            CoreIpcService::WireStart => handle_wire_message(&message)?,
            _ => {
                error!(
                    "Invalid service invoked: {:?}, message id {:?}, data {:?}",
                    message.service(),
                    message.id(),
                    message.data()
                );
                return Err(Error::InvalidFunction)?;
            }
        };
    }
}
```

The function runs an infinite loop that drives the app's message handling:

1. **Wait** — `CORE_SERVICE.receive()` blocks until Trezor Core sends a message.
2. **Dispatch** — the message service field determines what to do:
   - `WireStart` — a new protobuf request has arrived from the host; `handle_wire_message()` is called to process it.
   - anything else — an unexpected service was invoked; the error is logged and `Error::InvalidFunction` is returned, terminating the app.

### Wire Message Handling

When a `WireStart` message is received, `handle_wire_message()` is responsible for:

1. **Deserializing** the incoming protobuf payload from the message data.
2. **Dispatching** to the appropriate handler function based on the message type.
3. **Responding** — the result is serialized and sent back to Core:
   - On success → response is sent via the `WireEnd` service.
   - On error → the error is sent via the `WireError` service.

```
Host  ──WireStart──►  app()
                        │
                   deserialize
                        │
                   handler fn
                        │
              ┌─────────┴─────────┐
           success             failure
              │                   │
         WireEnd            WireError
              │                   │
Host  ◄───────┴───────────────────┘
```

### Services

While handling a wire message, the app can call into other Core services via IPC:

| Service | Description |
|---------|-------------|
| `UI` | Display screens, request user confirmation, show progress |
| `Progress` | Report progress of long-running operations |
| `WireContinue` | Request additional data chunks from the host when the payload is too large to fit in a single message |
| `Crypto` | Seed-based cryptographic operations (key derivation, signing) |
| `CryptoDirect` | Cryptographic functions that do **not** access the seed (hashing, encoding, etc.) |

These calls are synchronous — the app blocks until Core responds.

---

## IPC Buffer Configuration

The IPC buffer must be large enough to hold the biggest message the app ever sends to Core. It is declared using the `static_service!` macro:

```rust
static_service!(CORE_SERVICE, <buffer_size>);
```

Where `<buffer_size>` is the size in bytes. Set it to cover the largest outgoing protobuf message (including any nested fields), otherwise serialization will fail at runtime.

> **Tip:** When in doubt, measure the serialized size of your largest response message and round up to the nearest power of two.


## App Lifecycle

The real entry point of every modular app is `applet_main`, provided by the SDK. The user-defined `app()` function is called only after the SDK has fully initialized the environment. The initialization sequence is strictly ordered — functionality is not available before its initialization step completes.

### Initialization Sequence

#### 1. API Version Check

The SDK verifies that the API version required by the app is available on the running firmware. If the version is not supported, the app crashes immediately. This check is handled automatically by `trezorlib` — no user code is needed.

> ⚠️ No SDK functionality is available before this point.

#### 2. IPC Buffer Initialization

The IPC buffer used for communication with Trezor Core is set up. Its size is configured via the `static_service!` macro and must be large enough to hold the largest message the app sends to Core.

> ⚠️ No communication with Core (UI, Crypto, WireContinue, etc.) is available before this point.

#### 3. Heap Initialization

The heap allocator is initialized with the memory region defined by `heap-size` in `Cargo.toml`. The default heap is 16 KiB.

> ⚠️ No allocated types (`Box`, `Vec`, `String`, etc.) can be used before this point.

#### 4. User App

The user-defined `app()` function is called. From this point, the full SDK is available.

### Termination

When `app()` returns:

- **`Ok(())`** — the app exits cleanly via `system_exit()`.
- **`Err(e)`** — the error type, code, and message are logged, and the app exits with `system_exit_error()`, reporting the failure to Core.

### Sequence Diagram

```
applet_main()
    │
    ├─ 1. init API version
    │       └─ incompatible → crash (handled by trezorlib)
    │
    ├─ 2. init IPC buffer (CORE_SERVICE)
    │       └─ no Core communication before this
    │
    ├─ 3. init heap (HEAP)
    │       └─ no alloc types before this
    │
    └─ 4. call app()
            │
            ├─ Ok(())  → system_exit()
            └─ Err(e)  → log error → system_exit_error()
