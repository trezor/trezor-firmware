# Apps

The folder `src/apps/` is the place where all the user-facing features are implemented.

Each app must be registered by the `register` function inside the file `workflow_handlers.py`. This functions assigns what function should be called if some specific message was received. In other words, it is a link between the MicroPython functions and the Protobuf messages.

## Example

For a user facing application you would assign the message to the module in `_find_message_handler_module`. This binds the message `GetAddress` to function `get_address` inside the `apps.bitcoin.get_address` module.

```python
# in core/src/apps/workflow_handlers.py

# ...

def _find_message_handler_module(msg_type: int) -> str:
    from trezor.enums import MessageType

    # ...

    if msg_type == MessageType.GetAddress:
        return "apps.bitcoin.get_address"

    # ...
```

```python
# in core/src/apps/bitcoin/get_address.py

# ...

async def get_address(msg: GetAddress, keychain: Keychain, coin: CoinInfo) -> Address:
    # ...

```
