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

The log level is set via the `--log-level <level>` flag when building with `cargo app-tool`:

```sh
cargo app-tool build --log-level debug
cargo app-tool build --log-level info
cargo app-tool build --log-level warn
cargo app-tool build --log-level error
```

This automatically enables the corresponding `log_level_<level>` Cargo feature — no manual `Cargo.toml` changes are needed.

> **Note:** On hardware, memory is limited. Prefer higher log levels (e.g., `warn`) in production builds.

---

## Log Format in the Emulator

In the emulator, each log message is prefixed with a timestamp and a **source name**, followed by the severity level:

```sh
<timestamp> <source> <LEVEL> <message>
```

For example:

```sh
5.248 apps.extapp.crypto ERR Crypto operation 2 failed: Forbidden key path
5.249 extapp ERR DataError: received unexpected response message
```

Messages related to modular apps come from two kinds of sources:

- `apps.extapp.*` (e.g. `apps.extapp.run`, `apps.extapp.crypto`) — Core's side: app orchestration and the services Core provides to apps.
- `extapp` — everything the app logs, both its own messages and the SDK's. The source name is the same for every app for now; it doesn't carry the app's name or module path.

---

## Runtime Filtering

Even with a permissive build-time log level, many messages may arrive from Trezor Core. You can suppress unwanted output at runtime using:

```sh
trezorctl debug set-log-filter <filter>
```

### Filter Syntax

The filter string is a sequence of rules parsed left-to-right, separated by spaces. Each rule has the form:

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

App and SDK messages share the `extapp` source (see [Log Format in the Emulator](#log-format-in-the-emulator)), so they can only be filtered together. A filter starting with `+` already excludes everything it doesn't name, so there is no need to end it with `-*` — that would exclude everything again, since later rules override earlier ones.

**Show only app and SDK logs (all levels):**

```sh
trezorctl debug set-log-filter "+extapp"
```

**App and SDK at `INFO` and above, everything else off:**

```sh
trezorctl debug set-log-filter "+3extapp"
```

**App and SDK, plus Core's app services and orchestration, everything else off:**

```sh
trezorctl debug set-log-filter "+extapp +apps.extapp*"
```

**Suppress only debug noise from core orchestration, keep everything else:**

```sh
trezorctl debug set-log-filter "-4apps.extapp.run"
```

---

## Catching Errors

In release builds, it is not straightforward to trace where an error originates. Two approaches are available:

### 1. Enable the `debug` Feature

Build with `-d`/`--debug` to compile in the `debug` feature (see [Cargo Features](development.md#cargo-features)). This enables two things:

- more verbose log output including file and line information
- the `ResultExt` trait functionality (see below)

Without the `debug` feature, `ResultExt` calls are compiled out entirely and have no effect.

### 2. Use the `ResultExt` Trait

When the `debug` feature is enabled, the `ResultExt` trait adds a `.c()` method on `Result` that wraps any error with its call-site location (relative file path + line number):

```rust
use trezor_app_sdk::ResultExt;

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
