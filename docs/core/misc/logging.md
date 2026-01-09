# Logging for debugging purposes

Logging in the Trezor firmware is centralized so that all log records from all firmware components (bootloaders, prodtest, kernel, coreapp, Rust code, micropython code) are processed by a single routine. This ensures that the log format is always consistent:

```
{sec.msec} {module_name} {log_level} {message}
```

All log records are written to the debug console, which can be configured using the `DBG_CONSOLE` argument when building the firmware. If the debug console is disabled, all logging is disabled as well (i.e. in production builds).

Example:

```
make build_firmware TREZOR_MODEL=T3W1 DBG_CONSOLE=VCP
```

The following options are supported for the `DBG_CONSOLE` argument:

* VCP - outputs logs to the USB VCP console
* SWO - outputs logs to the SWO interface (requires STLink)
* SYSTEMVIEW - outputs logs using JLink and Segger SystemView

In the firmware emulator, all these logging backends are replaced with regular stderr output.

## Runtime filtering

Log records can be filtered at runtime using a simple filter. This filter can include or exclude messages from specific modules or severity levels.

In the firmware (or emulator), the filter can be configured using the `trezorctl debug set-log-filter` command:

Example:

```
trezorctl debug set-log-filter -- +1*+session*
```

(This filter keeps error messages from all modules and enables all messages for modules whose names start with "session".)

In prodtest (if logging is enabled), the filter can be configured using the `log-filter` command:

Example:

```
log-filter +1*+session
```

See `syslog_set_filter()` in `sys/syslog.h` for more details about the filter grammar.

## Logging from C code

Logging in C requires some setup, but the approach enables flexible compilation and reduces the resulting binary size.

To enable logging from C code, the `.c` file must:

1. Include the logging header.
2. Declare the logging module (the common module name).

Example in `my_module.c`:

```c
#include <sys/logging.h>

LOG_DECLARE(my_module)
```

In `syslog_config.h`, define the default logging level for the module if it is not defined yet:

```c
#ifndef SYSLOG_my_module_MAX_LOG_LEVEL
#define SYSLOG_my_module_MAX_LOG_LEVEL SYSLOG_DEFAULT_LOG_LEVEL
#endif
```

After this setup, you can use the printf-like logging macros `LOG_ERR`, `LOG_WARN`, `LOG_INF`, and `LOG_DBG`:

```c
LOG_ERR("operation failed (errcode=%d)", errcode);
```

Logging from C code is disabled by default. To enable logs, configure them manually in `syslog_config.h`. There are two options, which can also be used together:

1. Change the default logging level for all modules:

```c
#define SYSLOG_DEFAULT_LOG_LEVEL LOG_LEVEL_OFF
```

2. Change the logging level for a specific module:

```c
#define SYSLOG_xxx_module_MAX_LOG_LEVEL SYSLOG_DEFAULT_LOG_LEVEL
```

Instead of `LOG_LEVEL_OFF` or `SYSLOG_DEFAULT_LOG_LEVEL`, use one of `LOG_LEVEL_ERR`, `LOG_LEVEL_WARN`, `LOG_LEVEL_INF`, or `LOG_LEVEL_DBG`.

These settings determine which modules and log levels are compiled into the firmware binary.

## Notes on non-blocking behavior

When the logging backend is configured to use USB VCP (`DBG_CONSOLE=VCP`), all writes to the debug console are non-blocking by default. This may result in partial or lost messages, because the USB VCP internal buffer can fill quickly when the logging rate is high.

This default behavior can be overridden by setting the `BLOCK_ON_VCP` build argument. However, when logging from an interrupt context, writes to USB VCP remain non-blocking regardless of this setting.

When the logging backend is set to `SWO` or `SYSTEMVIEW`, writes are always blocking, ensuring that messages are never lost.
