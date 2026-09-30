# External Definitions Test Fixtures

Directory for network and token definitions and ERC-7730 contract descriptors,
stored as JSON and used for device testing with external definitions. These
files back the fixtures in [`sign_tx_external_definitions.json`](../../../../sign_tx_external_definitions.json).

## Format

Each file holds the definition type and the decoded protobuf message (bytes as
hex, enums by name):

```json
{
  "data_type": "ETHEREUM_NETWORK",
  "message": {
    "chain_id": 1,
    "symbol": "ETH",
    "slip44": 60,
    "name": "Ethereum"
  }
}
```

The tests serve them through `JsonSource` (in `tests/definitions.py`), which
encodes and dev-signs each definition when the device requests it, always with
format version 2 and the maximum timestamp, so the fixtures never expire.

The files are arranged as:

```
definitions/eth/chain-id/<chain-id>/network.json
definitions/eth/chain-id/<chain-id>/token-<token-address>.json
definitions/eth/chain-id/<chain-id>/display-format/<contract-address>-<function-signature>.json
```

## Adding definitions

Generate the definitions with the [`trezor/definitions`](https://github.com/trezor/trezor-common-definitions)
repo, in an external directory:

```sh
python cli.py generate --dev-sign -o <output_folder>
```

(Or you can ask the last release manager for the latest definitions or the
ERC-7730 FW maintainer(s).)

Pick the `.dat` files for the contract calls you want to test, and convert
each one to JSON next to it:

```python
import io, json, sys
from pathlib import Path

from trezorlib import definitions, messages, protobuf

TYPES = {
    messages.DefinitionType.ETHEREUM_NETWORK: messages.EthereumNetworkInfo,
    messages.DefinitionType.ETHEREUM_TOKEN: messages.EthereumTokenInfo,
    messages.DefinitionType.ETHEREUM_DISPLAY_FORMAT: messages.EthereumDisplayFormatInfo,
}

for name in sys.argv[1:]:
    path = Path(name)
    payload = definitions.Definition.parse(path.read_bytes()).payload
    msg = protobuf.load_message(io.BytesIO(payload.data), TYPES[payload.data_type])
    converted = {"data_type": payload.data_type.name, "message": protobuf.to_dict(msg)}
    path.with_suffix(".json").write_text(json.dumps(converted, indent=2) + "\n")
```

Then copy the `.json` files here, keeping the layout above.

## Important

Always add or remove the fixtures and definition files together.
