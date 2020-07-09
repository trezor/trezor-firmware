# click-test generator
#
# Beware: This tool is alpha-stage, both in terms of functionality and code quality.
# It is published here because it can be useful as-is. But it's full of bugs in any
# case.
#
# See docs/tests/click-tests.md for a brief instruction manual.

import inspect
import sys
import threading
import time
from pathlib import Path

import click

from trezorlib import (
    binance,
    btc,
    cardano,
    cosi,
    device,
    eos,
    ethereum,
    fido,
    firmware,
    lisk,
    misc,
    monero,
    nem,
    ripple,
    stellar,
    tezos,
)
from trezorlib.cli.trezorctl import cli as main

from trezorlib import cli, debuglink, protobuf  # isort:skip


# make /tests part of sys.path so that we can import buttons.py as a module
ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))
import buttons  # isort:skip

MODULES = (
    binance,
    btc,
    cardano,
    cosi,
    device,
    eos,
    ethereum,
    fido,
    firmware,
    lisk,
    misc,
    monero,
    nem,
    ripple,
    stellar,
    tezos,
)


CALLS_DONE = []
DEBUGLINK = None

get_client_orig = cli.TrezorConnection.get_client


def get_client(conn):
    global DEBUGLINK
    client = get_client_orig(conn)
    DEBUGLINK = debuglink.DebugLink(client.transport.find_debug())
    DEBUGLINK.open()
    DEBUGLINK.watch_layout(True)
    return client


cli.TrezorConnection.get_client = get_client


def scan_layouts(dest):
    while True:
        try:
            layout = DEBUGLINK.wait_layout()
        except Exception:
            return
        dest.append(layout)


CLICKS_HELP = """\
Type 'y' or just press Enter to click the right button (usually "OK")
Type 'n' to click the left button (usually "Cancel")
Type a digit (0-9) to click the appropriate button as if on a numpad.
Type 'g1,2' to click button in column 1 and row 2 of 3x5 grid (letter A on mnemonic keyboard).
Type 'i 1234' to send text "1234" without clicking (useful for PIN, passphrase, etc.)
Type 'u' or 'j' to swipe up, 'd' or 'k' to swipe down.
Type 'confirm' for hold-to-confirm (or a confirmation signal without clicking).
Type 'stop' to stop recording.
"""


def layout_to_output(layout):
    if isinstance(layout, str):
        return layout

    if len(layout.lines) > 1:
        text = " ".join(layout.lines[1:])
        return f"assert {text!r} in layout.text"
    else:
        return f"assert layout.text == {layout.text!r}"


def echo(what):
    click.secho(what, fg="blue", err=True)
    sys.stderr.flush()


def send_clicks(dest):
    echo(CLICKS_HELP)
    while True:
        key = click.prompt(click.style("Send click", fg="blue"), default="y")
        sys.stderr.flush()

        try:
            layout = DEBUGLINK.read_layout()
            echo("Please wait...")

            if key == "confirm":
                output = "debug.input(button=True)"
                DEBUGLINK.press_yes()
            elif key in "uj":
                output = "debug.input(swipe=messages.DebugSwipeDirection.UP)"
                DEBUGLINK.swipe_up()
            elif key in "dk":
                output = "debug.input(swipe=messages.DebugSwipeDirection.DOWN)"
                DEBUGLINK.swipe_down()
            elif key.startswith("i "):
                input_str = key[2:]
                output = f"debug.input({input_str!r})"
                DEBUGLINK.input(input_str)
            elif key.startswith("g"):
                x, y = [int(s) - 1 for s in key[1:].split(",")]
                output = f"debug.click(buttons.grid35({x}, {y}))"
                DEBUGLINK.click(buttons.grid35(x, y))
            elif key == "y":
                output = "debug.click(buttons.OK)"
                DEBUGLINK.click(buttons.OK)
            elif key == "n":
                output = "debug.click(buttons.CANCEL)"
                DEBUGLINK.click(buttons.CANCEL)
            elif key in "0123456789":
                if key == "0":
                    x, y = 1, 4
                else:
                    i = int(key) - 1
                    x = i % 3
                    y = 3 - (i // 3)  # trust me
                output = f"debug.click(buttons.grid35({x}, {y}))"
                DEBUGLINK.click(buttons.grid35(x, y))
            elif key == "stop":
                return
            else:
                raise Exception

            # give emulator time to react
            time.sleep(0.5)
            new_layout = DEBUGLINK.read_layout()
            if new_layout != layout:
                # assume emulator reacted with a layout change
                output = f"layout = {output[:-1]}, wait=True)"

            dest.append(output)
        except Exception:
            echo("bad input")


def record_wrapper(name, func):
    def wrapper(*args, **kwargs):
        clicks = []
        layouts = []
        call_item = [name, args, kwargs, clicks, layouts]

        clicks_thr = threading.Thread(target=send_clicks, args=(clicks,), daemon=True)
        clicks_thr.start()
        try:
            result = func(*args, **kwargs)
            call_item.extend([result, None])
            return result
        except BaseException as e:
            call_item.extend([None, e])
            raise
        finally:
            clicks_thr.join()

            thr = threading.Thread(target=scan_layouts, args=(layouts,), daemon=True)
            thr.start()
            # 5 seconds to download all layout changes so far should be enough
            thr.join(timeout=5)

            DEBUGLINK.close()  # this should shut down the layout scanning thread
            thr.join()
            DEBUGLINK.open()

            CALLS_DONE.append(call_item)

    return wrapper


for module in MODULES:
    assert inspect.ismodule(module)
    for name, member in inspect.getmembers(module):
        if not inspect.isfunction(member):
            continue

        sig = inspect.signature(member)
        params = list(sig.parameters)
        if params[0] != "client":
            continue

        func_name = f"{module.__name__}.{name}"
        setattr(module, name, record_wrapper(func_name, member))


def call_to_strs(call):
    func_name, args, kwargs, clicks, layouts, result, exception = call
    args = args[1:]

    arg_text = [repr(arg) for arg in args]
    arg_text.extend(f"{name}={value!r}" for name, value in kwargs.items())

    call = f"device_handler.run({func_name}, {', '.join(arg_text)})"

    result_list = []
    if exception is None:
        if isinstance(result, protobuf.MessageType):
            result_list.append("result = device_handler.result()")
            result_list.append(
                f"assert isinstance(result, messages.{result.__class__.__name__}"
            )
            for k, v in result.__dict__.items():
                if v is None or v == []:
                    continue
                result_list.append(f"assert result.{k} == {v!r}")
        else:
            result_list.append(f"assert device_handler.result() == {result!r}")
    else:
        result_list = [
            f"with pytest.raises({exception.__class__.__name__}):",
            "    device_handler.result()",
        ]

    layouts_iter = iter(layouts)
    layout_text = ["layout = debug.wait_layout()", next(layouts_iter)]

    for instr in clicks:
        layout_text.append(instr)
        if "wait=True" in instr:
            layout_text.append(next(layouts_iter))

    # finish layouts iterator -- should not do anything ideally
    layout_text.extend(layouts_iter)

    layout_text = [layout_to_output(l) for l in layout_text]

    all_lines = "\n".join([call] + layout_text + result_list).split("\n")
    all_lines = [f"    {l}" for l in all_lines]
    func_name_under = func_name.replace(".", "_")
    all_lines.insert(0, f"def test_{func_name_under}(device_handler):")
    all_lines.insert(1, "    debug = device_handler.debuglink()")

    return "\n".join(all_lines)


if __name__ == "__main__":
    echo(
        """\
Quick&Dirty Test Case Recorder.

Use as you would use trezorctl, input clicking commands via host keyboard
for best results.
"""
    )
    try:
        main()
    finally:
        if DEBUGLINK is not None:
            DEBUGLINK.watch_layout(False)
            DEBUGLINK.close()
            echo("\n# ========== test cases ==========\n")
            for call in CALLS_DONE:
                testcase = call_to_strs(call)
                echo(testcase)
                echo("\n")
