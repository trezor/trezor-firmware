# Test Suite for Changed Files

This document describes the test files created for the changed files in this PR.

## Test Files Created

### 1. test_trezor.workflow.py
Tests for `core/src/trezor/workflow.py`

**Coverage:**
- `IdleTimer` class:
  - Initialization and state management
  - Setting, updating, and removing timeouts
  - Touch() method for rescheduling
  - Clear() method for cleanup
- `spawn()` function for workflow registration
- `close_others()` function for workflow exclusivity
- Default workflow management (`set_default`, `start_default`, `kill_default`)
- `ALLOW_WHILE_LOCKED` message type configuration
- `autolock_interrupts_workflow` flag behavior
- Edge cases: empty state, multiple workflows, state transitions

**Test count:** 25+ test cases

### 2. test_trezor.wire.context.py
Tests for `core/src/trezor/wire/context.py`

**Coverage:**
- `CURRENT_CONTEXT` global variable management
- `get_context()` function with and without context
- `call()` and `call_any()` functions
- `with_context()` generator for context management
- Cache operations (`cache_get`, `cache_set`, `cache_delete`, `cache_is_set`, `cache_get_bool`, `cache_set_bool`, `cache_get_int`, `cache_set_int`)
- `UnexpectedMessageException` class
- `try_get_ctx_ids()` function for THP contexts
- `NoWireContext` exception handling
- Context switching and lifecycle
- Sessionless cache flag handling

**Test count:** 35+ test cases

### 3. test_trezor.wire.thp.session_context.py
Tests for `core/src/trezor/wire/thp/session_context.py`

**Coverage:**
- `GenericSessionContext` initialization and methods
- `SeedlessSessionContext` with InvalidSessionError on cache access
- `SessionContext` initialization and cache access
- Session state management (`get_session_state`, `set_session_state`)
- Session ID conversion from bytes to int
- Channel ID validation
- `release()` method for cleanup
- `write()` method delegation to channel
- Edge cases: multi-byte session IDs, channel ID mismatches, state transitions

**Test count:** 20+ test cases

### 4. test_trezor.ui.layout.py
Tests for `core/src/trezor/ui/__init__.py`

**Coverage:**
- `Layout` class initialization and lifecycle
- `set_current_layout()` function with assertions
- Layout states (`is_ready`, `is_running`, `is_finished`, `is_layout_attached`)
- `stop()` method and cleanup
- `ProgressLayout` class for background progress indicators
- Button request handling (`put_button_request`)
- Repaint operations (`request_complete_repaint`, `repaint`)
- `should_resume` flag behavior
- Timer management
- Multiple layout lifecycle management

**Test count:** 25+ test cases

### 5. test_trezor.ui.layouts.common.py
Tests for `core/src/trezor/ui/layouts/common.py`

**Coverage:**
- `interact()` function with various parameters
- Result handling (CONFIRMED, CANCELLED, INFO)
- Exception raising behavior (`raise_on_cancel` parameter)
- `confirm_only` mode
- Custom exception types
- `raise_if_not_confirmed()` wrapper function
- `draw_simple()` function
- `with_info()` function for info screens
- `confirm_linear_flow()` function
- Button request types
- Edge cases: None br_name, different button request types

**Test count:** 20+ test cases

### 6. test_trezor.wire.codec.codec_context.py
Tests for `core/src/trezor/wire/codec/codec_context.py`

**Coverage:**
- `CodecContext` initialization with buffer provider
- Buffer management (`_get_buffer`, buffer reuse, buffer allocation)
- `write()` method with various message sizes
- Buffer reallocation for large messages
- Small message handling without buffer
- IOError for large messages without buffer
- `release()` method for session cleanup
- Cache property with active/inactive sessions
- Message encoding and sending
- Buffer persistence across operations
- Provider interaction

**Test count:** 20+ test cases

### 7. test_trezor.wire.protocol_common.py
Tests for `core/src/trezor/wire/protocol_common.py`

**Coverage:**
- `Message` class initialization
- Message with various data types (bytes, bytearray, memoryview)
- Message with edge case values (type 0, large data, empty data)
- `Context` class initialization
- Context with channel_id
- Custom message type enum names
- `release()` default implementation
- `WireError` exception class
- Edge cases: empty channel_id, multiple contexts, large payloads

**Test count:** 15+ test cases

## Running the Tests

### Prerequisites

The tests require the Trezor firmware emulator to be built. The tests are designed to run with MicroPython in the Trezor environment.

### Build the Emulator

```bash
cd core
# Follow the build instructions in core/README.md to build the Unix emulator
# This typically involves running make commands to build ../build/unix/trezor-emu-core
```

### Run All New Tests

```bash
cd core/tests
./run_tests.sh test_trezor.workflow.py \
               test_trezor.wire.context.py \
               test_trezor.wire.thp.session_context.py \
               test_trezor.ui.layout.py \
               test_trezor.ui.layouts.common.py \
               test_trezor.wire.codec.codec_context.py \
               test_trezor.wire.protocol_common.py
```

### Run Individual Test Files

```bash
cd core/tests
./run_tests.sh test_trezor.workflow.py
```

### Test Environment

- **MicroPython**: The tests run in MicroPython with Trezor-specific modules
- **Mock Objects**: The tests use mock objects from `mock.py` and `mock_wire_interface.py`
- **Test Framework**: Custom unittest framework in `unittest.py`

## Test Coverage Summary

Total test files: 7
Total test cases: 160+

### Key Areas Tested:

1. **Workflow Management**: Task spawning, idle timers, default workflows, message locking
2. **Wire Context**: Context management, cache operations, context switching
3. **THP Sessions**: Session contexts, state management, channel communication
4. **UI Layouts**: Layout lifecycle, button requests, progress indicators
5. **UI Interactions**: User interaction flows, confirmation patterns
6. **Codec Context**: Message encoding, buffer management, session handling
7. **Protocol Common**: Base classes, messages, error handling

### Test Patterns Used:

- **Unit Tests**: Isolated component testing with mocks
- **State Testing**: Verification of state transitions and lifecycle
- **Edge Cases**: Boundary values, error conditions, unusual inputs
- **Regression Tests**: Prevention of known issues
- **Integration Points**: Testing component interactions

## Notes

- Tests follow the existing test patterns in the codebase
- Mock objects are used extensively to isolate components
- Tests cover both happy paths and error conditions
- Edge cases and boundary conditions are thoroughly tested
- Tests verify both functionality and error handling

## Maintenance

When modifying the tested modules:
1. Run the corresponding test file to ensure no regressions
2. Add new tests for new functionality
3. Update tests if behavior changes intentionally
4. Keep test documentation in sync with code changes