# Trezor Common

Common contains files shared among Trezor projects.

## Coin Definitions

JSON coin definitions and support tables.

## External definitions

Description of external definitions for the Ethereum and Solana tokens and the process of their generation. See [External definitions](external-definitions.md).

## Communication

We use [Protobuf v2](https://developers.google.com/protocol-buffers/) for host-device communication. The communication cycle is very simple, Trezor receives a message (request), acts on it and responds with another one (response). Trezor on its own is incapable of initiating the communication.

## Protobuf Definitions

Protobuf messages are defined in the [Common](https://github.com/trezor/trezor-firmware/tree/master/common) project, which is part of this monorepo. This repository is also exported to [trezor/trezor-common](https://github.com/trezor/trezor-common) to be used by third parties, which prefer not to include the whole monorepo. That copy is read-only mirror and all changes are happening in this monorepo.

## Tools

Tools for managing coin definitions and related data.

## Message Workflows

- [Bitcoin transaction signing](bitcoin-signing.md)
