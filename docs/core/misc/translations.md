# Translations

## Overview

`Trezor` stores translated strings in `.json` files in [core/translations directory](../../../core/translations) - e.g. [de.json](../../../core/translations/de.json).

When no foreign-language is present, the English version is used - [en.json](../../../core/translations/en.json).

Translations files contain the translated strings and also all the special font characters as a link to `.json` files in [fonts](../../../core/translations/fonts) directory. Font files are not needed for `english`, which uses just default/built-in `ASCII` characters.

## Generating blobs

To generate up-to-date blobs, use `python core/translations/cli.py gen` - they will appear in `core/translations` as `translations-*.bin` files. The files contain information about the specific hardware model, language and device version.

## Uploading blobs

To upload blobs with foreign-language translations, use `trezorctl set language <blob_location>` command.

To switch the language back into `english`, use `trezorctl set language -r`.
