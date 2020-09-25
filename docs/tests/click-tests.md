# Click Tests

This set of tests is intended for cases where USB communication must be decoupled from
the input stream. They are mainly based on sending simulated clicks and reading screen
contents. Unlike device tests that use the `client` fixture, click tests generally
use the `device_handler` fixture. TODO fixture documentation, the important point is
that `device_handler` runs `trezorlib` calls in the background and leaves the main
thread free to interact with the device from the user's perspective.

## Running the full test suite

_Note: You need Poetry, as mentioned in the core's [documentation](https://docs.trezor.io/trezor-firmware/core/) section._

In the `trezor-firmware` checkout, in the root of the monorepo, install the environment:

```sh
poetry install
```

Switch to a shell inside theenvironment:

```sh
poetry shell
```

If you want to test against the emulator, run it in a separate terminal:
```sh
./core/emu.py
```

Now you can run the test suite with `pytest` from the root directory:
```sh
pytest tests/click_tests
```

## Click test recorder

The repository now includes a tool for automatically generating testcases from user
interaction. The resulting test cases must still be tweaked manually, but they can
provide a solid starting point for a complex interaction pattern.

**Caveat:** The testcase recorder is in alpha-stage, both in terms of functionality
and code quality. Your mileage may vary.

Run the tool with:

```sh
python tests/click_tests/record_layout.py
```

The tool accepts the same arguments as `trezorctl`. For example, to record yourself
getting an address, use:

```sh
python tests/click_tests/record_layout.py btc get-address -n m/44h/0h/0h/0/0 -d
```

Instead of clicking buttons on the emulator, type commands in the terminal that ran
the tool. A list of possible button clicks will be shown in your terminal. These will
be sent to the emulator over debuglink.

(Note that if a particular click does not react through the tool, there is a good chance
that it won't work in the testcase either. Please file an issue.)

After the session is over (when you type `stop`), the tool will collect all layout
changes and output a testcase in pytest format. Copy-paste that into your test file
and tweak as appropriate.
