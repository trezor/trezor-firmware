# Logging in Modular Apps

This document covers the logging facilities available to modular apps built with the Trezor App SDK: the log macros themselves, how log levels are controlled at both build time and runtime, how log output is formatted in the emulator, and how to trace error origins in release builds.

## Log Macros

Four macros are available for logging at different severity levels:

- `debug!` — verbose diagnostic information
- `info!` — general informational messages
- `warn!` — non-fatal issues worth attention
- `error!` — logs an error message

All values passed to log macros must implement the `uDebug` trait. Note that some standard types require conversion before they can be logged — for example, `String` must be converted to `&str` via `.as_str()`.

```rust
use trezor_app_sdk::{error, warn, info, debug};

debug!("Processing item: {:?}", item);        // item: impl uDebug
info!("Application started");
warn!("Unexpected value: {:?}", value);        // value: impl uDebug
error!("Failed: {:?}", err);                   // err: impl uDebug

// String requires conversion to &str:
let msg: String = get_message();
info!("Message: {:?}", msg.as_str());

// Similarly for other non-uDebug types, convert to a supported form first
```

---

## Build-Time Filtering

To save memory, logs are filtered at compile time. Only logs at the enabled level and **above** are compiled into the binary — lower-level log calls are completely removed by the compiler, saving both code size and memory.

The log level is set via the `--log-level <level>` flag when building with `modular-xtask`:

```sh
modular-xtask build --log-level debug
modular-xtask build --log-level info
modular-xtask build --log-level warn
modular-xtask build --log-level build
```

This automatically enables the corresponding `feature_<level>` Cargo feature — no manual `Cargo.toml` changes are needed.

> **Note:** On hardware, memory is limited. Prefer higher log levels (e.g., `warning`) in production builds.

---

## Log Format in the Emulator

In the emulator, each log message is prefixed with a timestamp, the **crate name**, and the **relative path** to the module where it was emitted, followed by the severity level:

```sh
<timestamp> <crate>::<path/to/module> <LEVEL> <message>
```

For example:

```sh
5.248 apps.trezorapp.run ERR Failed to get public key bytes due to exception: format string needs more arguments
5.248 apps.trezorapp.run DBG Serializing crypto result
5.248 apps.trezorapp.run DBG Sending crypto result
5.249 tron ERR ApiError
```

Messages related to the modular app `apps.trezorapp.run` (core app services + modular app orchestration ), `<app_name>` (e.g. `tron`) or `trezor-app-sdk` for SDK-internal messages.

---

## Runtime Filtering

Even with a permissive build-time log level, many messages may arrive from Trezor Core. You can suppress unwanted output at runtime using:

```sh
trezorctl debug set-log-filter <filter>
```

### Filter Syntax

The filter string is a sequence of rules parsed left-to-right, separated by commas. Each rule has the form:

```sh
<op>[<level>]<module>[*]
```

| Part | Description |
| ------ | ------------- |
| `op` | `+` to include, `-` to exclude |
| `level` | Optional digit `1`–`4` → `ERR`/`WARN`/`INF`/`DBG`; defaults to `DBG` for `+`, `ERR` for `-` |
| `module` | Matched against the log source name; trailing `*` is a wildcard |

**Default behaviour:** if the filter is empty or starts with `-`, all sources are included initially. If it starts with `+`, all sources are excluded initially.

Rules are applied in order — later rules override earlier ones for matching sources.

### Examples

**Show only your app (all levels):**

```sh
trezorctl debug set-log-filter "+tron*,-*"
```

**Show only SDK logs (all levels):**

```sh
trezorctl debug set-log-filter "+trezor-app-sdk*,-*"
```

**Show only your app and SDK, suppress everything else:**

```sh
trezorctl debug set-log-filter "+tron*,+trezor-app-sdk*,-*"
```

**Your app at `DBG`, SDK at `WARN` and above, everything else off:**

```sh
trezorctl debug set-log-filter "+4tron*,+2trezor-app-sdk*,-*"
```

**Your app at `INFO` and above, SDK errors only, everything else off:**

```sh
trezorctl debug set-log-filter "+3tron*,+1trezor-app-sdk*,-*"
```

**Suppress only debug noise from core orchestration, keep everything else:**

```sh
trezorctl debug set-log-filter "-4apps.trezorapp.run"
```

---

## Catching Errors

In release builds, it is not straightforward to trace where an error originates. Two approaches are available:

### 1. Enable the `debug` Feature

Build with `--log-level debug` to compile in the debug feature. This enables two things:

- more verbose log output including file and line information
- the `ResultExt` trait functionality (see below)

Without the `debug` feature, `ResultExt` calls are compiled out entirely and have no effect.

### 2. Use the `ResultExt` Trait

When the `debug` feature is enabled, the `ResultExt` trait adds a `.c()` method on `Result` that wraps any error with its call-site location (relative file path + line number):

```rust
use sdk::ResultExt;

fn my_function() -> Result<(), Error> {
    some_operation().c()?;  // wraps error with file + line on failure
    Ok(())
}
```

When an error propagates up through `.c()?` calls, each call site is recorded as a `Error::Context` node, forming a chain. The full chain is printed when the error is logged at the top level:

```sh
Context Error at
Location: src/my_function.rs:10
Location: src/caller.rs:42
Caused by: DataError: invalid input
```

Without the `debug` feature, `.c()` is a no-op that simply returns `self` — the `Error::Context` variant does not exist at all and no location data is stored.
