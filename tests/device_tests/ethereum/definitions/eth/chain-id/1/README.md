# External Definitions Test Fixtures

Directory for encoded (dev) signed token definitions and ERC-7730 contract
descriptors, used for device testing with external definitions. These files
back the fixtures in [`sign_tx_external_definitions.json`](../../../../sign_tx_external_definitions.json).

## Updating the definitions

Keep this directory up to date with the latest definitions from the
`definitions.tar.xz` or `deploy.tar.xz` tarballs, that can be obtained from the [`trezor/definitions`](https://github.com/trezor/trezor-common-definitions)
repo by running:

```sh
python cli.py generate --dev-sign -o <output_folder>
```

Run the command above in an external directory, then pick the contract call
you want to test.

(Or you can ask the last release manager for the latest definitions or the ERC-7730 FW maintainer(s))

The generated files are arranged as:

```
definitions/eth/<chain-id>/<display-format>/<contract-address>-<function-signature>.dat
```

## Important

Always add or remove the fixtures and definition files together.
