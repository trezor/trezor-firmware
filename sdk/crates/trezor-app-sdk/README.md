# Trezor App SDK

A unified SDK for developing Trezor applications in Rust.

## Features

- **Unified API**: All functionality in one crate
- **High-level UI**: Easy-to-use functions for user interaction
- **Structured Logging**: With compile-time filtering
- **Type-safe**: Leverages Rust's type system
- **No-std**: Works in embedded environments

## Architecture

```
trezor-app-sdk/
├── log          - Logging module with macros (error!, info!, etc.)
├── ui           - High-level UI functions (confirm_value, show_success, etc.)
└── low_level_api - Low-level system API (for advanced use, custom loggers)
```

## Quick Start

### 1. Add Dependency

```toml
[dependencies]
trezor-app-sdk = { path = "../trezor-app-sdk" }
```

### 2. Implement Logger

```rust
use trezor_app_sdk::{self as sdk, log::{Logger, Record, format_with_timestamp}};

struct AppLogger;

impl AppLogger {
    const fn new() -> Self { Self }
}

impl Logger for AppLogger {
    fn log(&self, record: &Record) {
        let timestamp = sdk::low_level_api::Api::systick_ms().unwrap_or(0);
        let formatted = format_with_timestamp(record, timestamp);
        let _ = sdk::low_level_api::Api::dbg_console_write(formatted.as_bytes());
    }
}

sdk::global_logger!(AppLogger);
```

### 3. Write Your App

```rust
use trezor_app_sdk::{self as sdk, ui, info, error};

#[no_mangle]
pub extern "C" fn applet_main(api_getter: sdk::TrezorApiGetter) -> i32 {
    // Initialize SDK
    if let Err(e) = sdk::init(api_getter) {
        return e.to_c_int();
    }

    info!("App started");

    // Use UI functions
    match ui::confirm_value("Title", "Confirm?") {
        Ok(true) => {
            info!("Confirmed");
            ui::show_success("Success", "Done!")?;
        }
        Ok(false) => info!("Cancelled"),
        Err(e) => {
            error!("Error: {:?}", e);
            return e.to_c_int();
        }
    }

    0
}
```

## Module Overview

### `log` Module

Provides structured logging with compile-time filtering:

```rust
use trezor_app_sdk::{error, warn, info, debug, trace};

error!("Critical: {}", msg);
warn!("Warning: {}", msg);
info!("Started");
debug!("Value: {:?}", val);
trace!("Entering function");
```

**Compile-time filtering:**
```bash
RUSTFLAGS='--cfg log_level="info"' cargo build  # Only error, warn, info
RUSTFLAGS='--cfg log_level="trace"' cargo build # All levels (default)
```

### `ui` Module

High-level UI functions:

- `confirm_value(title, content) -> Result<bool>` - Show confirmation dialog
- `confirm_properties(title, props) -> Result<bool>` - Confirm key-value list
- `show_warning(title, content) -> Result<()>` - Display warning
- `show_success(title, content) -> Result<()>` - Display success message
- `request_string(prompt) -> Result<String>` - Get string input
- `request_number(title, content, init, min, max) -> Result<u32>` - Get number
- `sleep(ms) -> Result<()>` - Sleep for milliseconds
- `request_finish() -> Result<bool>` - Signal completion

### `low_level_api` Module

Direct access to system functions. Use only for:
- Implementing custom loggers
- Advanced IPC operations
- System-level operations

**Available through `sdk::low_level_api::Api`:**
- `systick_ms()` - Get system time
- `dbg_console_write(data)` - Write to debug console
- `system_exit(code)` - Exit with code
- `ipc_*` functions - IPC operations

## Migration from Old Crates

### From `trezor-log` + `trezor-api` + `trezor-ui-api`

**Before:**
```rust
use trezor_log::{error, info};
use trezor_api::{Api, ApiWrapper};
use trezor_ui_api::confirm_value;
```

**After:**
```rust
use trezor_app_sdk::{self as sdk, ui, error, info};
// Use: sdk::init(), ui::confirm_value(), error!(), info!()
```

## Examples

See `example-app/` for a complete working example.

## Build Configuration

### Log Levels

```bash
# Production (errors only)
RUSTFLAGS='--cfg log_level="error"' cargo build --release

# Development (all logs)
RUSTFLAGS='--cfg log_level="trace"' cargo build
```

### Optimization

```toml
[profile.release]
opt-level = "z"  # Optimize for size
lto = true       # Link-time optimization
panic = "abort"  # Smaller panic handler
```

## Design Philosophy

1. **Single Import**: One SDK import instead of multiple crates
2. **Progressive Disclosure**: High-level API by default, low-level available
3. **Type Safety**: Compile-time checks where possible
4. **Zero Cost**: No runtime overhead for unused features
5. **Embedded-First**: No-std, minimal dependencies

## License

See parent LICENSE
