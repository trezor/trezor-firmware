These scripts automate some tasks related to release process.

* __`relicence.py`__ rewrites licence headers in all non-empty Python files
* __`bump-required-fw-versions.py`__ downloads latest firmware versions and updates trezorlib requirements
* __`make-options-rst.py`__ runs all `trezorctl` commands with the `--help` option and concatenates output as `OPTIONS.rst`
