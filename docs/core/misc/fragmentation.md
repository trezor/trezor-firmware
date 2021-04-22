# Memory fragmentation management

Trezor-core memory is managed by a mark-and-sweep garbage collector. Throughout the
run-time of the firmware, the memory space gets increasingly fragmented as the GC sweep
is initiated at arbitrary points.

To combat fragmentation, we attempt to thoroughly clear the memory space after finishing
every workflow, and keep only a limited set of modules alive at all times. These must
take care to not hold external references.

## Always active modules

The following modules are kept loaded at all times:

* `trezor`
* `trezor.utils`
* `storage`
* `storage.common`
* `storage.cache`
* `storage.device`
* `storage.fido2`
* `trezor.pin` - held alive because the function `show_pin_timeout` is registered as a
  callback for `trezorconfig` and storage unlock operations
* `usb`

The above modules are only allowed to import C modules (`trezorconfig`, `trezorutils`,
`trezorcrypto`, etc.) or each other. We currently do not have any automation to enforce
this, so please be careful when editing them.

## Presizing

To save storage, Micropython only preallocates 1 slot in a module dict. Most of our
modules use more slots than that. This means that the dict is reallocated, possibly
several times. This is inconvenient at most times, but especially undesirable when it
would happen to an always-active module at some point at run-time. The allocator would
put the newly reallocated dict somewhere in the middle of the GC arena, and it would
stay there.

This does happen in practice: e.g., when you import `trezor.strings`, a new reference
`strings` is inserted into the `trezor` module.

For this reason, we call `utils.presize_module` on `trezor` and `storage` at first
import time. The sizes are determined empirically and it might be necessary to raise
them in the future.

The backing storage for `sys.modules` can also be reallocated at run-time. We configure
Micropython to preallocate 160 slots in `mpconfigport.h` variable
`MICROPY_LOADED_MODULES_DICT_SIZE`. This is asserted at the end of unimport in
`trezor.utils`, so if we ever need more modules than that, the test suite _should_ catch
it.

## Top-level and function-local imports

In order to keep the imported image size in check, in certain places we avoid importing
something at top-level, and instead import it in a function which actually needs the
functionality. That way the module can be imported without immediately pulling in all of
its possible dependencies.

The following imports `trezor.ui` at import time - when importing `module`, `trezor.ui`
is always imported, regardless of whether anyone calls the function `draw_foo`:
```
# module.py
import trezor.ui

def draw_foo():
    trezor.ui.display.draw_text("Foo")
```

The following defers the import until the function is called:
```
# module.py

def draw_foo():
    import trezor.ui

    trezor.ui.display.draw_text("Foo")
```

The general rules of thumb are as follows:

### C modules can always be imported.

These do not take any space in RAM.

### Always-active modules can always be imported.

They are always active, so we do not need to worry about allocating.

### In `apps.*`, we prefer clarity over optimization.

It might still be useful to, e.g., avoid importing `trezor.ui.layouts` for operations
that are sometimes silent, but it is not too important. All of the application code is
scrubbed from memory when the workflow exits.

### In system modules, we are extra careful.

This means `apps.base`, `apps.common`, and everything outside the `apps` namespace.

A module should only import on top-level if the import is either:
* C module or an always active module,
* a module that is expected to already be imported when this module is loaded
  (this is often the case in `apps.common` -- e.g., `trezor.workflow` is not always active, but is presumed active as soon as `session` is up),
* small module without further dependencies,
* something without which the whole module doesn't make sense (this is usually the case
  with layout code: `apps.common.confirm` doesn't make sense without importing
  `trezor.ui`)

### Avoid importing `trezor.ui`.

The `trezor.ui` namespace is one of the largest in the codebase, not counting
application code. Importing the `trezor.ui` module alone is not a big problem, but
pulling in anything from `trezor.ui.layouts` or `trezor.ui.components` usually means
loading the full UI machinery. We only want to do that if we are sure that whoever is
importing us is going to be drawing things.
