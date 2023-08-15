# TOIF Tool

A helpful CLI tool to work with TOIFs.

## Installation

The command `toiftool` is available within firmware repository's Poetry shell.

To install the tool separate from the firmware repository, run:

```bash
pip install -e .
```

## Displaying TOIFs

To display a TOIF image in a viewer, run:

```bash
toiftool show <path/to/toif>
```

## Converting TOIFs

To convert to or from TOIF, run:

```bash
toiftool convert <path/to/image.toif> <path/to/output.jpg>
toiftool convert <path/to/image.png> <path/to/output.toif>
```

The in/out format will be determined by the file extension.

## Getting information about TOIFs

To get information about a TOIF, run:

```bash
toiftool info <path/to/toif>
```
