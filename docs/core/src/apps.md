# Apps

The folder `src/apps/` is the place where all the user-facing features are implemented.

Each app has a `boot()` function in the module's \_\_init\_\_ file. This functions assigns what function should be called if some specific message was received. In other words, it is a link between the MicroPython functions and the Protobuf messages.

## Example

This binds the message GetAddress to function `get_address` inside the `apps.bitcoin` module.

```python
from trezor import wire
from trezor.messages import MessageType

wire.add(MessageType.GetAddress, apps.bitcoin, "get_address")
```
