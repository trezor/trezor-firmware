# testapp

A test-only app that exposes every modui block to the host, so the UI can be
exercised by hand on every model. It signs nothing and derives nothing.

**Manual testing only, for now.** There are no automated tests; the host
library is written so they can be added on top of it later.

**Never ship it.** It is dev-signed only and must stay out of every release
bundle. Its manifest declares a curve and a testnet path only because core
requires one of each; neither is used.

## How it works

Each wire request names one block and carries its parameters one to one
(`protob/testapp.proto`). The app calls the block and answers with the reply
exactly as the library returned it (`UiResult`), so the host sees what the
person did — `Confirmed`, `Cancelled`, `Choice(n)`... A block that fails
answers with a `Failure`. The host picks every parameter, including the step
name (`br`).

| Request | Block |
|---|---|
| `ConfirmAction` | `modui::confirm::action` |
| `ConfirmValue` | `modui::confirm::value` |
| `ConfirmData` | `modui::confirm::data` |
| `ConfirmProperties` | `modui::confirm::properties` |
| `ConfirmSummary` | `modui::confirm::summary` |
| `ShowNotice` | `modui::notice::show` |
| `ShowProgress` | `modui::progress::run_with`, paced by the host (below) |

## Build and run

From the repository root, inside `nix-shell` with `.venv` active:

```sh
# the emulator, with app loading
cd core && CARGO_INCREMENTAL=0 ../.venv/bin/xtask build firmware --emulator \
    --model T3T1 --pyopt false --dbg-console vcp --debug-link --apps && cd ..
# the app
make extapp_build_emu EXTAPP=testapp EXTAPP_MODEL=t3t1
# run the emulator (another terminal)
cd core && PYOPT=0 ../.venv/bin/./emu.py
```

Then drive one block at a time:

```sh
sdk/apps/testapp/host/testappctl --help
sdk/apps/testapp/host/testappctl action --final \
    --extra "Account info" "Account=Tron #1" "Path=m/44'/195'/0'"
sdk/apps/testapp/host/testappctl value --address --footer-warning "Not yours"
sdk/apps/testapp/host/testappctl notice --severity danger
sdk/apps/testapp/host/testappctl progress --total 20 --steps 20
```

Every subcommand has sensible defaults, so `testappctl action` alone works.
The app is loaded afresh each run, so a rebuilt `testapp.elf` is what runs;
`--no-reload` skips that.

## Host library

`host/testapp_host` is the part meant to outlive manual testing; `cli.py` is
only a frontend over it.

```python
from testapp_host import TestApp, connect, messages as m

app = TestApp.load(connect())
result = app.call(m.ConfirmAction(title="Send", action="Really?", br="t/1"))
assert result.reply == m.Reply.Confirmed
```

A progress stays on the device for as long as a `with` block runs, and ends
however the block ends. The app asks the host for each step (`ProgressTick`),
the host answers `ProgressStep` or, on leaving the block, `ProgressEnd`:

```python
with app.progress("Working...", total=len(chunks)) as p:
    for chunk in chunks:
        process(chunk)
        p.step()
```

`messages.py` is generated from `protob/*.proto` on import, and regenerated
whenever a `.proto` is newer, so both sides of the wire always agree.
