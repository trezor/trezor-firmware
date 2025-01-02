# Hello world feature in TT

(How to develop on Trezor)

## Overview
This document shows the creation of a custom functionality (feature, application) on TT. It explains how to build both the Trezor (device, core) logic, as well as the client (computer, host, trezorlib) logic needed to speak with Trezor. For most new features, also the communication layer between Trezor and computer (protobuf) needs to be modified, to set up the messages they will exchange.

Intermediate knowledge of `python` and `linux` environment is assumed here to easily follow along. For steps how to set up the Trezor dev environment, refer to other docs - [build](../core/build/index.md) or [emulator](../core/emulator/index.md). The most important part is being in the `poetry shell` of this project, so all dependencies are installed.

## Feature description
We will implement a simple hello-world feature where Trezor gets some information from the host, will do something with it (optionally shows something on the screen), and returns some information back to the host, where we want to display them. (Note that there are no cryptographic operations involved in this example, it focuses only on basic communication between Trezor and host.)

## Implementation

As already mentioned, to get something useful from Trezor, writing device logic is not enough. We need to have a specific communication channel between the computer and Trezor, and also the computer needs to know how to speak to the device to trigger wanted action.

### TLDR: [implementation in a single commit](https://github.com/trezor/trezor-firmware/commit/e1cbb8a97018ec3ea39e759bbdc9a5311f992dc5)

### 1. Communication part (protobuf)
Communication between Trezor and the computer is handled by a protocol called `protobuf`. It allows for the creation of specific messages (containing clearly defined data) that will be exchanged. More details about this can be seen in [docs](../common/communication/index.md).

Trezor on its own cannot send data to the computer, it can only react to a "request" message it recognizes and send a "response" message.
Both of these messages will need to be specified, and both parts of communication will need to understand them.

Protobuf messages are defined in `common/protob` directory in `.proto` files. When we are creating a brand-new feature (application), it is worth creating a new `.proto` file dedicated only for this feature. Let's call it `messages-hello.proto` and fill it with the content below.

#### **`common/protob/messages-helloworld.proto`**
```protobuf
syntax = "proto2";
package hw.trezor.messages.helloworld;

// Sugar for easier handling in Java
option java_package = "com.satoshilabs.trezor.lib.protobuf";
option java_outer_classname = "TrezorMessageHelloWorld";

import "messages.proto";

/**
 * Request: Hello world request for text
 * @next HelloWorldResponse
 * @next Failure
 */
message HelloWorldRequest {
    required string name = 1;
    optional uint32 amount = 2 [default=1];
    optional bool show_display = 3;
}

/**
 * Response: Hello world text
 * @end
 */
 message HelloWorldResponse {
    required string text = 1;
}
```
There are some officialities at the top, the most important things are the `message` declarations. We are defining a `HelloWorldRequest`, that will be sent from the computer to Trezor, and `HelloWorldResponse`, that will be sent back from Trezor. There are many features and data-types `protobuf` supports - see [Google docs](https://developers.google.com/protocol-buffers) or other `common/protob/messages-*.proto` files.

After defining the details of communication messages, we will also need to give these messages their unique IDs and specify the direction in which they are sent (into Trezor or from Trezor). That is done in `common/protob/messages.proto` file. We will append a new block at the end of the file:
#### **`common/protob/messages.proto`**
```protobuf
// Hello world
MessageType_HelloWorldRequest = 900 [(wire_in) = true];
MessageType_HelloWorldResponse = 901 [(wire_out) = true];
```

After this, we are almost done with `protobuf`! The only thing left is to run `make gen` in the root directory to create all the auto-generated files. By running this, the `protobuf` definitions will be translated into `python` classes in both `core` and `python` sub-repositories, so that they can understand these messages. Files under `core/src/trezor` and `python/src/trezorlib` should be modified by this.

#### Optional step
This feature will be implemented only on `TT` and not the older `T1` model. If we want to be compatible with `CI`, we need to define these messages as unused for `T1`. That is done in `legacy/firmware/protob/Makefile`, where we will extend the `SKIPPED_MESSAGES` variable:

#### **`legacy/firmware/protob/Makefile`**
```sh
SKIPPED_MESSAGES := ... \
	HelloWorldRequest HelloWorldResponse
```

### 2. Trezor part (core)
The second part deals with creating the "application code" on Trezor. Surprisingly, this part is probably the easiest one from all three parts here (as this is just hello-world example).

All the applications running on Trezor are situated under `core/src/apps` directory. We could create a new application, or reuse the existing one if the feature logically corresponds to it. We will choose to implement this feature under `misc` application, as it is really a miscellaneous one.

We can therefore create a file `core/src/apps/misc/hello_world.py` and fill it with the content below:

#### **`core/src/apps/misc/hello_world.py`**
```python
from typing import TYPE_CHECKING

from trezor.messages import HelloWorldResponse
from trezor.ui.layouts import confirm_text

if TYPE_CHECKING:
    from trezor.messages import HelloWorldRequest


async def hello_world(msg: HelloWorldRequest) -> HelloWorldResponse:
    text = _get_text_from_msg(msg)
    if msg.show_display:
        await confirm_text(
            "confirm_hello_world",
            "Hello world",
            text,
            description="Hello world example",
        )
    return HelloWorldResponse(text=text)


def _get_text_from_msg(msg: HelloWorldRequest) -> str:
    return msg.amount * f"Hello {msg.name}!\n"
```

Note that we need to import the newly created protobuf messages (`HelloWorldRequest` and `HelloWorldResponse`) to provide type hints and to be able to return the response. We are also importing a `UI` layout so that we can show a confirmation dialog.

All the protobuf fields are accessible on the `msg` object and are accessed via dot notation like class attributes (`msg.show_display`). When instantiating the response object, keyword-arguments need to be used - `HelloWorldResponse(text=text)`.

Even though the code in `core` is run by a `micropython` interpreter, almost all basic features from "classic" python are supported - like `f-strings` here.

As we want to also write unittests for this module, we define a helper function `_get_text_from_msg`, even though it could easily be inlined in this case.

To see the details about code style and conventions, refer to [codestyle.md](../core/misc/codestyle.md).

We have defined all the logic, but it is not being called anywhere. We need to register the function to be called as a response to the appropriate message - in our case `HelloWorldRequest`. Registration is done in `core/src/apps/workflow_handlers.py` and the following two lines need to be added there (ideally under the `misc` section):

#### **`core/src/apps/workflow_handlers.py`**
```python
if msg_type == MessageType.HelloWorldRequest:
    return "apps.misc.hello_world"
```

The above will make sure that the `msg` (of type `HelloWorldRequest`) will be supplied into the `hello_world` function we created.

Lastly, running `make gen` in the root directory makes sure the new `misc/hello_world.py` module will be discovered. `core/src/all_modules.py` should be modified as a result.

These are all the necessary code changes in `core`. For this code to work, we will still need to build it, but that will be done in Part 4. Next, we will focus on the client implementation.

### 3. Host part (trezorlib)
So far we have defined the messages going to the Trezor and back and the Trezor logic itself. What remains is the code sitting on the computer and sending these messages into Trezor and receiving them.

There are more ways how to achieve this, for example [Connect](https://github.com/trezor/connect) is a way of communicating with Trezor from a web browser. However, we will decide to implement this connection via `trezorlib`, our own python [library](https://pypi.org/project/trezor/), which lives under `python/src/trezorlib` and acts as a `CLI` (Command-line interface) to communicate with Trezor (via `trezorctl` command).

This implementation will be split into two parts, as we will create the Trezor-communication logic in one file and the `CLI` logic taking arguments and calling this code in the second file. (It would be possible to define everything at once in the `CLI` file, but we want the possibility to call the Trezor-speaking function separately, for example when testing.)

We will create the `python/src/trezorlib/hello_world.py` file and fill it with code to speak with Trezor:

#### **`python/src/trezorlib/hello_world.py`**
```python
from typing import TYPE_CHECKING, Optional

from . import messages
from .tools import expect

if TYPE_CHECKING:
    from .client import TrezorClient
    from .protobuf import MessageType


def say_hello(
    client: "TrezorClient",
    name: str,
    amount: Optional[int],
    show_display: bool,
) -> "MessageType":
    return client.call(
        messages.HelloWorldRequest(
            name=name,
            amount=amount,
            show_display=show_display,
        ),
        expect=messages.HelloWorldResponse,
    ).text
```

Code above is sending `HelloWorldRequest` into Trezor and is expecting to get `HelloWorldResponse` back (from which it extracts the `text` string as a response).

This function is then called from the `CLI` function, which we will define in `python/src/trezorlib/cli/hello_world.py`.

#### **`python/src/trezorlib/cli/hello_world.py`**
```python
from typing import TYPE_CHECKING, Optional

import click

from .. import hello_world
from . import with_client

if TYPE_CHECKING:
    from ..client import TrezorClient


@click.group(name="helloworld")
def cli() -> None:
    """Hello world commands."""


@cli.command()
@click.argument("name")
@click.option("-a", "--amount", type=int, help="How many times to greet.")
@click.option(
    "-d", "--show-display", is_flag=True, help="Whether to show confirmation screen."
)
@with_client
def say_hello(
    client: "TrezorClient", name: str, amount: Optional[int], show_display: bool
) -> str:
    """Simply say hello to the supplied name."""
    return hello_world.say_hello(client, name, amount, show_display=show_display)
```

Code above is importing the `hello_world` module defined before and is calling its `say_hello()` function with arguments received from the user. We are using [click](https://click.palletsprojects.com/en/8.0.x/) library to create the `CLI` - first the `helloworld` group and then the `say_hello` command (which is invoked by `say-hello`).

Example of calling the `say_hello` function via command line is `trezorctl helloworld say-hello George -a 3 -d`, which utilizes all the defined arguments and options (only the `name` argument is required here).

However, the command above will not work yet, as the `helloworld` group is not registered in the main `CLI` file - `python/src/trezorlib/cli/trezorctl.py`. It will therefore need some small modifications - importing the new module and registering it:

#### **`python/src/trezorlib/cli/trezorctl.py`**
```python
from . import helloworld
...
cli.add_command(hello_world.cli)
```

If we are currently in `poetry shell`, the `trezorctl` command is being evaluated directly from the source code in `python/src/trezorlib`. That means it should be able to understand our example command `trezorctl helloworld say-hello George -a 3 -d`.

The example command on its own will however not work without listening Trezor which understands the new messages. In the next and final part, we will build and spawn a Trezor on our computer with all the changes made in Part 1 and 2.

### 4. Putting it together
Looks like all the code changes have been done, the final part is to build a Trezor image - `emulator` - so that we can actually run and test all the logic we created.

Detailed information about the emulator can be found in its [docs](../core/emulator/index.md), but we only need two most important commands, that will build and spawn the emulator:

```sh
cd core
make build_unix
./emu.py
```

After this, the emulator screen should be visible. Trying our example command should give a nice confirmation screen, and when confirming it with the green button, we should see the output in our terminal.

```sh
$ trezorctl helloworld say-hello George -a 3 -d
Please confirm action on your Trezor device.
Hello George!
Hello George!
Hello George!
```

For building the new feature into a physical Trezor, refer to [embedded](../core/build/embedded.md).

## Testing
It is always good to include some tests exercising the created functionality, so when we break it later, it will be noticed. Trezor model T supports both `unit tests` and `integration tests` (which are called `device tests`).

### Unit tests
[docs](../core/tests/index.md)

Unit tests can verify individual (mostly helper) functions that have clearly defined inputs and outputs.

They are stored under `core/tests` and can be run by `make test` in the `core` directory.

To call a specific test (the one we are about to create), run `make test TESTOPTS=test_apps.misc.hello_world.py`

#### **`core/tests/test_apps.misc.hello_world.py`**
```python
from common import *

from trezor.messages import HelloWorldRequest
from apps.misc.hello_world import _get_text_from_msg


class TestHelloWorld(unittest.TestCase):
    def test_get_text_from_msg(self):
        msg = HelloWorldRequest(name="Satoshi", amount=2, show_display=False)
        self.assertEqual(_get_text_from_msg(msg), "Hello Satoshi!\nHello Satoshi!\n")


if __name__ == "__main__":
    unittest.main()
```

Code above is using the `unittest` testing framework, however not directly from python's standard library. As these unit tests are run by `micropython`, which does not have `unittest` library, we had to create the functionality ourselves in `core/tests/unittest.py` - see `from common import *`.

Current code checks one usage of `_get_text_from_msg`, the only deterministic helper function we use in our feature. One could create many test vectors trying different inputs and expecting different outputs.

### Device tests
[docs](../tests/device-tests.md)

Device tests (our name for integration tests) should test the whole workflow from sending the first request into Trezor to Trezor sending the final response.

`trezorlib` is used extensively in these tests as a way to request something from Trezor and then assert the expected response (it actually uses the code we created in Part 3).

They are closely connected with [ui tests](../tests/ui-tests.md), which assert Trezor's screens have a known and expected content during the device tests.

Device tests are stored in `tests/device_tests` and they can be run by `make test_emu` in `core`. Running the specific file we will create can be done by `make test_emu TESTOPTS="-k test_hello_world.py"`.

#### **`tests/device_tests/misc/test_hello_world.py`**

```python
from typing import Optional

import pytest

from trezorlib import hello_world
from trezorlib.debuglink import TrezorClientDebugLink as Client

VECTORS = (  # name, amount, show_display
    ("George", 2, True),
    ("John", 3, False),
    ("Hannah", None, False),
)


@pytest.mark.models("core")
@pytest.mark.parametrize("name, amount, show_display", VECTORS)
def test_hello_world(
    client: Client, name: str, amount: Optional[int], show_display: bool
):
    with client:
        greeting_text = hello_world.say_hello(
            client, name=name, amount=amount, show_display=show_display
        )
        greeting_lines = greeting_text.strip().splitlines()

        assert len(greeting_lines) == amount or 1
        assert all(name in line for line in greeting_lines)
```

Unlike in unit tests, [pytest](https://docs.pytest.org) is used as the test framework, which is more suitable for bigger and more complex test suites.

As the functionality is developed only for `core`, we want to limit the test via `@pytest.mark.models("core")`, otherwise the CI would run it (and fail) for Trezor One too.

We are also using the `@pytest.mark.parametrize` decorator, which is an efficient way of testing multiple inputs into the same test case.

We are not asserting the exact result of the greeting (that is done by unit tests), we just check it has the expected structure - but we can check really anything here.

Note the usage of `trezorlib.hello_world.say_hello`, which we defined earlier, so we see how it can be useful for testing purposes.

#### Optional step
If we want to be fully compatible with `CI`, we need to create expected `UI-test` results. The most straightforward way to do it is to run `make test_emu_ui_record` in `core` directory.

## Conclusion
All changes in one commit can be seen [here](https://github.com/trezor/trezor-firmware/commit/e1cbb8a97018ec3ea39e759bbdc9a5311f992dc5).

Ideas for potentially useful Trezor features are welcome. Feel free to submit issues and open PRs, even if incomplete.
