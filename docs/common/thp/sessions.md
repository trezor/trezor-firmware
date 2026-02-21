# Introduction

This document specifies the application layer of the Trezor-Host protocol (THP). For general information about the protocol, and lower protocol layers, see [specification.md](./specification.md).

# Application layer

The THP application layer has the following structure:
| **Offset** | **Size** | **Field name**             | **Description**                                   |
|:----------:|:--------:|:---------------------------|:--------------------------------------------------|
| 0          | 1        | *session_id*               | A single byte identifying the session. |
| 1          | 2        | *message_type*             | TODO |
| 3          | var      | *protobuf_encoded_message* | TODO |

# Session vs. channel

THP Channel represents a single encrypted connection ("encrypted channel"). Each channel can contain multiple sessions. A (standard) session represents a single passphrase-wallet. Each session can have arbitrary passphrase (or none), there can be multiple sessions with the same passphrase.

## Session

A new session is created by sending a `ThpCreateNewSession` with desired parameters to the Trezor.

## Seedless sessions

Seedless sessions are a special kind of sessions. These sessions can be used for operations that do not require the seed to be derived - for instance management tasks. Only seedless sessions can be used on uninitialzed devices.

